# Atmos — Weather Forecasting Project (Tasks 4 → 5 → 6)

10 years (2016-10-16 → 2026-10-15) of weather for **Cairo, Alexandria and Aswan** from the Open-Meteo archive API →
time-series EDA & ARIMA/SARIMA forecasting (notebooks) → a Django web app that serves **3 ML models × 7 forecast days**.

© 2026 Noura Maher Elamin · [LinkedIn](https://www.linkedin.com/in/nouramaherelamin/) · [GitHub](https://github.com/nouramaherelamin)

## 1. Setup (Windows PowerShell)
```powershell
python -m pip install -r requirements.txt
```
(`pmdarima` and `tensorflow` are optional — install them one by one only if you want auto_arima / the LSTM bonus.)

## 2. Run the pipeline — in this order
| Step | Command | Creates |
|---|---|---|
| Task 4 | open **`Task4_Weather_API_EDA.ipynb`** (or `python task4_data_eda.py`) | `data/weather_clean.csv`, plots + summary in `outputs/` |
| Task 5 | open **`Task5_Time_Series_Forecasting.ipynb`** (or `python task5_forecasting.py --skip-lstm`) | ARIMAX/SARIMA results, diagnostics, comparison in `outputs/` |
| App models | `python train_app_models.py` | `django_app/models/<city>.joblib` (downloads Alexandria & Aswan once: ~20 API calls, cached in `data/cities/`) |

If a city fails (e.g. temporary Open-Meteo rate limit) the others are still trained and the script prints the exact command to retry (downloaded years are cached). Check what the app sees with `dir django_app\models`.
`python train_app_models.py --cities cairo` trains only Cairo (no extra downloads); `--fast` trains smaller models for a quick test.
The script also pins pandas/numpy/scikit-learn/joblib in `django_app/requirements.txt` to the versions you trained with (needed for Docker/Render).

## 3. Run the web app
```powershell
cd django_app
python manage.py check_model      # proves the app reproduces the training predictions
python manage.py runserver        # http://127.0.0.1:8000
python manage.py test             # 50+ automated tests (no internet / no trained model needed)
```

## 4. What the app does
- **Home** – form (city, model, today's mean temperature/humidity/wind/pressure, date) → tomorrow's temperature **plus a 7-day outlook**, 95 % range, comparison with the seasonal normal, a chart, and a *"Why this prediction?"* bar chart.
- **Use latest real data** – button that fills the form with yesterday's real readings from Open-Meteo (and draws the last days on the chart).
- **Model dropdown** – Ridge, Gradient Boosting, Random Forest or *Best (auto)*; accuracy of each is on the About page.
- **Prediction history** – last 8 predictions (stored in a signed cookie), downloadable as CSV.
- **Insights** – 10-year climate dashboard (monthly profile, yearly means, last 365 days vs normal, rainfall, heatmap, KPIs).
- **Batch** – upload a CSV (`date,temperature,humidity,wind_speed,pressure`) → predictions for every row, download as CSV.
- **API + Swagger UI** – `/api/predict/`, `/api/latest/`, `/api/batch/`, `/api/models/`, `/api/health/`, docs at `/api/` and `/api/swagger/`, spec at `/api/openapi.json`. Rate limit: 60 requests/minute/IP.
- **City backgrounds** – the page photo changes with the selected city (`static/forecast/<city>.jpg`: Cairo, Alexandria and Aswan included; for a new city save a photo as `django_app/forecast/static/forecast/<slug>.jpg` — without one, the Cairo photo is used).
- **API playground** – edit the parameters, press *Send request* and see the formatted JSON response, with ready-made cURL / Python / JavaScript snippets.
- English / Arabic (RTL) toggle, light / dark mode, responsive layout.

## 5. Docker
```powershell
docker compose up --build        # http://localhost:8000   (train the models first, they are copied into the image)
```

## 6. Deploy publicly (Render — free)
1. Push this folder to GitHub (include `django_app/models/*.joblib`; ~5 MB each).
2. Render → **New + → Blueprint** → select the repo (uses `render.yaml`). Open the generated URL when the build finishes.
3. For any other host: set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<random>`, `DJANGO_ALLOWED_HOSTS=<your-domain>`, `DJANGO_CSRF_ORIGINS=https://<your-domain>`; build `pip install -r django_app/requirements.txt && python manage.py collectstatic --noinput`; start `gunicorn weather_site.wsgi`.

GitHub Actions (`.github/workflows/ci.yml`) runs the test-suite on every push.

## Project structure
```
config.py                      shared settings (cities, dates, paths)
task4_data_eda.py / .ipynb     API download, cleaning, EDA (Task 4)
task5_forecasting.py / .ipynb  stationarity, ARIMA/SARIMA(X), walk-forward, LSTM bonus (Task 5)
train_app_models.py            trains the per-city model bundles for the web app
django_app/
  forecast/trainer.py          model training (3 models × 7 horizons, chronological hold-out)
  forecast/ml.py               model registry (loaded once), prediction, explanation   } pure Python,
  forecast/validation.py       single source of input limits                           } no Django imports
  forecast/openmeteo.py, batchio.py, insights.py, openapi.py                           }
  forecast/forms.py, views.py, urls.py, ratelimit.py   Django glue
  forecast/templates/, static/ UI
  forecast/test_logic.py, test_views.py                tests
```

## Notes on the modelling (for your report)
- Task 5 models the **daily** series with ARIMA + yearly Fourier terms (SARIMA with period 365 is not practical) and a true SARIMA(·)(·,12) on monthly means.
- The web app uses direct multi-horizon models (one model per day +1…+7) because they accept the form inputs (humidity, wind, pressure) — ARIMA/LSTM need the full recent history instead.
- Everything is evaluated on the last 90 days only (chronological split, no leakage) and compared with *persistence* and *seasonal-average* baselines.
