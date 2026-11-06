"""Helpers for tests: build a small synthetic model bundle so tests never need the real trained files or the internet."""
import numpy as np
import pandas as pd

from . import trainer


def synthetic_daily(seed=1, start="2022-01-01", end="2026-10-15"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end, freq="D")
    doy = idx.dayofyear.values
    temp = 21 + 9 * np.sin(2 * np.pi * (doy - 110) / 365.25) + rng.normal(0, 1.6, len(idx))
    return pd.DataFrame({"temperature": temp, "humidity": np.clip(55 - 1.2 * (temp - 21) + rng.normal(0, 6, len(idx)), 5, 100),
                         "wind_speed": np.abs(rng.normal(14, 5, len(idx))), "pressure": 1012 + rng.normal(0, 3, len(idx)),
                         "precipitation": (rng.random(len(idx)) < .03) * rng.random(len(idx)) * 5}, index=idx)


def make_bundle(slug="cairo", name="Cairo, Egypt", lat=30.04, lon=31.24, seed=1):
    return trainer.build_bundle(synthetic_daily(seed), {"slug": slug, "name": name, "lat": lat, "lon": lon}, test_days=60, fast=True)
