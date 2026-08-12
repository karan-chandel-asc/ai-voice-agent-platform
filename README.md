# Deskline — AI Voice Agents for Hospitality

**Deskline** is a full-stack platform that lets hotels and restaurants run custom AI voice agents for room bookings, table reservations, and guest FAQs — without Retell or Vapi.

Built on an **owned stack**: Twilio + ConversationRelay, Groq LLM, Django REST, and FastAPI.

---

## Features

- **Live voice agents** for front desk & restaurant hosting
- **Browser calling** (Twilio Voice SDK) + inbound phone webhooks
- **Local booking tools** (`book_room` / `book_table`) — no external webhook glue
- **Dashboard** — KPIs, today’s reservations, recent calls
- **Call history & analytics** — outcomes, sentiment, agent performance
- **My Tools** — attach OpenAI-style tool schemas to agents
- **One-command demo seed** for portfolio screenshots

---

## Screenshots

<p align="center">
  <img src="screenshots/01-landing-page.png" alt="Deskline landing page" width="90%" />
</p>
<p align="center"><em>Landing page — hospitality-focused value proposition and product preview</em></p>

<br/>

| Preview | Screen |
|:-------:|--------|
| <img src="screenshots/02-platform-features.png" width="320" alt="Platform features" /> | **Platform features**<br/>Inbound handling, room & table booking, campaigns, knowledge base, live monitor, and analytics. |
| <img src="screenshots/03-login.png" width="320" alt="Login" /> | **Secure login**<br/>Hotel operations console sign-in with clear product positioning. |
| <img src="screenshots/04-operations-dashboard.png" width="320" alt="Operations dashboard" /> | **Operations dashboard**<br/>30-day KPIs, active agents, today’s room/table bookings, and recent calls. |
| <img src="screenshots/05-analytics.png" width="320" alt="Analytics" /> | **Analytics**<br/>Call volume, outcome breakdown, booking rate, and performance trends. |
| <img src="screenshots/06-my-agents.png" width="320" alt="My Agents" /> | **My Agents**<br/>Manage live, paused, and draft voice agents with tools and phone numbers. |
| <img src="screenshots/07-my-tools.png" width="320" alt="My Tools" /> | **My Tools**<br/>Built-in booking and availability tools agents can invoke during calls. |
| <img src="screenshots/08-call-history.png" width="320" alt="Call History" /> | **Call history**<br/>Filterable logs with outcome, sentiment, duration, and agent attribution. |
| <img src="screenshots/09-integrations.png" width="320" alt="Integrations" /> | **Settings & integrations**<br/>External connectors (e.g. Google Sheets) and account management. |

### Screenshot index

| File | Description |
|------|-------------|
| `screenshots/01-landing-page.png` | Marketing landing / hero |
| `screenshots/02-platform-features.png` | Feature grid |
| `screenshots/03-login.png` | Authentication |
| `screenshots/04-operations-dashboard.png` | Main dashboard |
| `screenshots/05-analytics.png` | Performance analytics |
| `screenshots/06-my-agents.png` | Agent management |
| `screenshots/07-my-tools.png` | Tool library |
| `screenshots/08-call-history.png` | Call logs |
| `screenshots/09-integrations.png` | Integrations & account |

---

## Architecture

### System overview

```mermaid
flowchart TB
  subgraph Clients
    Browser["Dashboard UI<br/>Django Templates"]
    Phone["Guest Phone"]
    BrowserCall["Browser Softphone<br/>Twilio Voice SDK"]
  end

  subgraph Platform["Deskline Platform"]
    Django["Django + DRF<br/>:8000<br/>Auth · Agents · Bookings · Calls"]
    FastAPI["FastAPI Voice Engine<br/>:8001<br/>Relay · Token · WebSocket"]
    DB[(SQLite / Postgres)]
    Redis[(Redis sessions)]
  end

  subgraph External["Voice & AI"]
    Twilio["Twilio Voice<br/>ConversationRelay"]
    Groq["Groq LLM"]
    STT["Deepgram STT"]
  end

  Browser --> Django
  BrowserCall --> Twilio
  Phone --> Twilio
  Twilio -->|"POST /relay/inbound<br/>or /relay/browser-outbound"| FastAPI
  Twilio <-->|"WSS /relay/ws"| FastAPI
  FastAPI --> Groq
  FastAPI --> STT
  FastAPI --> DB
  FastAPI --> Redis
  Django --> DB
  Browser -->|"REST + JWT"| Django
  BrowserCall -->|"GET /relay/token"| FastAPI
```

### Call flow (browser or phone)

```mermaid
sequenceDiagram
  participant Guest
  participant Twilio
  participant FastAPI as Voice Engine
  participant DB as Database
  participant Groq as Groq LLM

  Guest->>Twilio: Place call (phone / browser)
  Twilio->>FastAPI: POST TwiML webhook
  FastAPI->>DB: Lookup live agent + tools
  FastAPI->>DB: Create CallLog + session
  FastAPI-->>Twilio: ConversationRelay TwiML
  Twilio->>FastAPI: WebSocket /relay/ws
  loop Conversation
    Twilio->>FastAPI: Caller speech (transcript)
    FastAPI->>Groq: Chat + tool calling
    alt Tool: book_room / book_table
      FastAPI->>DB: Save Booking
      FastAPI-->>Twilio: Confirmation speech
    else Normal reply
      FastAPI-->>Twilio: Agent speech
    end
  end
  FastAPI->>DB: Update CallLog + transcripts
```

