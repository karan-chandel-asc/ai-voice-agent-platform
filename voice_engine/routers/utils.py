import json
import redis.asyncio as redis
from ..config import settings



def _redis():
    return redis.from_url(settings.REDIS_URL)


async def store_call_session(call_sid: str, agent: dict):
    r = _redis()
    await r.setex(f"call_session:{call_sid}", 3600, json.dumps(agent))
    await r.aclose()


async def load_call_session(call_sid: str) -> dict | None:
    r = _redis()
    raw = await r.get(f"call_session:{call_sid}")
    await r.aclose()
    return json.loads(raw) if raw else None



END_CALL_TOOL = {
    "type": "function",
    "function": {
        "name": "end_call",
        "description": "Hang up the call after the conversation is fully complete.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": []},
    },
}

def build_tools(agent_tools: list[dict], user_tools: list[dict] | None = None) -> list[dict]:
    result = []

    # user tools — parameters field may be stored as a full OpenAI function object
    # { type:"function", function:{ name, description, parameters:{...} } }
    # or as a bare JSON Schema { type:"object", properties:{...} }
    # Handle both shapes.
    for ut in (user_tools or []):
        params = ut.get("parameters") or {}
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}

        # Case 1: parameters field is a full OpenAI tool object — use it directly
        if params.get("type") == "function" and "function" in params:
            result.append(params)
            continue

        # Case 2: bare JSON Schema or empty — wrap it
        name = ut.get("name", "").replace(" ", "_").lower()
        if not name:
            continue
        if "type" not in params:
            params = {"type": "object", "properties": params, "required": []}
        result.append({
            "type": "function",
            "function": {
                "name": name,
                "description": ut.get("description", ""),
                "parameters": params,
            },
        })

    result.append(END_CALL_TOOL)

    # Deduplicate by function name — user tools override catalog tools if same name
    seen, deduped = set(), []
    for tool in reversed(result):  # reversed so user tools (added later) win
        fn_name = tool.get("function", {}).get("name", "")
        if fn_name not in seen:
            seen.add(fn_name)
            deduped.append(tool)
    return list(reversed(deduped))
