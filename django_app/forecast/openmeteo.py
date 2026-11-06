"""Fetch the most recent REAL observations for a city from Open-Meteo (no API key). Pure Python (needs `requests`)."""
import datetime as dt
from collections import defaultdict

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = "temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure"


class UpstreamError(Exception):
    """The weather provider is unreachable or returned unusable data."""


def summarize(payload, today=None, min_hours=20, history_days=30):
    """Hourly payload -> daily means for COMPLETE UTC days (before `today`). Returns the latest day + a short history."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    try:
        h = payload["hourly"]
        times = h["time"]
        cols = {"temperature": h["temperature_2m"], "humidity": h["relative_humidity_2m"],
                "wind_speed": h["wind_speed_10m"], "pressure": h["surface_pressure"]}
    except (KeyError, TypeError) as e:
        raise UpstreamError(f"Unexpected response from the weather provider ({e})")
    buckets = defaultdict(lambda: {k: [] for k in cols})
    for i, t in enumerate(times):
        day = dt.date.fromisoformat(t[:10])
        if day >= today:
            continue
        vals = {k: cols[k][i] for k in cols}
        if any(v is None for v in vals.values()):
            continue
        for k, v in vals.items():
            buckets[day][k].append(float(v))
    days = []
    for day in sorted(buckets):
        b = buckets[day]
        if len(b["temperature"]) >= min_hours:
            days.append({"date": day.isoformat(), **{k: round(sum(v) / len(v), 2) for k, v in b.items()}})
    if not days:
        raise UpstreamError("No complete recent day available from the weather provider")
    latest = days[-1]
    return {**latest, "source": "Open-Meteo", "history": [{"date": d["date"], "temperature": d["temperature"]} for d in days[-history_days:]]}


def fetch_latest(lat, lon, http_get=None, timeout=15):
    if http_get is None:
        import requests
        http_get = requests.get
    params = {"latitude": lat, "longitude": lon, "hourly": HOURLY, "past_days": 31, "forecast_days": 1,
              "timezone": "UTC", "temperature_unit": "celsius", "wind_speed_unit": "kmh"}
    try:
        r = http_get(FORECAST_URL, params=params, timeout=timeout)
        r.raise_for_status()
        return summarize(r.json())
    except UpstreamError:
        raise
    except Exception as e:
        raise UpstreamError(f"Could not reach the weather provider: {e.__class__.__name__}")