### Data model (core)

```mermaid
erDiagram
  CustomUser ||--o{ Agent : owns
  CustomUser ||--o{ UserTool : owns
  Agent ||--o{ AgentUserTool : has
  UserTool ||--o{ AgentUserTool : linked
  Agent ||--o{ CallLog : receives
  Agent ||--o{ Booking : creates
  CallLog ||--o{ CallTranscript : has
  Agent }o--|| ElevenLabsVoice : optional

  CustomUser {
    uuid id
    string email
    string business_name
    string plan
  }
  Agent {
    uuid id
    string agent_name
    string status
    string phone_number
    text system_prompt
  }
  Booking {
    uuid id
    string booking_type
    string guest_name
    date check_in
    bool is_confirmed
  }
  CallLog {
    uuid id
    string twilio_call_sid
    string outcome
    int duration_seconds
    float sentiment_score
  }
```

---

## Tech stack

| Layer | Technology |
|--------|------------|
| Web / API | Django 4.2, Django REST Framework, SimpleJWT |
| Voice runtime | FastAPI, Uvicorn, Twilio ConversationRelay |
| LLM | Groq (tool calling) |
| Speech | Deepgram (via Twilio CR), Twilio TTS |
| UI | Django templates, Tailwind CSS (local build) |
| Data | SQLite (local) / Postgres (optional) |
| Jobs | Celery (optional; eager mode for local) |

---

## Project structure

```
ai-voice-agent-platform/
├── accounts/          # Auth, profile, seed_demo command
├── agents/            # Agents, tools, bookings
├── calls/             # Call logs, transcripts, analytics
├── dashboard/         # Stats & booking panels
├── knowledge/         # Documents / RAG hooks
├── integrations/      # Third-party connectors
├── voice_engine/      # FastAPI: relay, browser call, WS
├── templates/         # Deskline UI
├── static/            # Tailwind CSS, Twilio SDK
├── manage.py
└── requirements.txt
```

---

## Quick start

### 1. Setup

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Ensure in `.env`:

```env
USE_SQLITE=True
DATABASE_URL=sqlite:///db.sqlite3
FASTAPI_BASE_URL=http://localhost:8001
DJANGO_BASE_URL=http://localhost:8000
CELERY_TASK_ALWAYS_EAGER=True
```

### 2. Database + demo data

```bash
python manage.py migrate
python manage.py seed_demo
npm install
npm run build:css
```

**Demo login**

| Field | Value |
|--------|--------|
| Email | `demo@deskline.io` |
| Password | `demo1234` |

### 3. Run (two terminals)

```bash
# Terminal 1 — Django UI + API
python manage.py runserver

# Terminal 2 — Voice engine
uvicorn voice_engine.main:app --reload --port 8001
```

Open **http://127.0.0.1:8000** → Log in → Dashboard.

---

## Twilio (optional — live calls)

For real phone / browser softphone testing:

1. Create a **TwiML App**  
   Voice Request URL (POST):
   ```
   https://<your-ngrok>.ngrok-free.dev/relay/browser-outbound
   ```
2. Point phone number inbound webhook to:
   ```
   https://<your-ngrok>.ngrok-free.dev/relay/inbound
   ```
3. Tunnel FastAPI:
   ```bash
   ngrok http 8001
   ```
4. Set in `.env`:
   ```env
   FASTAPI_BASE_URL=https://<your-ngrok>.ngrok-free.dev
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_APP_SID=...
   TWILIO_API_KEY_SID=...
   TWILIO_API_KEY_SECRET=...
   ```
5. Restart Uvicorn after changing `.env`.

Agent status must be **Live** for lookup during calls.

---

## Demo data (for screenshots)

```bash
python manage.py seed_demo --flush
```

Seeds Harbor Inn demo profile, agents, tools, calls, and bookings used in the gallery above.

Login: `demo@deskline.io` / `demo1234`

---

## API map (high level)

| Area | Base path |
|------|-----------|
| Auth | `/api/auth/` |
| Agents & tools | `/api/agents/` |
| Calls & analytics | `/api/calls/` |
| Dashboard | `/api/dashboard/` |
| Voice token / relay | `http://localhost:8001/relay/` |

Health check: `GET http://localhost:8001/health`

---

## Tooling for agents

Attach tools in **My Tools**, then link them on the agent. Runtime names:

| Tool | Purpose |
|------|---------|
| `book_room` | Hotel room reservation |
| `book_table` | Restaurant table reservation |
| `check_availability` | Slot check (demo) |

LLM receives OpenAI-style function schemas from `UserTool.parameters`.

---

## Environment variables

See `.env.example` for the full list. Minimum for UI-only screenshots:

- `SECRET_KEY`, `USE_SQLITE=True`
- `FASTAPI_BASE_URL`, `DJANGO_BASE_URL`

For live voice: Twilio + Groq (+ Deepgram via Twilio CR).

---

## License

Private portfolio project — all rights reserved unless otherwise stated.
