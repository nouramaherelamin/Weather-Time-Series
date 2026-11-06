"""
Builds the model bundles used by the Django web app (one .joblib per city, 3 models x 7 horizons each).

    python train_app_models.py                       # all cities in config.CITIES (Cairo reuses Task 4's data)
    python train_app_models.py --cities aswan        # only the listed cities (comma separated)
    python train_app_models.py --fast                # smaller models (quick smoke test)
    python train_app_models.py --refresh             # re-download the data

Run Task 4 first (it creates data/weather_clean.csv for Cairo). Other cities are downloaded once (10 API calls each)
and cached in data/cities/<city>/raw/, so if the download stops (rate limit / no internet) just run the command again.
"""
import argparse
import re
import sys
from importlib import metadata

import joblib
import pandas as pd

import config

sys.path.insert(0, str(config.BASE / "django_app"))
from forecast import trainer  # noqa: E402


def pin_requirements():
    """Pin the libraries that matter for unpickling to the versions used for training (so Docker/Render match)."""
    req = config.BASE / "django_app" / "requirements.txt"
    if not req.exists():
        return
    text = req.read_text()
    for pkg in ("pandas", "numpy", "scikit-learn", "joblib"):
        text = re.sub(rf"(?m)^{re.escape(pkg)}\b.*$", f"{pkg}=={metadata.version(pkg)}", text)
    req.write_text(text)
    print("[requirements] pinned:", ", ".join(f"{p}=={metadata.version(p)}" for p in ("pandas", "numpy", "scikit-learn", "joblib")))


def train_city(city, args):
    if city["slug"] == "cairo" and config.CLEAN_CSV.exists() and not args.refresh:
        daily = pd.read_csv(config.CLEAN_CSV, parse_dates=["date"], index_col="date").asfreq("D")
        print(f"using Task 4 data: {config.CLEAN_CSV.name} ({len(daily)} days)")
    else:
        from task4_data_eda import build_city_daily            # imported lazily (pulls in matplotlib)
        daily = build_city_daily(city, refresh=args.refresh)
    bundle = trainer.build_bundle(daily, city, fast=args.fast)
    out = config.APP_MODELS_DIR / f"{city['slug']}.joblib"
    joblib.dump(bundle, out, compress=3)
    print(f"saved {out.name} ({out.stat().st_size / 1e6:.1f} MB) | trained through {bundle['trained_through']} | best model: {bundle['best_model']}")
    for m in bundle["models"].values():
        print(f"  {m['label']:<20} MAE " + " ".join(f"+{h}d:{m['metrics'][h]['MAE']:.2f}" for h in trainer.HORIZONS))
    for k, v in bundle["baselines"].items():
        print(f"  {k:<20} MAE " + " ".join(f"+{h}d:{v[h]['MAE']:.2f}" for h in trainer.HORIZONS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", default=",".join(c["slug"] for c in config.CITIES))
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    wanted = [s.strip() for s in args.cities.split(",") if s.strip()]
    known = {c["slug"] for c in config.CITIES}
    unknown = [w for w in wanted if w not in known]
    if unknown:
        sys.exit(f"Unknown city slug(s): {', '.join(unknown)}. Available: {', '.join(sorted(known))}")
    config.APP_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    legacy = config.APP_MODELS_DIR / "weather_model.joblib"
    if legacy.exists():
        legacy.unlink()
        print("[cleanup] removed the old single-model file weather_model.joblib")

    failed = []
    for city in [c for c in config.CITIES if c["slug"] in wanted]:
        print(f"\n=== {city['name']} ===")
        try:
            train_city(city, args)
        except Exception as e:                                   # one failing city must not lose the others
            failed.append(city["slug"])
            print(f"!! {city['name']} NOT trained: {e.__class__.__name__}: {e}")

    pin_requirements()
    have = sorted(p.stem for p in config.APP_MODELS_DIR.glob("*.joblib"))
    print("\nModels available to the web app:", ", ".join(have) or "none")
    if failed:
        print(f"\n!! Not finished: {', '.join(failed)}. Usually a temporary Open-Meteo rate limit or no internet.")
        print("   Years already downloaded are cached, so just retry in a few minutes:")
        print(f"   python train_app_models.py --cities {','.join(failed)}")
        sys.exit(1)
    print("\nDone. Verify with:  cd django_app && python manage.py check_model")


if __name__ == "__main__":
    main()
