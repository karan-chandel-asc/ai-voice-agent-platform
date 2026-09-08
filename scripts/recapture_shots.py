"""Re-capture a few targeted screenshots."""
import json
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

r = requests.post(
    f"{BASE}/api/auth/login/api/",
    json={"email": "demo@deskline.io", "password": "demo1234"},
    timeout=20,
)
tok = r.json()["data"]
access, refresh = tok["access"], tok.get("refresh", "")

auth_js = f"""
localStorage.setItem('access_token', {json.dumps(access)});
localStorage.setItem('refresh_token', {json.dumps(refresh)});
sessionStorage.setItem('access_token', {json.dumps(access)});
sessionStorage.setItem('refresh_token', {json.dumps(refresh)});
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # Features section on landing
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{BASE}/#product", wait_until="domcontentloaded")
    time.sleep(1.2)
    try:
        page.locator("#product").first.scroll_into_view_if_needed()
    except Exception:
        page.evaluate("document.getElementById('product')?.scrollIntoView()")
    time.sleep(0.8)
    page.screenshot(path=str(OUT / "02-platform-features.png"))
    print("02-platform-features.png")

    # Also hospitality section as alternate if product is thin
    page.goto(f"{BASE}/#hospitality", wait_until="domcontentloaded")
    time.sleep(1.0)
    try:
        page.locator("#hospitality").first.scroll_into_view_if_needed()
    except Exception:
        pass
    time.sleep(0.6)
    page.screenshot(path=str(OUT / "02b-hospitality.png"))
    print("02b-hospitality.png")
    page.close()

    # Authed pages
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(auth_js)
    page = ctx.new_page()

    # Agent detail — pick first agent from list API
    agents = requests.get(
        f"{BASE}/api/agents/agent-list-api/?page_size=1",
        headers={"Authorization": f"Bearer {access}"},
        timeout=20,
    ).json()
    agent_id = None
    try:
        agent_id = (agents.get("results") or {}).get("data", [{}])[0].get("id")
    except Exception:
        pass
    if not agent_id:
        # fallback parse
        data = agents.get("results", agents.get("data"))
        if isinstance(data, dict):
            data = data.get("data") or []
        if isinstance(data, list) and data:
            agent_id = data[0].get("id")

    if agent_id:
        page.goto(
            f"{BASE}/api/agents/voice-agent-detail/?pk={agent_id}",
            wait_until="domcontentloaded",
        )
        time.sleep(2.0)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.screenshot(path=str(OUT / "11-agent-detail.png"))
        print("11-agent-detail.png", agent_id)
    else:
        print("No agent id for detail shot")

    # Knowledge base again with wait
    page.goto(f"{BASE}/api/knowledge/voice-knowledge-base/", wait_until="domcontentloaded")
    time.sleep(2.5)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.screenshot(path=str(OUT / "07-my-tools.png"))
    print("07-my-tools.png")

    # Agents list again
    page.goto(f"{BASE}/api/agents/voice-agents/", wait_until="domcontentloaded")
    time.sleep(2.5)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.screenshot(path=str(OUT / "06-my-agents.png"))
    print("06-my-agents.png")

    browser.close()
print("OK")
