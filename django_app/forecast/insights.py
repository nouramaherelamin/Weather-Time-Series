"""Climate insights computed from the bundled 10-year daily history. Pure Python + numpy/pandas (no Django)."""
import numpy as np
import pandas as pd

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _color(v, lo, hi):
    """blue -> yellow -> red scale as a CSS rgb() string."""
    t = 0.5 if hi == lo else min(max((v - lo) / (hi - lo), 0), 1)
    stops = [(59, 130, 246), (250, 204, 21), (239, 68, 68)]
    a, b, u = (stops[0], stops[1], t * 2) if t < .5 else (stops[1], stops[2], (t - .5) * 2)
    return "rgb(%d,%d,%d)" % tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))


def compute(history, climatology):
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    t = df["temperature"]
    clim = pd.Series(climatology, index=range(1, 367))
    anomaly = t - clim.reindex(t.index.dayofyear).values
    slope = float(np.polyfit(np.arange(len(anomaly)) / 3652.5, anomaly.values, 1)[0])          # °C per decade

    by_month = t.groupby(t.index.month)
    monthly = {"labels": MONTHS, "mean": [round(float(by_month.mean()[m]), 2) for m in range(1, 13)],
               "p10": [round(float(by_month.quantile(.1)[m]), 2) for m in range(1, 13)],
               "p90": [round(float(by_month.quantile(.9)[m]), 2) for m in range(1, 13)]}
    rain = None
    if "precipitation" in df:
        per_month = df["precipitation"].resample("MS").sum()
        avg = per_month.groupby(per_month.index.month).mean()
        rain = {"labels": MONTHS, "mm": [round(float(avg.get(m, 0.0)), 1) for m in range(1, 13)]}
    annual = t.groupby(t.index.year).agg(["mean", "count"])
    annual = annual[annual["count"] >= 300]                                       # full years only
    yearly = {"labels": [str(y) for y in annual.index], "mean": [round(float(v), 2) for v in annual["mean"]]}

    last = t.iloc[-365:]
    recent = {"labels": [d.strftime("%Y-%m-%d") for d in last.index], "temp": [round(float(v), 2) for v in last],
              "avg30": [None if np.isnan(v) else round(float(v), 2) for v in last.rolling(30).mean()],
              "normal": [round(float(clim[d.dayofyear]), 2) for d in last.index]}

    pivot = t.groupby([t.index.year, t.index.month]).mean().unstack()
    lo, hi = float(np.nanmin(pivot.values)), float(np.nanmax(pivot.values))
    heat = [{"year": int(y), "cells": [None if np.isnan(v) else {"v": round(float(v), 1), "c": _color(v, lo, hi)} for v in row]}
            for y, row in zip(pivot.index, pivot.values)]

    kpis = {"mean": round(float(t.mean()), 1), "hottest": round(float(t.max()), 1), "hottest_date": t.idxmax().date().isoformat(),
            "coldest": round(float(t.min()), 1), "coldest_date": t.idxmin().date().isoformat(),
            "trend_per_decade": round(slope, 2), "years": round(len(t) / 365.25, 1)}
    if "precipitation" in df:
        wet = df["precipitation"].idxmax()
        kpis.update(wettest=round(float(df["precipitation"].max()), 1), wettest_date=wet.date().isoformat(),
                    rainy_days_per_year=round(float((df["precipitation"] >= 1).sum() / (len(df) / 365.25)), 1))
    return {"monthly": monthly, "rain": rain, "yearly": yearly, "recent": recent, "heat": heat, "months": MONTHS, "kpis": kpis}
