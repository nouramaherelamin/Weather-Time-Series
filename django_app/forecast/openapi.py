"""OpenAPI 3 description of the JSON API (served at /api/openapi.json and rendered by Swagger UI). Pure Python."""
from .validation import LIMITS


def build_spec(city_slugs, model_keys, version="2.0.0"):
    num = lambda n: {"name": n, "in": "query", "required": True, "description": LIMITS[n][3] + f" ({LIMITS[n][2]})",
                     "schema": {"type": "number", "minimum": LIMITS[n][0], "maximum": LIMITS[n][1]}}
    common = [num("temperature"), num("humidity"), num("wind_speed"), num("pressure"),
              {"name": "date", "in": "query", "required": True, "description": "Date of the readings (YYYY-MM-DD)",
               "schema": {"type": "string", "format": "date"}},
              {"name": "city", "in": "query", "required": False, "schema": {"type": "string", "enum": city_slugs, "default": city_slugs[0]}},
              {"name": "model", "in": "query", "required": False, "description": "'best' = the most accurate model for day 1",
               "schema": {"type": "string", "enum": ["best"] + model_keys, "default": "best"}}]
    day = {"type": "object", "properties": {"day": {"type": "integer"}, "date": {"type": "string", "format": "date"},
           "prediction": {"type": "number"}, "low": {"type": "number"}, "high": {"type": "number"}, "normal": {"type": "number"}}}
    pred = {"type": "object", "properties": {
        "city": {"type": "string"}, "model": {"type": "string"}, "start_date": {"type": "string"},
        "prediction": {"type": "number", "description": "Tomorrow's mean temperature (°C)"},
        "low": {"type": "number"}, "high": {"type": "number"}, "forecast": {"type": "array", "items": day, "description": "Days +1 … +7"},
        "explain": {"type": "array", "items": {"type": "object", "properties": {"feature": {"type": "string"}, "effect": {"type": "number"}}}},
        "outside_training_range": {"type": "array", "items": {"type": "string"}}}}
    err = {"type": "object", "properties": {"errors": {"type": "object"}}}
    errors = {"400": {"description": "Validation error", "content": {"application/json": {"schema": err}}},
              "429": {"description": "Rate limit exceeded (see Retry-After header)"}}
    return {
        "openapi": "3.0.3",
        "info": {"title": "Atmos Weather Predictor API", "version": version,
                 "description": "Predict the next 7 days of mean temperature from today's mean weather readings. © Noura Maher Elamin."},
        "paths": {
            "/api/predict/": {
                "get": {"summary": "Predict (query string)", "parameters": common,
                        "responses": {"200": {"description": "Forecast", "content": {"application/json": {"schema": pred}}}, **errors}},
                "post": {"summary": "Predict (form fields)", "requestBody": {"content": {"application/x-www-form-urlencoded": {"schema": {
                    "type": "object", "required": ["temperature", "humidity", "wind_speed", "pressure", "date"],
                    "properties": {p["name"]: p["schema"] for p in common}}}}},
                    "responses": {"200": {"description": "Forecast", "content": {"application/json": {"schema": pred}}}, **errors}}},
            "/api/latest/": {"get": {"summary": "Latest REAL daily readings for a city (Open-Meteo)",
                                     "parameters": [common[5]],
                                     "responses": {"200": {"description": "Latest complete day + 30-day history"},
                                                   "502": {"description": "Weather provider unavailable"}, "429": errors["429"]}}},
            "/api/batch/": {"post": {"summary": "Batch prediction from a CSV file", "description":
                            "CSV columns: date,temperature,humidity,wind_speed,pressure (optional: city,model). Max 1000 rows / 1 MB. Add ?format=csv to get a CSV back.",
                            "requestBody": {"content": {"multipart/form-data": {"schema": {"type": "object", "properties": {
                                "file": {"type": "string", "format": "binary"}}}}}},
                            "responses": {"200": {"description": "Per-row predictions"}, "400": errors["400"], "429": errors["429"]}}},
            "/api/models/": {"get": {"summary": "Available cities and models with their hold-out accuracy", "responses": {"200": {"description": "OK"}}}},
            "/api/health/": {"get": {"summary": "Health check", "responses": {"200": {"description": "OK"}}}},
        },
    }
