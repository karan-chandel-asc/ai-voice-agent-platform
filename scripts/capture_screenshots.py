"""Capture README screenshots of the Deskline UI (updated theme)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 1440, "height": 900}

PAGES = [
    ("01-landing-page.png", "/", False, None),
    ("02-platform-features.png", "/", False, "features"),  # scroll to features
    ("03-login.png", "/api/auth/login/", False, None),
    ("04-operations-dashboard.png", "/api/dashboard/voice-dashboard/", True, None),
    ("05-analytics.png", "/api/monitoring/voice-analytics/", True, None),
    ("06-my-agents.png", "/api/agents/voice-agents/", True, None),
    ("07-my-tools.png", "/api/knowledge/voice-knowledge-base/", True, None),
    ("08-call-history.png", "/api/calls/voice-call-history/", True, None),
    ("09-integrations.png", "/api/integrations/voice-integrations/", True, None),
    ("10-bookings.png", "/api/dashboard/bookings/", True, None),
]


def login_tokens():
    for email, password in (
        ("demo@deskline.io", "demo1234"),
        ("demo@deskline.io", "Demo1234"),
        ("admin@deskline.io", "admin1234"),
    ):
        try:
            r = requests.post(
                f"{BASE}/api/auth/login/api/",
                json={"email": email, "password": password},
                timeout=20,
            )
            data = r.json()
            if data.get("success") and data.get("data", {}).get("access"):
                print(f"Logged in as {email}")
                return data["data"]["access"], data["data"].get("refresh", "")
            print(f"Login failed for {email}: {data.get('message')}")
        except Exception as e:
            print(f"Login error for {email}: {e}")
    return None, None


def inject_auth(page, access, refresh):
    page.add_init_script(
        f"""
        localStorage.setItem('access_token', {json.dumps(access)});
        localStorage.setItem('refresh_token', {json.dumps(refresh or '')});
        sessionStorage.setItem('access_token', {json.dumps(access)});
        sessionStorage.setItem('refresh_token', {json.dumps(refresh or '')});
        """
    )


def shot(page, name, url, auth, mode, access, refresh):
    path = OUT / name
    context_kwargs = {"viewport": VIEWPORT}
    # fresh context when auth changes is handled outside
    page.set_viewport_size(VIEWPORT)
    page.goto(f"{BASE}{url}", wait_until="domcontentloaded", timeout=60000)
    time.sleep(1.2)

    if mode == "features":
        # try common anchors / sections on landing
        for sel in ("#features", "[id*='feature']", "text=Platform", "text=Features"):
            try:
                loc = page.locator(sel).first
                if loc.count():
                    loc.scroll_into_view_if_needed(timeout=2000)
                    time.sleep(0.6)
                    break
            except Exception:
                pass
        else:
            page.evaluate("window.scrollTo(0, Math.min(900, document.body.scrollHeight))")
            time.sleep(0.5)

    # wait for loading placeholders to settle on auth pages
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    time.sleep(1.0)

    page.screenshot(path=str(path), full_page=False)
    print(f"Saved {path.name} ({path.stat().st_size // 1024} KB)")


def main():
    access, refresh = login_tokens()
    if not access:
        print("WARNING: could not login — auth pages may redirect to login")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # public pages
        ctx_public = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page_pub = ctx_public.new_page()

        # authed pages
        ctx_auth = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        if access:
            ctx_auth.add_init_script(
                f"""
                localStorage.setItem('access_token', {json.dumps(access)});
                localStorage.setItem('refresh_token', {json.dumps(refresh or '')});
                sessionStorage.setItem('access_token', {json.dumps(access)});
                sessionStorage.setItem('refresh_token', {json.dumps(refresh or '')});
                """
            )
        page_auth = ctx_auth.new_page()

        for name, url, needs_auth, mode in PAGES:
            page = page_auth if needs_auth else page_pub
            try:
                shot(page, name, url, needs_auth, mode, access, refresh)
            except Exception as e:
                print(f"FAILED {name}: {e}")

        # agent create page if agents exist
        try:
            page_auth.goto(f"{BASE}/api/agents/voice-create-agent/", wait_until="domcontentloaded")
            time.sleep(1.5)
            try:
                page_auth.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass
            page_auth.screenshot(path=str(OUT / "12-create-agent.png"), full_page=False)
            print("Saved 12-create-agent.png")
        except Exception as e:
            print(f"create-agent skip: {e}")

        browser.close()

    print("Done ->", OUT)


if __name__ == "__main__":
    main()
