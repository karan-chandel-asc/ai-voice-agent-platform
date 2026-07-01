from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import relay_test, browser_call

app = FastAPI(title="Voice Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
    ],
    allow_origin_regex=r"https://.*\.ngrok-free\.app",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(relay_test.router)
app.include_router(browser_call.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
