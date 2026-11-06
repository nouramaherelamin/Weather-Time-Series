"""Tiny per-IP rate limiter on top of Django's cache (fixed 60-second window)."""
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "?"))


def rate_limit(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        limit = getattr(settings, "API_RATE_LIMIT", 60)
        window = int(time.time() // 60)
        key = f"rl:{client_ip(request)}:{window}"
        cache.add(key, 0, timeout=70)
        try:
            n = cache.incr(key)
        except ValueError:
            n = 1
        if n > limit:
            r = JsonResponse({"error": "Rate limit exceeded", "limit_per_minute": limit}, status=429)
            r["Retry-After"] = str(60 - int(time.time()) % 60)
            return r
        return view(request, *args, **kwargs)
    return wrapper
