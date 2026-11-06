"""Template context: the background photo follows the selected city (?city=... or the submitted form)."""
from functools import lru_cache

from django.contrib.staticfiles import finders
from django.templatetags.static import static

from . import ml


@lru_cache(maxsize=32)
def _photo(slug):
    """static URL of forecast/<slug>.jpg if that file exists, otherwise the Cairo photo."""
    name = f"forecast/{slug}.jpg"
    return static(name if finders.find(name) else "forecast/cairo.jpg")


def city_background(request):
    slugs = [c["slug"] for c in ml.cities()] or ["cairo"]
    default = "cairo" if "cairo" in slugs else slugs[0]
    wanted = request.POST.get("city") or request.GET.get("city")
    current = wanted if wanted in slugs else default
    return {"backgrounds": {s: _photo(s) for s in slugs}, "bg_current": _photo(current), "bg_default": _photo(default)}
