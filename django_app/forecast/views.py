import base64
import csv
import datetime as dt
import io
from functools import lru_cache, wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from . import batchio, insights as insights_mod, ml, openmeteo
from .forms import BatchForm, WeatherForm
from .openapi import build_spec
from .ratelimit import rate_limit

HISTORY_KEY, HISTORY_MAX = "hist", 8


# ----------------------------------------------------------------------------- helpers
def _category(t):
    if t < 10: return ("cat_cold", "Cold", "cold", "bi-snow2")
    if t < 20: return ("cat_mild", "Mild", "mild", "bi-cloud-sun-fill")
    if t < 30: return ("cat_warm", "Warm", "warm", "bi-sun-fill")
    return ("cat_hot", "Hot", "hot", "bi-thermometer-sun")


def _ctx(request, active, slug=None):
    ready = ml.is_ready()
    if slug not in {c["slug"] for c in ml.cities()}:      # ignore unknown ?city= values
        slug = None
    ctx = {"active": active, "author": settings.AUTHOR, "ready": ready, "cities": ml.cities() if ready else []}
    if ready:
        b = ml.get_bundle(slug)
        best = ml.model_options(b["city"]["slug"])
        ctx.update(city=b["city"]["name"], city_slug=b["city"]["slug"], coords=f"{b['city']['lat']:.4f}° N, {b['city']['lon']:.4f}° E",
                   trained_through=b["trained_through"], n_years=round(b["n_days"] / 365.25), model_options=best,
                   best_mae=next(o["mae1"] for o in best if o["best"]), best_label=next(o["label"] for o in best if o["best"]))
    return ctx


def requires_model_html(view):
    @wraps(view)
    def wrapper(request, *a, **k):
        if not ml.is_ready():
            return render(request, "forecast/no_model.html", {"active": "", "author": settings.AUTHOR, "ready": False, "cities": []}, status=503)
        return view(request, *a, **k)
    return wrapper


def requires_model_api(view):
    @wraps(view)
    def wrapper(request, *a, **k):
        if not ml.is_ready():
            return JsonResponse({"error": "No trained model found. Run `python train_app_models.py` first."}, status=503)
        return view(request, *a, **k)
    return wrapper


def _run(cd):
    slug = cd.get("city") or ml.get_bundle()["city"]["slug"]
    return ml.predict(slug, cd.get("model") or "best", cd["temperature"], cd["humidity"], cd["wind_speed"], cd["pressure"], cd["date"])


def _remember(request, result, cd):
    hist = list(request.session.get(HISTORY_KEY, []))
    hist.insert(0, {"ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "c": result["city_slug"], "m": result["model"],
                    "d": result["start_date"], "t": cd["temperature"], "h": cd["humidity"], "w": cd["wind_speed"],
                    "p": cd["pressure"], "y": result["prediction"], "lo": result["low"], "hi": result["high"]})
    request.session[HISTORY_KEY] = hist[:HISTORY_MAX]
    request.session.modified = True


def _history(request):
    return request.session.get(HISTORY_KEY, [])


def _decorate(result, temperature):
    key, label, css, icon = _category(result["prediction"])
    result.update(cat_key=key, label=label, css=css, icon=icon)
    for f in result["forecast"]:
        f["cat_key"], f["cat_label"], f["css"], f["icon"] = _category(f["prediction"])
    result["chart"] = {"start_date": result["start_date"], "start_value": temperature, "city_slug": result["city_slug"],
                       "dates": [f["date"] for f in result["forecast"]], "pred": [f["prediction"] for f in result["forecast"]],
                       "low": [f["low"] for f in result["forecast"]], "high": [f["high"] for f in result["forecast"]],
                       "normal": [f["normal"] for f in result["forecast"]]}
    return result


# ----------------------------------------------------------------------------- pages
@requires_model_html
def index(request):
    result, slug = None, None
    if request.method == "POST":
        form = WeatherForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            result = _decorate(_run(cd), cd["temperature"])
            _remember(request, result, cd)
            slug = result["city_slug"]
    else:
        form = WeatherForm()
    ctx = _ctx(request, "home", slug or request.POST.get("city") or request.GET.get("city"))
    ctx.update(form=form, result=result, history=_history(request))
    return render(request, "forecast/index.html", ctx)


@lru_cache(maxsize=16)
def _insights(slug, trained_through):
    b = ml.get_bundle(slug)
    return insights_mod.compute(b["history"], b["climatology"])


@requires_model_html
def insights(request):
    b = ml.get_bundle(request.GET.get("city") if request.GET.get("city") in [c["slug"] for c in ml.cities()] else None)
    ctx = _ctx(request, "insights", b["city"]["slug"])
    ctx["ins"] = _insights(b["city"]["slug"], b["trained_through"])
    return render(request, "forecast/insights.html", ctx)


@requires_model_html
def about(request):
    ctx = _ctx(request, "about", request.GET.get("city") if request.GET.get("city") in [c["slug"] for c in ml.cities()] else None)
    ctx["comparison"] = ml.comparison(ctx["city_slug"])
    ctx["rows"] = [{"label": k, "values": v} for k, v in ml.comparison(ctx["city_slug"])["series"].items()]
    return render(request, "forecast/about.html", ctx)


