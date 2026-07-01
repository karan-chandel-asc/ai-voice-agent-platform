"""
Browser-based calling — no phone / no ISD pack needed.
Open http://localhost:8001/relay/dialer in your browser, pick an agent, and click Call.

Twilio.js makes a VoIP call over the internet directly to your agent.
The browser call goes through the FULL pipeline (agent lookup, call log, session, tools, KB).

Setup:
  1. Go to Twilio Console → Explore Products → Voice → TwiML Apps
  2. Create a TwiML App
     Voice Request URL: https://<ngrok>.ngrok.io/relay/browser-outbound   (POST)
  3. Copy the TwiML App SID → set TWILIO_TWIML_APP_SID in .env
  4. Go to API Keys → Create API Key (Standard) → copy SID + Secret
     Set TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET in .env
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse, Response
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from core.logger import logger
from .db import get_live_agents, get_agent_by_id, create_call_log, get_demo_agent
from ..config import settings
from .utils import store_call_session

_base   = settings.FASTAPI_BASE_URL.rstrip("/")
_ws_url = _base.replace("https://", "wss://").replace("http://", "ws://") + "/relay/ws"

router = APIRouter(prefix="/relay", tags=["browser-call"])

TWIML_APP_SID   = settings.TWILIO_APP_SID
API_KEY_SID     = settings.TWILIO_API_KEY_SID
API_KEY_SECRET  = settings.TWILIO_API_KEY_SECRET

DEFAULT_VOICES = {
    "en": "en-US-Neural2-F",
    "es": "es-ES-Neural2-A",
    "fr": "fr-FR-Neural2-A",
    "de": "de-DE-Neural2-A",
    "hi": "hi-IN-Neural2-A",
    "pt": "pt-BR-Neural2-A",
}


@router.get("/token")
async def get_token(request: Request):
    """Generate a short-lived Twilio Access Token for the browser client."""
    logger.info(f"[TOKEN] Request from origin={request.headers.get('origin','?')}  host={request.headers.get('host','?')}")
    logger.info(f"[TOKEN] TWIML_APP_SID={TWIML_APP_SID!r}  API_KEY_SID={API_KEY_SID!r}")

    if not TWIML_APP_SID or not API_KEY_SID or not API_KEY_SECRET:
        logger.error("[TOKEN] Missing Twilio credentials — check TWILIO_APP_SID / TWILIO_API_KEY_SID / TWILIO_API_KEY_SECRET in .env")
        return JSONResponse({"error": "Missing Twilio credentials on server"}, status_code=500)

    try:
        token = AccessToken(
            settings.TWILIO_ACCOUNT_SID,
            API_KEY_SID,
            API_KEY_SECRET,
            identity="browser-user",
            ttl=3600,
        )
        grant = VoiceGrant(
            outgoing_application_sid=TWIML_APP_SID,
            incoming_allow=False,
        )
        token.add_grant(grant)
        jwt = token.to_jwt()
        logger.info(f"[TOKEN] Issued OK — identity=browser-user  ttl=3600  app={TWIML_APP_SID}")
        return JSONResponse({"token": jwt})
    except Exception as e:
        logger.error(f"[TOKEN] Failed to generate token: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/demo-token")
async def get_demo_token():
    """Public token for the homepage live demo — no auth required."""
    agent = await get_demo_agent()
    demo_agent_id = agent["agent_id"] if agent else None

    token = AccessToken(
        settings.TWILIO_ACCOUNT_SID,
        API_KEY_SID,
        API_KEY_SECRET,
        identity="demo-guest",
        ttl=1800,
    )
    grant = VoiceGrant(
        outgoing_application_sid=TWIML_APP_SID,
        incoming_allow=False,
    )
    token.add_grant(grant)
    return JSONResponse({"token": token.to_jwt(), "agent_id": demo_agent_id})


@router.get("/agents")
async def list_agents():
    """Return all live agents for the dialer dropdown."""
    agents = await get_live_agents()
    return JSONResponse(agents)


@router.post("/browser-outbound")
async def browser_outbound(
    CallSid: str  = Form(default=""),
    From:    str  = Form(default="browser-user"),
    AgentId: str  = Form(default=""),
):
    """
    TwiML returned when browser client places a call.
    Mirrors InboundWebhookForCalls: agent lookup → call log → session → TwiML.
    """
    logger.info(f"[OUTBOUND] ──────────────────────────────────────────")
    logger.info(f"[OUTBOUND] CallSid={CallSid!r}  From={From!r}  AgentId={AgentId!r}")

    # ── Step 1: agent lookup ──────────────────────────────────
    agent = None
    if AgentId:
        try:
            agent = await get_agent_by_id(AgentId)
            if agent:
                logger.info(f"[OUTBOUND] Agent found: name={agent.get('agent_name')!r}  id={agent.get('agent_id')!r}")
            else:
                logger.error(f"[OUTBOUND] get_agent_by_id returned None for AgentId={AgentId!r} — agent may not be LIVE or doesn't exist")
        except Exception as e:
            logger.error(f"[OUTBOUND] Agent lookup EXCEPTION: {e}", exc_info=True)
    else:
        logger.warning(f"[OUTBOUND] No AgentId received in form POST — TwiML App params not forwarded")

    # ── Step 2: create call log ───────────────────────────────
    if CallSid:
        try:
            await create_call_log(
                call_sid    = CallSid,
                from_number = From,
                agent_id    = agent["agent_id"] if agent else None,
            )
            logger.info(f"[OUTBOUND] CallLog created for CallSid={CallSid}")
        except Exception as e:
            logger.error(f"[OUTBOUND] CallLog creation FAILED: {e}", exc_info=True)

        if agent:
            try:
                await store_call_session(CallSid, agent)
                logger.info(f"[OUTBOUND] Session stored in Redis — key=call_session:{CallSid}  agent={agent['agent_name']!r}")
            except Exception as e:
                logger.error(f"[OUTBOUND] Redis store_call_session FAILED: {e}", exc_info=True)
    else:
        logger.warning("[OUTBOUND] No CallSid received — cannot create call log or store session")

    # ── Step 3: build TwiML ───────────────────────────────────
    if agent:
        agent_name       = agent.get("agent_name", "your assistant")
        language         = agent.get("language") or "en"
        voice            = DEFAULT_VOICES.get(language, "en-US-Neural2-F")
        deepgram_model   = "nova-2-phonecall" if language.startswith("en") else "nova-2"
        welcome_greeting = f"Hello! Thank you for calling. This is {agent_name}. May I have your name please?"
    else:
        agent_name       = "AI Assistant"
        language         = "en"
        voice            = "en-US-Neural2-F"
        deepgram_model   = "nova-2-phonecall"
        welcome_greeting = "Hello! Thank you for calling. How can I help you today?"

    agent_id_param    = agent["agent_id"] if agent else ""
    ws_url_with_agent = f"{_ws_url}?agent_id={agent_id_param}"

    logger.info(f"[OUTBOUND] WS URL → {ws_url_with_agent}")
    logger.info(f"[OUTBOUND] Voice={voice!r}  Language={language!r}  Greeting={welcome_greeting!r}")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <ConversationRelay
      url="{ws_url_with_agent}"
      welcomeGreeting="{welcome_greeting}"
      voice="{voice}"
      transcriptionProvider="deepgram"
      speechModel="{deepgram_model}"
      language="{language}"
      interruptible="true"
    />
  </Connect>
</Response>"""
    logger.info(f"[OUTBOUND] Returning TwiML OK")
    return Response(content=twiml, media_type="application/xml")
