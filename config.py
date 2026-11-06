"""Shared settings for Tasks 4, 5 and 6. Change the city/dates here and re-run."""
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUT = BASE / "outputs"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

CITY = "Cairo, Egypt"
LAT, LON = 30.0444, 31.2357
START, END = "2016-10-16", "2026-10-15"   # 10 years (Open-Meteo archive lags a few days behind today)

RAW_DIR = DATA / "raw_chunks"                  # one raw API response per year
RAW_JSON = DATA / "raw_openmeteo_response.json" # all chunks combined
HOURLY_CSV = DATA / "weather_hourly_clean.csv"
CLEAN_CSV = DATA / "weather_clean.csv"
MODEL_PATH = DATA / "task5_feature_model.joblib"        # Task 5 coursework model (the web app uses train_app_models.py)
APP_MODELS_DIR = BASE / "django_app" / "models"        # model bundles loaded by the Django app
CITY_DIR = DATA / "cities"                              # per-city daily CSVs + raw API chunks

CITIES = [   # cities available in the web app (add more here, then re-run train_app_models.py)
    {"slug": "cairo", "name": "Cairo, Egypt", "lat": 30.0444, "lon": 31.2357},
    {"slug": "alexandria", "name": "Alexandria, Egypt", "lat": 31.2001, "lon": 29.9187},
    {"slug": "aswan", "name": "Aswan, Egypt", "lat": 24.0889, "lon": 32.8998},
]

# Cities served by the web app (Cairo is the one analysed in the Task 4/5 notebooks).
CITIES = [
    {"slug": "cairo", "name": "Cairo, Egypt", "lat": 30.0444, "lon": 31.2357},
    {"slug": "alexandria", "name": "Alexandria, Egypt", "lat": 31.2001, "lon": 29.9187},
    {"slug": "aswan", "name": "Aswan, Egypt", "lat": 24.0889, "lon": 32.8998},
]
CITIES_DIR = DATA / "cities"
APP_MODELS_DIR = BASE / "django_app" / "models"
