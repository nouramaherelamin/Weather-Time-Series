"""CSV batch prediction helpers. Pure Python (no Django)."""
import csv
import io

from .validation import REQUIRED, validate_inputs

MAX_BYTES, MAX_ROWS = 1_000_000, 1000
SAMPLE_CSV = ("date,temperature,humidity,wind_speed,pressure\n"
              "2026-04-14,23.5,48,11.2,1011.8\n2026-07-20,34.1,40,15.0,1006.3\n2026-12-02,16.8,62,9.5,1016.0\n")


class BatchError(ValueError):
    pass


def parse_csv(data):
    if len(data) > MAX_BYTES:
        raise BatchError("File is too large (max 1 MB).")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BatchError("File must be UTF-8 encoded CSV.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise BatchError("The CSV is empty.")
    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
    missing = [c for c in REQUIRED if c not in reader.fieldnames]
    if missing:
        raise BatchError("Missing column(s): " + ", ".join(missing) + ". Required: " + ", ".join(REQUIRED) + ".")
    rows = []
    for line, row in enumerate(reader, start=2):
        if len(rows) >= MAX_ROWS:
            raise BatchError(f"Too many rows (max {MAX_ROWS}).")
        if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
            continue                                              # skip blank lines
        rows.append((line, {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}))
    if not rows:
        raise BatchError("The CSV has a header but no data rows.")
    return rows


def run_batch(rows, predict_fn, city, model, valid_cities, valid_models):
    """predict_fn(slug, model, t, h, w, p, date) -> result dict. Returns a list of flat result dicts."""
    out = []
    for line, raw in rows:
        slug = (raw.get("city") or city or "").strip().lower() or city
        mdl = (raw.get("model") or model or "best").strip().lower()
        base = {"line": line, "city": slug, "model": mdl, **{k: raw.get(k, "") for k in REQUIRED}}
        clean, errors = validate_inputs(raw)
        if slug not in valid_cities:
            errors["city"] = f"Unknown city '{slug}'."
        if mdl != "best" and mdl not in valid_models:
            errors["model"] = f"Unknown model '{mdl}'."
        if errors:
            out.append({**base, "status": "error", "error": "; ".join(f"{k}: {v}" for k, v in errors.items())})
            continue
        r = predict_fn(slug, mdl, clean["temperature"], clean["humidity"], clean["wind_speed"], clean["pressure"], clean["date"])
        flat = {**base, "model": r["model"], "status": "ok", "error": "", "low_d1": r["low"], "high_d1": r["high"]}
        for f in r["forecast"]:
            flat[f"pred_d{f['day']}"] = f["prediction"]
        out.append(flat)
    return out


FIELDS = (["line", "status", "error", "city", "model"] + REQUIRED + ["pred_d1", "low_d1", "high_d1"]
          + [f"pred_d{i}" for i in range(2, 8)])


def to_csv(results):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in results:
        w.writerow(r)
    return buf.getvalue()
