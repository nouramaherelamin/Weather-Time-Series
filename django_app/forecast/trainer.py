"""Builds the per-city model bundle used by the web app. Pure Python + scikit-learn (no Django).

For every horizon h = 1..7 days we train a DIRECT model: today's mean conditions + day-of-year -> mean temperature at t+h.
Three model families are trained; they are evaluated on a chronological hold-out (last `test_days` days, no shuffling,
and no training row whose target falls inside the test period), then re-fitted on all data for production use.
"""
import datetime as dt

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["temperature", "humidity", "wind_speed", "pressure", "doy_sin", "doy_cos"]
INPUT_COLS = ["temperature", "humidity", "wind_speed", "pressure"]
HORIZONS = list(range(1, 8))


def model_specs(fast=False):
    n_gb, n_rf = (40, 25) if fast else (200, 120)
    return {
        "ridge": ("Ridge Regression", lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0))),
        "gbr": ("Gradient Boosting", lambda: GradientBoostingRegressor(
            n_estimators=n_gb, max_depth=3, learning_rate=.05, subsample=.8, random_state=42)),
        "rf": ("Random Forest", lambda: RandomForestRegressor(
            n_estimators=n_rf, max_depth=8, min_samples_leaf=5, n_jobs=-1, random_state=42)),
    }


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": float(np.mean(np.abs(y - p))), "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
            "sMAPE": float(np.mean(2 * np.abs(y - p) / (np.abs(y) + np.abs(p))) * 100)}


def climatology(series):
    """Mean by day-of-year (1..366), circularly smoothed with a 15-day window -> numpy array of length 366."""
    c = series.groupby(series.index.dayofyear).mean().reindex(range(1, 367)).interpolate().bfill().ffill()
    ext = pd.concat([c.iloc[-15:], c, c.iloc[:15]]).rolling(15, center=True).mean().iloc[15:-15]
    return ext.values.astype(float)


def add_features(df):
    df = df.copy()
    df["doy_sin"] = np.sin(2 * np.pi * df.index.dayofyear / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df.index.dayofyear / 365.25)
    return df


def build_bundle(daily, city, test_days=90, fast=False):
    """daily: DataFrame with DatetimeIndex (daily) and temperature/humidity/wind_speed/pressure(/precipitation).
    city: {"slug","name","lat","lon"}."""
    df = daily.sort_index().asfreq("D")
    cols = [c for c in INPUT_COLS + ["precipitation"] if c in df.columns]
    df[cols] = df[cols].interpolate(method="time", limit=3, limit_direction="both")
    df = add_features(df.dropna(subset=INPUT_COLS))
    test_start = df.index.max() - pd.Timedelta(days=test_days - 1)
    specs = model_specs(fast)
    X = df[FEATURES]
    clim_train = climatology(df.loc[df.index < test_start, "temperature"])
    clim_all = climatology(df["temperature"])

    models, baselines = {}, {"persistence": {}, "climatology": {}}
    for key, (label, make) in specs.items():
        models[key] = {"label": label, "estimators": {}, "resid_std": {}, "metrics": {}}
    for h in HORIZONS:
        y = df["temperature"].shift(-h)
        valid = y.notna()
        tr = valid & (df.index < test_start - pd.Timedelta(days=h))       # no label leakage into the test window
        te = valid & (df.index >= test_start)
        if te.sum() < 10 or tr.sum() < 100:
            raise ValueError(f"Not enough data for horizon {h} (train={tr.sum()}, test={te.sum()})")
        yte = y[te]
        for key, (label, make) in specs.items():
            m = make().fit(X[tr], y[tr])
            pred = m.predict(X[te])
            models[key]["metrics"][h] = metrics(yte, pred)
            models[key]["resid_std"][h] = float(np.std(yte.values - pred, ddof=1))
            models[key]["estimators"][h] = make().fit(X[valid], y[valid])   # production model: all data
        doy_target = (df.index[te] + pd.Timedelta(days=h)).dayofyear
        baselines["persistence"][h] = metrics(yte, df.loc[te, "temperature"])
        baselines["climatology"][h] = metrics(yte, clim_train[doy_target - 1])

    best = min(models, key=lambda k: models[k]["metrics"][1]["MAE"])
    sample_row = df.iloc[-8]
    sample = {"inputs": {c: float(sample_row[c]) for c in INPUT_COLS}, "date": sample_row.name.date().isoformat(),
              "predictions": {k: {h: float(models[k]["estimators"][h].predict(X.iloc[[-8]])[0]) for h in HORIZONS} for k in models}}
    hist_cols = [c for c in ["temperature", "humidity", "wind_speed", "pressure", "precipitation"] if c in df.columns]
    history = {"date": [d.date().isoformat() for d in df.index]}
    history.update({c: [round(float(v), 2) for v in df[c].fillna(0)] for c in hist_cols})
    return {
        "city": dict(city), "features": FEATURES, "horizons": HORIZONS, "models": models, "baselines": baselines,
        "best_model": best, "test_days": test_days, "trained_through": df.index.max().date().isoformat(),
        "n_days": int(len(df)), "train_means": {c: float(df[c].mean()) for c in FEATURES},
        "train_ranges": {c: [float(df[c].min()), float(df[c].max())] for c in INPUT_COLS},
        "climatology": [float(v) for v in clim_all], "history": history, "sample": sample,
        "sklearn_version": sklearn.__version__, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
