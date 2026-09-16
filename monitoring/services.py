"""Helpers for Deskline outreach visit tracking."""
from __future__ import annotations

import json
import urllib.request
from datetime import timedelta

from django.utils import timezone

from core.logger import logger

from .models import ProjectVisit

# Public pages that count as "opened the project" for outreach.
TRACKED_PATHS = {
    "/",
    "/api/auth/login/",
    "/api/auth/forgot-password/",
}

BOT_HINTS = (
    "bot",
    "crawl",
    "spider",
    "slurp",
    "facebookexternalhit",
    "preview",
    "wget",
    "curl",
    "python-requests",
    "httpclient",
    "monitoring",
    "uptime",
)


def client_ip(request) -> str | None:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    real_ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real_ip:
        return real_ip
    return request.META.get("REMOTE_ADDR") or None


def is_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(h in ua for h in BOT_HINTS)


def should_track(request) -> bool:
    if request.method != "GET":
        return False
    path = request.path or "/"
    if path not in TRACKED_PATHS:
        return False
    ua = request.META.get("HTTP_USER_AGENT", "")
    if is_bot(ua):
        return False
    return True


def _headers_country(request) -> str:
    """Prefer CDN country headers when present (Cloudflare / similar)."""
    code = (
        request.META.get("HTTP_CF_IPCOUNTRY")
        or request.META.get("HTTP_X_COUNTRY_CODE")
        or request.META.get("HTTP_X_VERCEL_IP_COUNTRY")
        or ""
    ).strip().upper()
    if code and code not in ("XX", "T1", "UNKNOWN"):
        return code
    return ""


def _cache_get(key):
    try:
        from django.core.cache import cache
        return cache.get(key)
    except Exception:
        return None


def _cache_set(key, value, timeout):
    try:
        from django.core.cache import cache
        cache.set(key, value, timeout)
    except Exception:
        pass


def lookup_geo(ip: str | None) -> dict:
    """Resolve country/city for an IP. Cached 24h. Never raises."""
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return {"country": "Local", "country_code": "LO", "city": ""}

    cache_key = f"deskline:geo:{ip}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict):
        return cached

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city"
        req = urllib.request.Request(url, headers={"User-Agent": "DesklineVisitTracker/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore") or "{}")
        if data.get("status") == "success":
            result = {
                "country": data.get("country") or "Unknown",
                "country_code": data.get("countryCode") or "",
                "city": data.get("city") or "",
            }
            _cache_set(cache_key, result, 60 * 60 * 24)
            return result
    except Exception as exc:
        logger.warning(f"[VISIT] geo lookup failed for {ip}: {exc}")

    result = {"country": "Unknown", "country_code": "", "city": ""}
    _cache_set(cache_key, result, 60 * 30)
    return result


def record_visit(request) -> ProjectVisit | None:
    """Persist one outreach visit for the current request."""
    if not should_track(request):
        return None

    ip = client_ip(request)
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
    referrer = (request.META.get("HTTP_REFERER") or "")[:500]
    path = request.path or "/"

    # Light dedupe: same IP + path within 30 minutes → skip
    if ip:
        since = timezone.now() - timedelta(minutes=30)
        exists = ProjectVisit.objects.filter(
            ip_address=ip,
            path=path,
            visited_at__gte=since,
        ).exists()
        if exists:
            return None

    code = _headers_country(request)
    geo = lookup_geo(ip)
    country = geo.get("country") or "Unknown"
    country_code = code or geo.get("country_code") or ""
    city = geo.get("city") or ""

    visit = ProjectVisit.objects.create(
        ip_address=ip,
        country=country,
        country_code=country_code,
        city=city,
        path=path,
        referrer=referrer,
        user_agent=ua,
    )
    logger.info(f"[VISIT] {ip} · {country} · {path}")
    return visit
