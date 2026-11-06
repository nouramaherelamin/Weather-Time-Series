"""Input validation shared by the web form, the JSON API and the CSV batch upload. Pure Python (no Django)."""
import datetime as dt
import math

# name: (min, max, unit, label)
LIMITS = {
    "temperature": (-10.0, 55.0, "°C", "Mean temperature"),
    "humidity": (0.0, 100.0, "%", "Mean relative humidity"),
    "wind_speed": (0.0, 150.0, "km/h", "Mean wind speed"),
    "pressure": (900.0, 1100.0, "hPa", "Mean surface pressure"),
}
INPUTS = list(LIMITS)
REQUIRED = INPUTS + ["date"]


def parse_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def validate_inputs(raw):
    """raw: mapping with temperature/humidity/wind_speed/pressure/date -> (clean, errors)."""
    clean, errors = {}, {}
    for name, (lo, hi, unit, label) in LIMITS.items():
        v = raw.get(name)
        if v is None or str(v).strip() == "":
            errors[name] = "Please enter a value."
            continue
        try:
            x = float(str(v).strip())
        except ValueError:
            errors[name] = "Enter a valid number."
            continue
        if not math.isfinite(x):
            errors[name] = "Enter a valid number."
        elif x < lo or x > hi:
            errors[name] = f"{label} must be between {lo:g} and {hi:g} {unit}."
        else:
            clean[name] = x
    d = raw.get("date")
    if d is None or str(d).strip() == "":
        errors["date"] = "Please enter a date."
    else:
        try:
            clean["date"] = parse_date(d)
        except ValueError:
            errors["date"] = "Use the format YYYY-MM-DD."
    return clean, errors
