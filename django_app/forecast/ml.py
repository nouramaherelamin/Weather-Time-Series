"""Model registry + prediction logic. Pure Python (no Django). Bundles are loaded ONCE and reused across requests."""
import copy
import datetime as dt
import logging
import threading
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from .trainer import FEATURES, HORIZONS

log = logging.getLogger(__name__)
_lock = threading.Lock()
_REG = {}

FEATURE_GROUPS = {"temperature": ["temperature"], "humidity": ["humidity"], "wind_speed": ["wind_speed"],
                  "pressure": ["pressure"], "season": ["doy_sin", "doy_cos"]}
GROUP_LABELS = {"temperature": "Today’s temperature", "humidity": "Humidity", "wind_speed": "Wind speed",
                "pressure": "Pressure", "season": "Time of year"}


def reset():
    with _lock:
        _REG.clear()
    _cached_predict.cache_clear()


def register(bundle):
    with _lock:
        _REG[bundle["city"]["slug"]] = bundle
    _cached_predict.cache_clear()


def load_all(models_dir):
    """Load every *.joblib bundle in models_dir (once). Returns the list of loaded city slugs."""
    import sklearn
    d = Path(models_dir)
    for f in sorted(d.glob("*.joblib")) if d.exists() else []:
        try:
            b = joblib.load(f)
            if "models" not in b or "city" not in b:        # e.g. the old single-model file
                continue
        except Exception as e:                               # corrupt / incompatible file: skip, keep serving the others
            log.warning("Could not load %s: %s", f.name, e)
            continue
        if b.get("sklearn_version") != sklearn.__version__:
            log.warning("%s was trained with scikit-learn %s but %s is installed - re-run train_app_models.py",
                        f.name, b.get("sklearn_version"), sklearn.__version__)
        register(b)
    return list(_REG)


def is_ready():
    return bool(_REG)


def cities():
    return [dict(b["city"], trained_through=b["trained_through"]) for b in _REG.values()]


def get_bundle(slug=None):
    if not _REG:
        raise RuntimeError("No trained model found - run `python train_app_models.py` first")
    if slug is None:
        slug = "cairo" if "cairo" in _REG else next(iter(_REG))
    if slug not in _REG:
        raise KeyError(f"Unknown city '{slug}'")
    return _REG[slug]


def model_options(slug=None):
    b = get_bundle(slug)
    out = []
    for key, m in b["models"].items():
        out.append({"key": key, "label": m["label"], "mae1": round(m["metrics"][1]["MAE"], 2),
                    "rmse1": round(m["metrics"][1]["RMSE"], 2), "smape1": round(m["metrics"][1]["sMAPE"], 2),
                    "best": key == b["best_model"]})
    return out


def comparison(slug=None):
    """MAE by horizon for every model + baselines (for tables/charts)."""
    b = get_bundle(slug)
    rows = {m["label"]: [round(m["metrics"][h]["MAE"], 3) for h in HORIZONS] for m in b["models"].values()}
    rows["Persistence (today = tomorrow)"] = [round(b["baselines"]["persistence"][h]["MAE"], 3) for h in HORIZONS]
    rows["Climatology (seasonal average)"] = [round(b["baselines"]["climatology"][h]["MAE"], 3) for h in HORIZONS]
    return {"horizons": HORIZONS, "series": rows}


def _features(t, h, w, p, doy):
    import math
    return {"temperature": t, "humidity": h, "wind_speed": w, "pressure": p,
            "doy_sin": math.sin(2 * math.pi * doy / 365.25), "doy_cos": math.cos(2 * math.pi * doy / 365.25)}


@lru_cache(maxsize=1024)                      # identical inputs return instantly (bonus: caching)
def _cached_predict(slug, model_key, t, h, w, p, date_iso):
    b = get_bundle(slug)
    if model_key in (None, "", "best"):
        model_key = b["best_model"]
    if model_key not in b["models"]:
        raise KeyError(f"Unknown model '{model_key}'")
    m = b["models"][model_key]
    start = dt.date.fromisoformat(date_iso)
    x = pd.DataFrame([_features(t, h, w, p, start.timetuple().tm_yday)])[FEATURES]
    forecast = []
    for hz in HORIZONS:
        val = float(m["estimators"][hz].predict(x)[0])
        margin = 1.96 * m["resid_std"][hz]
        d = start + dt.timedelta(days=hz)
        forecast.append({"day": hz, "date": d.isoformat(), "prediction": round(val, 2), "low": round(val - margin, 2),
                         "high": round(val + margin, 2), "normal": round(b["climatology"][min(d.timetuple().tm_yday, 366) - 1], 2)})
    # explanation for tomorrow: how much does each input move the prediction vs. "average" conditions?
    base = _features(t, h, w, p, start.timetuple().tm_yday)
    rows = [base]
    for g, feats in FEATURE_GROUPS.items():
        r = dict(base)
        for f in feats:
            r[f] = b["train_means"][f]
        rows.append(r)
    preds = m["estimators"][1].predict(pd.DataFrame(rows)[FEATURES])
    explain = sorted(({"feature": g, "label": GROUP_LABELS[g], "effect": round(float(preds[0] - preds[i + 1]), 2)}
                      for i, g in enumerate(FEATURE_GROUPS)), key=lambda e: -abs(e["effect"]))
    given = {"temperature": t, "humidity": h, "wind_speed": w, "pressure": p}
    outside = [k for k, v in given.items() if not (b["train_ranges"][k][0] - 1e-9 <= v <= b["train_ranges"][k][1] + 1e-9)]
    first = forecast[0]
    return {"city": b["city"]["name"], "city_slug": slug, "model": model_key, "model_label": m["label"],
            "start_date": date_iso, "prediction": first["prediction"], "low": first["low"], "high": first["high"],
            "forecast": forecast, "explain": explain, "outside_training_range": outside,
            "mae_day1": round(m["metrics"][1]["MAE"], 2), "trained_through": b["trained_through"]}


def predict(slug, model_key, temperature, humidity, wind_speed, pressure, date):
    date_iso = date.isoformat() if hasattr(date, "isoformat") else str(date)
    return copy.deepcopy(_cached_predict(slug, model_key or "best", float(temperature), float(humidity),
                                         float(wind_speed), float(pressure), date_iso))
