"""
Twilio Conversation Relay — real agent lookup from DB

HOW TO RUN:
1. Start FastAPI:
       uvicorn voice_engine.main:app --reload --port 8001

2. Expose with ngrok:
       ngrok http 8001

3. In Twilio console set your phone number webhook:
       Voice → Webhook → https://<ngrok-id>.ngrok.io/relay/inbound   (HTTP POST)

4. Call your Twilio number — the AI will answer using the agent assigned to that number.

MODELS:
  llama-3.1-8b-instant      — lowest latency (default)
  llama-3.3-70b-versatile   — best quality + tool use
"""

import json
import asyncio
import time
import asyncpg
import redis.asyncio as redis
from celery import Celery
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import Response, JSONResponse, HTMLResponse
from groq import AsyncGroq
from twilio.rest import Client as TwilioClient
from  core.logger import logger
from pydantic import ValidationError
from .pydantic import TwilioInboundForm
from .db import *
from .utils import *
# from knowledge.pipnecone import PineconeService, embed_texts
from .prompts import (
    FALLBACK_SYSTEM_PROMPT, FALLBACK_SESSION_PROMPT,
    CAPABILITY_NOTE_WITH_TOOLS, CAPABILITY_NOTE_NO_TOOLS,
    SENTIMENT_SYSTEM_PROMPT, OUTCOME_CLASSIFICATION_PROMPT,
)
# _pinecone = PineconeService()

router = APIRouter(prefix="/relay", tags=["relay-test"])

_groq            = AsyncGroq(api_key=settings.GROQ_API_KEY)
GROQ_MODEL       = "llama-3.1-8b-instant"    # fast — used for plain conversation
GROQ_TOOL_MODEL  = "llama-3.3-70b-versatile" # reliable tool calling

# sender-only Celery — just pushes tasks to Redis broker, no Django needed
_celery = Celery(broker=settings.REDIS_URL)

# ── Tool executor: save locally in DB (no external webhooks) ───────────────────
async def execute_tool(name: str, arguments: dict, agent_tools: list[dict], user_tools: list[dict] | None = None) -> str:
    from asgiref.sync import sync_to_async

    if name == "end_call":
        return json.dumps({"end": True})

    if name in ("book_room", "book_hotel_room", "room_booking"):
        from agents.booking_service import save_room_booking
        result = await sync_to_async(save_room_booking)(arguments)
        return json.dumps(result)

    if name in ("book_table", "book_restaurant", "table_booking"):
        from agents.booking_service import save_table_booking
        result = await sync_to_async(save_table_booking)(arguments)
        return json.dumps(result)

    if name == "check_availability":
        return json.dumps({
            "date": arguments.get("date"),
            "slots": ["9:00 AM", "10:30 AM", "2:00 PM", "3:30 PM"],
            "note": "Availability checked locally",
        })

    return json.dumps({"error": f"Unknown tool: {name}"})




def _twiml_hangup(message: str) -> Response:
    twiml = f"<Response><Say>{message}</Say><Hangup/></Response>"
    return Response(content=twiml, media_type="application/xml")