@requires_model_html
def batch(request):
    ctx = _ctx(request, "batch", request.POST.get("city") or request.GET.get("city"))
    results = None
    if request.method == "POST":
        form = BatchForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            try:
                rows = batchio.parse_csv(f.read())
                valid_models = [o["key"] for o in ml.model_options()]
                results = batchio.run_batch(rows, ml.predict, form.cleaned_data["city"] or ml.get_bundle()["city"]["slug"],
                                            form.cleaned_data["model"] or "best", [c["slug"] for c in ml.cities()], valid_models)
            except batchio.BatchError as e:
                form.add_error("file", str(e))
        if results is not None:
            text = batchio.to_csv(results)
            ok = sum(1 for r in results if r["status"] == "ok")
            ctx.update(results=results[:100], total=len(results), ok=ok, failed=len(results) - ok,
                       csv_b64=base64.b64encode(text.encode()).decode(), truncated=len(results) > 100)
    else:
        form = BatchForm()
    ctx["form"] = form
    return render(request, "forecast/batch.html", ctx)


def batch_sample(request):
    r = HttpResponse(batchio.SAMPLE_CSV, content_type="text/csv")
    r["Content-Disposition"] = 'attachment; filename="sample_batch.csv"'
    return r


def history_export(request):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time_utc", "city", "model", "date", "temperature", "humidity", "wind_speed", "pressure", "pred_tomorrow", "low", "high"])
    for h in _history(request):
        w.writerow([h["ts"], h["c"], h["m"], h["d"], h["t"], h["h"], h["w"], h["p"], h["y"], h["lo"], h["hi"]])
    r = HttpResponse(buf.getvalue(), content_type="text/csv")
    r["Content-Disposition"] = 'attachment; filename="prediction_history.csv"'
    return r


@require_POST
def history_clear(request):
    request.session.pop(HISTORY_KEY, None)
    return redirect("index")


def api_docs(request):
    return render(request, "forecast/api.html", _ctx(request, "api") if ml.is_ready() else
                  {"active": "api", "author": settings.AUTHOR, "ready": False, "cities": [], "city": "", "model_options": []})


def swagger(request):
    return render(request, "forecast/swagger.html", {"active": "api", "author": settings.AUTHOR, "ready": ml.is_ready(), "cities": []})


# ----------------------------------------------------------------------------- JSON API
def openapi(request):
    slugs = [c["slug"] for c in ml.cities()] or ["cairo"]
    keys = [o["key"] for o in ml.model_options()] if ml.is_ready() else ["ridge", "gbr", "rf"]
    return JsonResponse(build_spec(slugs, keys))


@csrf_exempt
@rate_limit
@requires_model_api
@require_http_methods(["GET", "POST"])
def api_predict(request):
    form = WeatherForm(request.POST if request.method == "POST" else request.GET)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    return JsonResponse(_run(form.cleaned_data))


@csrf_exempt
@rate_limit
@requires_model_api
@require_http_methods(["GET"])
def api_latest(request):
    slug = request.GET.get("city") or ml.get_bundle()["city"]["slug"]
    try:
        b = ml.get_bundle(slug)
    except KeyError:
        return JsonResponse({"error": f"Unknown city '{slug}'"}, status=400)
    key = f"latest:{slug}"
    data = cache.get(key)
    if data is None:
        try:
            data = openmeteo.fetch_latest(b["city"]["lat"], b["city"]["lon"])
        except openmeteo.UpstreamError as e:
            return JsonResponse({"error": str(e)}, status=502)
        cache.set(key, data, 30 * 60)
    return JsonResponse({**data, "city": b["city"]["name"], "city_slug": slug})


@csrf_exempt
@rate_limit
@requires_model_api
@require_POST
def api_batch(request):
    form = BatchForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    try:
        rows = batchio.parse_csv(form.cleaned_data["file"].read())
    except batchio.BatchError as e:
        return JsonResponse({"error": str(e)}, status=400)
    results = batchio.run_batch(rows, ml.predict, form.cleaned_data["city"] or ml.get_bundle()["city"]["slug"],
                                form.cleaned_data["model"] or "best", [c["slug"] for c in ml.cities()],
                                [o["key"] for o in ml.model_options()])
    if request.GET.get("format") == "csv":
        r = HttpResponse(batchio.to_csv(results), content_type="text/csv")
        r["Content-Disposition"] = 'attachment; filename="predictions.csv"'
        return r
    ok = sum(1 for x in results if x["status"] == "ok")
    return JsonResponse({"count": len(results), "ok": ok, "failed": len(results) - ok, "rows": results})


@rate_limit
@requires_model_api
def api_models(request):
    out = []
    for c in ml.cities():
        out.append({**c, "best_model": ml.get_bundle(c["slug"])["best_model"], "models": ml.model_options(c["slug"]),
                    "mae_by_horizon": ml.comparison(c["slug"])})
    return JsonResponse({"cities": out})


def api_health(request):
    return JsonResponse({"status": "ok" if ml.is_ready() else "no_model", "cities": [c["slug"] for c in ml.cities()]})
