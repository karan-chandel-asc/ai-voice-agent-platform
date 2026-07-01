import uuid
import asyncpg
from ..config import settings


# ── Agent lookup ───────────────────────────────────────────────────────────────
async def get_demo_agent() -> dict | None:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT id::text AS agent_id, agent_name FROM agents_agent "
            "WHERE is_demo = true AND status = 'live' LIMIT 1"
        )
        return dict(row) if row else None
    finally:
        await conn.close()


async def get_live_agents() -> list[dict]:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        rows = await conn.fetch(
            "SELECT id::text AS agent_id, agent_name FROM agents_agent WHERE status = 'live' ORDER BY agent_name"
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_agent_by_id(agent_id: str) -> dict | None:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                a.id::text         AS agent_id,
                a.agent_name,
                a.system_prompt,
                a.status,
                a.language,
                e.voice_id         AS elevenlabs_voice_id
            FROM agents_agent a
            LEFT JOIN agents_elevenlabsvoice e ON e.id = a.elevenlabs_voice_id
            WHERE a.id = $1::uuid AND a.status = 'live'
            """,
            agent_id,
        )
        if not row:
            return None

        agent = dict(row)

        user_tools = await conn.fetch(
            """
            SELECT ut.id::text, ut.name, ut.description, ut.webhook_url, ut.parameters
            FROM agents_agentusertool aut
            JOIN agents_usertool      ut ON ut.id = aut.user_tool_id
            WHERE aut.agent_id = $1::uuid AND aut.is_active = true AND ut.is_active = true
            """,
            agent["agent_id"],
        )
        agent["tools"] = []
        agent["user_tools"] = [dict(t) for t in user_tools]

        kb_docs = await conn.fetch(
            """
            SELECT id::text FROM knowledge_agentdocument
            WHERE agent_id = $1::uuid AND status = 'ready'
            """,
            agent["agent_id"],
        )
        agent["kb_doc_ids"] = [r["id"] for r in kb_docs]
        return agent
    finally:
        await conn.close()


async def get_agent_by_phone(to_number: str) -> dict | None:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        row = await conn.fetchrow(
            """
            SELECT
                a.id::text         AS agent_id,
                a.agent_name,
                a.system_prompt,
                a.status,
                a.language,
                e.voice_id         AS elevenlabs_voice_id
            FROM agents_phonenumber p
            JOIN agents_agent        a ON a.id = p.agent_id
            LEFT JOIN agents_elevenlabsvoice e ON e.id = a.elevenlabs_voice_id
            WHERE p.phone_number = $1
              AND a.status       = 'live'
            """,
            to_number,
        )
        if not row:
            return None

        agent = dict(row)

        user_tools = await conn.fetch(
            """
            SELECT ut.id::text, ut.name, ut.description, ut.webhook_url, ut.parameters
            FROM agents_agentusertool aut
            JOIN agents_usertool      ut ON ut.id = aut.user_tool_id
            WHERE aut.agent_id = $1::uuid AND aut.is_active = true AND ut.is_active = true
            """,
            agent["agent_id"],
        )
        agent["tools"] = []
        agent["user_tools"] = [dict(t) for t in user_tools]

        kb_docs = await conn.fetch(
            """
            SELECT id::text FROM knowledge_agentdocument
            WHERE agent_id = $1::uuid AND status = 'ready'
            """,
            agent["agent_id"],
        )
        agent["kb_doc_ids"] = [r["id"] for r in kb_docs]
        return agent
    finally:
        await conn.close()


# ── Call log ───────────────────────────────────────────────────────────────────
async def create_call_log(call_sid: str, from_number: str, agent_id: str | None = None) -> None:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute(
            """
            INSERT INTO calls_calllog (
                id, twilio_call_sid, caller_phone, agent_id,
                direction, status, outcome,
                duration_seconds, was_transferred, recording_url,
                reason, started_at, created_at
            ) VALUES (
                gen_random_uuid(), $1, $2, $3,
                'inbound', 'initiated', 'no_outcome',
                0, false, '',
                '', NOW(), NOW()
            )
            ON CONFLICT (twilio_call_sid) DO NOTHING
            """,
            call_sid, from_number, uuid.UUID(agent_id) if agent_id else None,
        )
    finally:
        await conn.close()


async def update_call_log(call_sid: str, **fields) -> None:
    """
    Update only the fields you pass as keyword arguments.

    Examples:
        await update_call_log(call_sid, status="completed", duration_seconds=120)
        await update_call_log(call_sid, status="failed")
        await update_call_log(call_sid, outcome="booked", sentiment_score=0.8)
        await update_call_log(call_sid, was_transferred=True, recording_url="https://...")
    """
    if not fields:
        return

    # allowed columns — prevents SQL injection from arbitrary kwargs
    # ended_at is excluded here: always set via SQL NOW() when present in fields
    ALLOWED = {
        "status", "duration_seconds", "outcome", "sentiment_score",
        "was_transferred", "recording_url", "reason",
    }
    safe = {k: v for k, v in fields.items() if k in ALLOWED}
    set_ended_at = fields.get("ended_at", False)  # pass ended_at=True to stamp it

    if not safe and not set_ended_at:
        return

    clauses = []
    values  = [call_sid]   # $1 is always call_sid
    idx     = 2

    for col, val in safe.items():
        clauses.append(f"{col} = ${idx}")
        values.append(val)
        idx += 1

    if set_ended_at:
        clauses.append("ended_at = NOW()")   # SQL expression, not a parameter

    sql = f"UPDATE calls_calllog SET {', '.join(clauses)} WHERE twilio_call_sid = $1"

    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute(sql, *values)
    finally:
        await conn.close()


# ── Transcripts ────────────────────────────────────────────────────────────────
async def save_transcript(call_sid: str, speaker: str, text: str) -> None:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute(
            """
            INSERT INTO calls_calltranscript (id, call_id, speaker, text, langgraph_node, timestamp)
            SELECT gen_random_uuid(), id, $2, $3, '', NOW()
            FROM   calls_calllog
            WHERE  twilio_call_sid = $1
            """,
            call_sid, speaker, text,
        )
    finally:
        await conn.close()