# ── TwiML inbound endpoint
@router.post("/inbound")
async def InboundWebhookForCalls(
        request: Request,
        CallSid: str = Form(...),
        From: str    = Form(...),
        To: str      = Form(...),
    ):
    logger.info(f"[INBOUND] Request received — CallSid={CallSid} From={From} To={To}")

    # ── Step 1: validate form fields
    try:
        form = TwilioInboundForm(call_sid=CallSid, from_number=From, to_number=To)
    except ValidationError as e:
        err = e.errors()[0]["msg"].replace("Value error, ", "")
        logger.warning(f"[INBOUND] Validation failed: {err}")
        return _twiml_hangup("This call could not be processed. Goodbye.")

    # get agent
    agent = await get_agent_by_phone(form.to_number)

    if not agent:
        logger.warning(f"[INBOUND] No live agent for {form.to_number}")
        await create_call_log(
            call_sid    = form.call_sid,
            from_number = form.from_number,
        )
        await update_call_log(
            form.call_sid,
            status   = "failed",
            reason   = "no_agent_configured",
            ended_at = True,
        )
        return _twiml_hangup("Sorry, this number is not currently configured. Goodbye.")

    # ── Step 3: CREATE call log — agent found, call is live
    await create_call_log(
        call_sid    = form.call_sid,
        from_number = form.from_number,
        agent_id    = agent["agent_id"],
    )
    logger.info(f"[INBOUND] CallLog created — Agent={agent['agent_name']} CallSid={form.call_sid}")

    await store_call_session(form.call_sid, agent)

    # ── Step 5: reply with ConversationRelay TwiML ────────────────────────────
    ws_url = settings.relay_ws_url

    # use voice from DB
    language      = agent.get("language") or "en"
    # voice_id      = agent.get("elevenlabs_voice_id")
    deepgram_model = "nova-2-phonecall" if language.startswith("en") else "nova-2"

    # default Google TTS voices per language when no ElevenLabs voice is configured
    DEFAULT_VOICES = {
        "en": "en-US-Neural2-F",
        "es": "es-ES-Neural2-A",
        "fr": "fr-FR-Neural2-A",
        "de": "de-DE-Neural2-A",
        "hi": "hi-IN-Neural2-A",
        "pt": "pt-BR-Neural2-A",
    }
    # voice = voice_id or DEFAULT_VOICES.get(language, "en-US-Neural2-F")
    voice = "en-US-Neural2-F"

    agent_name    = agent.get("agent_name", "your assistant")
    welcome_greeting = f"Hello! Thank you for calling. This is {agent_name}. May I have your name please?"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
        <Connect>
            <ConversationRelay
            url="{ws_url}"
            welcomeGreeting="{welcome_greeting}"
            voice="{voice}"
            transcriptionProvider="deepgram"
            speechModel="{deepgram_model}"
            language="{language}"
            interruptible="true"
            />
        </Connect>
        </Response>"""
    return Response(content=twiml, media_type="application/xml")


# ── WebSocket handler
@router.websocket("/ws")
async def ImboundCallWS(ws: WebSocket):

    await ws.accept()

    agent_id_qp: str = ws.query_params.get("agent_id", "")
    logger.info(f"[WS] ── New connection  agent_id_qp={agent_id_qp!r}  client={ws.client}")

    history:          list[dict]  = []
    agent_config:     dict | None = None
    tools:            list[dict]  = []
    call_sid:         str         = ""
    from_number:      str         = ""
    started_at:       float       = 0.0
    _interrupt_event: asyncio.Event = asyncio.Event()

    try:
        while True:
            raw = await ws.receive_text()
            msg  = json.loads(raw)
            kind = msg.get("type")

            logger.debug(f"[WS] msg type={kind!r}  callSid={msg.get('callSid','?')}")

            if kind == "setup":
                call_sid    = msg.get("callSid", "")
                from_number = msg.get("from", "")
                started_at  = time.time()
                logger.info(f"[WS:SETUP] callSid={call_sid!r}  from={from_number!r}  agent_id_qp={agent_id_qp!r}")

                # ── Try Redis by real CA SID ──────────────────
                agent_config = await load_call_session(call_sid)
                if agent_config:
                    logger.info(f"[WS:SETUP] Session found in Redis by CA SID — agent={agent_config.get('agent_name')!r}")
                else:
                    logger.warning(f"[WS:SETUP] No Redis session for CA SID={call_sid!r}")

                # ── Browser call fallback: load by agent_id QP ─
                if not agent_config and agent_id_qp:
                    logger.info(f"[WS:SETUP] Trying DB lookup by agent_id_qp={agent_id_qp!r}")
                    try:
                        agent = await get_agent_by_id(agent_id_qp)
                        if agent:
                            agent_config = agent
                            logger.info(f"[WS:SETUP] Agent loaded from DB: {agent_config.get('agent_name')!r}")
                            if call_sid:
                                await store_call_session(call_sid, agent_config)
                                logger.info(f"[WS:SETUP] Re-stored session under real SID={call_sid!r}")
                        else:
                            logger.error(f"[WS:SETUP] get_agent_by_id({agent_id_qp!r}) returned None — agent missing or not LIVE")
                    except Exception as e:
                        logger.error(f"[WS:SETUP] DB agent lookup EXCEPTION: {e}", exc_info=True)
                elif not agent_config:
                    logger.error(f"[WS:SETUP] No agent_id_qp and no Redis session — will use fallback prompt")

                if agent_config:
                    tools = build_tools(agent_config.get("tools", []), agent_config.get("user_tools", []))
                    logger.info(f"[WS:SETUP] Ready — agent={agent_config['agent_name']!r}  tools={[t['function']['name'] for t in tools]}")
                else:
                    logger.warning(f"[WS:SETUP] Using FALLBACK config — no real agent found")
                    agent_config = {
                        "agent_name":    "AI Assistant",
                        "system_prompt": FALLBACK_SESSION_PROMPT,
                        "agent_id":      None,
                        "tools":         [],
                    }
                    tools = [END_CALL_TOOL]

            elif kind == "prompt":
                user_text = msg.get("voicePrompt", "").strip()
                if not user_text or agent_config is None:
                    continue
                logger.info(f"[USER]  {user_text}")
                history.append({"role": "user", "content": user_text})

                # save caller turn — fire-and-forget, no await needed
                if call_sid:
                    asyncio.create_task(save_transcript(call_sid, "caller", user_text))

                _interrupt_event.clear()
                should_end, agent_reply = await respond(ws, history, agent_config, tools, call_sid, _interrupt_event)

                # save agent reply
                if call_sid and agent_reply:
                    asyncio.create_task(save_transcript(call_sid, "agent", agent_reply))

                if should_end:
                    await ws.send_text(json.dumps({"type": "end"}))
                    duration = int(time.time() - started_at) if started_at else 0
                    if call_sid:
                        outcome = await classify_outcome(history) if history else "no_outcome"
                        logger.info(f"[OUTCOME] classified → {outcome}")
                        await update_call_log(
                            call_sid,
                            status           = "completed",
                            duration_seconds = duration,
                            reason           = "agent_ended",
                            outcome          = outcome,
                            ended_at         = True,
                        )
                        _celery.send_task(
                            "voice_engine.tasks.post_call_pipeline",
                            args=[call_sid, "completed", duration],
                        )
                    break

            elif kind == "interrupt":
                logger.info(f"[INTERRUPT] {msg.get('utteranceUntilInterrupt', '')}")
                _interrupt_event.set()   # signal respond() to stop streaming

            elif kind == "end":
                duration      = int(time.time() - started_at) if started_at else 0
                twilio_reason = msg.get("reason", "")
                logger.info(f"[END] reason={twilio_reason}  duration={duration}s")

                if call_sid:
                    outcome = await classify_outcome(history) if history else "no_outcome"
                    logger.info(f"[OUTCOME] classified → {outcome}")
                    await update_call_log(
                        call_sid,
                        status           = "completed",
                        duration_seconds = duration,
                        reason           = twilio_reason,
                        outcome          = outcome,
                        ended_at         = True,
                    )
                    _celery.send_task(
                        "voice_engine.tasks.post_call_pipeline",
                        args=[call_sid, "completed", duration],
                    )
                break

    except WebSocketDisconnect:
        logger.info("[WS] caller disconnected abruptly")
        if call_sid:
            duration = int(time.time() - started_at) if started_at else 0
            asyncio.create_task(update_call_log(
                call_sid,
                status           = "completed",
                duration_seconds = duration,
                reason           = "caller_hangup",
                ended_at         = True,
            ))
    except Exception as e:
        logger.error(f"[WS ERROR] {e}")
        import traceback; traceback.print_exc()
        if call_sid:
            duration = int(time.time() - started_at) if started_at else 0
            asyncio.create_task(update_call_log(
                call_sid,
                status           = "failed",
                duration_seconds = duration,
                reason           = str(e)[:100],
                ended_at         = True,
            ))


async def classify_outcome(history: list[dict]) -> str:
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history if m.get("content"))
    resp = await _groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": OUTCOME_CLASSIFICATION_PROMPT},
            {"role": "user",   "content": transcript},
        ],
        max_tokens=10,
        temperature=0,
    )
    result = (resp.choices[0].message.content or "").strip().lower()
    return result if result in ("booked", "faq_resolved") else "no_outcome"


async def respond(
    ws: WebSocket,
    history: list[dict],
    agent_config: dict,
    tools: list[dict],
    call_sid: str = "",
    interrupt: asyncio.Event | None = None,
) -> bool:

    base_prompt = (
        agent_config.get("system_prompt") or
        FALLBACK_SYSTEM_PROMPT.format(agent_name=agent_config.get("agent_name", "AI"))
    )

    # ── Step 2: inject capability guard into the prompt ───────────────────────
    capabilities = [t["function"]["name"] for t in tools if t["function"]["name"] != "end_call"]
    if capabilities:
        capability_note = CAPABILITY_NOTE_WITH_TOOLS.format(capabilities=", ".join(capabilities))
    else:
        capability_note = CAPABILITY_NOTE_NO_TOOLS

    system_prompt = base_prompt + capability_note

    # ── Step 2.5: KB lookup — inject relevant context if agent has documents ──
    # kb_doc_ids = agent_config.get("kb_doc_ids", [])
    # if kb_doc_ids and history:
    #     try:
    #         query_vec = embed_texts([history[-1]["content"]])[0]
    #         hits = _pinecone.query(kb_doc_ids, query_vec, top_k=5)
    #         if hits:
    #             kb_context = "\n".join(f"- {h['text']}" for h in hits)
    #             system_prompt += f"\n\nRelevant knowledge base info:\n{kb_context}"
    #     except Exception as e:
    #         logger.warning(f"[KB] lookup failed: {e}")

    # ── Step 3: build the message list to send to Groq
    messages = [{"role": "system", "content": system_prompt}] + history

    # use the reliable model when tools are present, fast model for plain chat
    has_tools     = bool(tools)
    active_model  = GROQ_TOOL_MODEL if has_tools else GROQ_MODEL
    # low temperature for tool calls (precise data collection), slightly higher for chat
    temperature   = 0.1 if has_tools else 0.3

    # ── Step 4: tool-call loop
    while True:
        text_buf      = ""   # collects all spoken text
        tc_acc: dict  = {}   # accumulates tool call fragments (tool JSON arrives in pieces)
        finish_reason = None

        # ── Step 5: call Groq with streaming
        try:
            stream = await _groq.chat.completions.create(
                model                = active_model,
                messages             = messages,
                tools                = tools,
                tool_choice          = "auto",
                parallel_tool_calls  = False,   # never call two tools at once
                stream               = True,
                max_tokens           = 200,
                temperature          = temperature,
            )
        except Exception as groq_err:
            logger.warning(f"[GROQ] {active_model} failed, retrying with {GROQ_TOOL_MODEL}: {groq_err}")
            stream = await _groq.chat.completions.create(
                model                = GROQ_TOOL_MODEL,
                messages             = messages,
                tools                = tools,
                tool_choice          = "auto",
                parallel_tool_calls  = False,
                stream               = True,
                max_tokens           = 200,
                temperature          = 0.1,
            )

        # ── Step 6: process each streamed chunk, flush sentence-by-sentence ─────
        # Twilio speaks each "last:True" chunk as one TTS utterance.
        # Sending max 2 sentences per utterance keeps replies short + interruptible.
        sentence_buf  = ""   # tokens since last flush
        sentence_count = 0   # how many sentences flushed so far this turn
        SENTENCES_PER_CHUNK = 2   # ← tune this: 1 = very snappy, 2 = natural

        async for chunk in stream:
            # caller interrupted — stop generating immediately
            if interrupt and interrupt.is_set():
                logger.info("[RESPOND] Interrupt received — stopping stream")
                break

            choice        = chunk.choices[0]
            delta         = choice.delta
            finish_reason = choice.finish_reason or finish_reason

            if delta.content:
                # strip any leaked tool-call syntax the model accidentally puts in text
                clean = delta.content
                if "<function=" in clean or "<function" in clean:
                    clean = clean[:clean.index("<function")]
                if not clean:
                    continue
                text_buf     += clean
                sentence_buf += clean

                # flush when we hit sentence-ending punctuation
                if any(sentence_buf.rstrip().endswith(p) for p in (".", "!", "?", "…")):
                    sentence_count += 1
                    if sentence_count >= SENTENCES_PER_CHUNK:
                        # mark last=True so Twilio speaks this chunk immediately
                        await ws.send_text(json.dumps({"type": "text", "token": sentence_buf, "last": True}))
                        sentence_buf   = ""
                        sentence_count = 0
                    else:
                        # still within the chunk — send as non-final so it buffers
                        await ws.send_text(json.dumps({"type": "text", "token": sentence_buf, "last": False}))
                        sentence_buf = ""

            if delta.tool_calls:
                for tc_chunk in delta.tool_calls:
                    idx = tc_chunk.index
                    if idx not in tc_acc:
                        tc_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc_chunk.id:
                        tc_acc[idx]["id"] = tc_chunk.id
                    if tc_chunk.function:
                        if tc_chunk.function.name:
                            tc_acc[idx]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tc_acc[idx]["arguments"] += tc_chunk.function.arguments

        # flush any remaining text that didn't end with punctuation
        if sentence_buf.strip():
            await ws.send_text(json.dumps({"type": "text", "token": sentence_buf, "last": True}))

        # ── Step 7: signal end of this full turn
        await ws.send_text(json.dumps({"type": "text", "token": "", "last": True}))
        print(f"[AGENT] {text_buf!r}  finish={finish_reason}  tools={[v['name'] for v in tc_acc.values()]}")

        # ── Step 8: plain text reply? → done for this turn
        # if the model gave a normal spoken reply (no tool call), save it and return
        # Fallback: sometimes llama-3.3 puts <function=name>{...}</function> in text instead of tool_calls
        if (finish_reason != "tool_calls" or not tc_acc) and "<function=" in text_buf:
            import re
            fn_match = re.search(r"<function=(\w+)>(.*?)</function>", text_buf, re.DOTALL)
            if fn_match:
                fn_name = fn_match.group(1)
                fn_args = fn_match.group(2).strip()
                spoken  = text_buf[:fn_match.start()].strip()
                logger.warning(f"[GROQ] text-mode tool call detected: {fn_name} — injecting as tool_call")
                tc_acc  = {0: {"id": f"fallback-{fn_name}", "name": fn_name, "arguments": fn_args}}
                finish_reason = "tool_calls"
                text_buf = spoken
                if spoken:
                    await ws.send_text(json.dumps({"type": "text", "token": spoken, "last": True}))
        if finish_reason != "tool_calls" or not tc_acc:
            history.append({"role": "assistant", "content": text_buf})
            return False, text_buf  # False = do NOT hang up

        # ── Step 9: reconstruct full tool call list from accumulated fragments ─
        tool_calls_msg = [
            {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
            for _, tc in sorted(tc_acc.items())
        ]
        # append assistant's tool-call decision to messages so Groq sees it next round
        messages.append({"role": "assistant", "content": text_buf or None, "tool_calls": tool_calls_msg})

        # ── Step 10: execute each tool and collect results ────────────────────
        end_call         = False
        agent_user_tools = agent_config.get("user_tools", [])

        for tc in tool_calls_msg:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                args = {}
            # inject context so booking can link to agent + call
            if name not in ("end_call",):
                args.setdefault("agent_id", agent_config.get("agent_id") or "")
                args.setdefault("call_sid", call_sid or "")
            logger.info(f"[TOOL] calling {name!r}  args={args}")
            result = await execute_tool(name, args, [], agent_user_tools)
            logger.info(f"[TOOL] {name!r} result → {result[:200]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

            if name == "end_call":
                end_call = True

        # ── Step 11: end_call tool was triggered → say goodbye and hang up ────
        if end_call:
            # ask Groq for a short farewell sentence (non-streaming, max 80 tokens)
            farewell = await _get_farewell(messages)
            if farewell:
                await ws.send_text(json.dumps({"type": "text", "token": farewell, "last": True}))
                await asyncio.sleep(0.8)  # give TTS time to finish speaking before we hang up
            history.append({"role": "assistant", "content": farewell})
            return True, farewell


async def _get_farewell(messages: list[dict]) -> str:
    resp = await _groq.chat.completions.create(
        model=GROQ_MODEL, messages=messages, max_tokens=80, stream=False
    )
    return resp.choices[0].message.content or ""
