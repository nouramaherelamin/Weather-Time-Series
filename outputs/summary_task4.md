# Task 4 - Summary

**Region / range:** Cairo, Egypt (30.0444, 31.2357); 2016-10-16 to 2026-10-15 - 10 years, 87648 hourly records aggregated to 3652 daily records (UTC).
**API:** Open-Meteo Historical Weather API (`https://archive-api.open-meteo.com/v1/archive`) - free, no key, hourly history back to 1940 by coordinates. Pulled hourly in 10 yearly
requests (raw responses cached in `data/raw_chunks/`), then aggregated to daily (mean temperature/humidity/wind/pressure/cloud, summed precipitation).
Daily granularity over 10 years was chosen because it lets us see yearly seasonality and a long-term trend, which a few months of hourly data cannot.
**Parameters:** {"hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,surface_pressure,cloud_cover", "timezone": "UTC", "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm"}. Rate limits: HTTP 429 is handled with back-off and per-chunk caching.

**Temporal patterns:** daily mean temperature ranges 8.9-36.3 °C (mean 23.4, std 6.5). There is a very strong yearly cycle
(seasonal strength 0.90): hot summers, mild winters, with the spread (volatility) largest in spring/autumn transitions.
After removing the seasonal cycle the trend is +1.62 °C per decade (p=1.16e-42; autocorrelation makes this p-value optimistic).
Precipitation is zero on most days with rare, short winter events (right-skewed); correlation with temperature is -0.12, temperature vs humidity -0.57.

**Stationarity:** temperature ADF p=0.0023, KPSS p=0.1000 - both tests agree the series is stationary. The raw series is not stationary in the
strict sense because of the deterministic yearly cycle; Task 5 removes it (Fourier terms / seasonal differencing) before ARIMA modelling.

**Data quality:** duplicate timestamps = 0; missing hourly timestamps = 0; missing hourly values before cleaning = 0;
physically impossible values = 0; daily rolling-z outliers flagged = {'temperature': 1, 'wind_speed': 2, 'pressure': 0}; remaining missing after cleaning = 0.
Handling: impossible values -> NaN; gaps <=6h time-interpolated, longer gaps seasonal-naive (same hour previous days); precipitation gaps = 0 mm; outliers winsorized to rolling mean +/- 3.5 std (never deleted). Units consistent: °C, mm, km/h, %, hPa.
