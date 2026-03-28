"""
Redline Reveal — FastAPI backend
WebSocket handler for bidirectional voice (PCM audio ↔ Gemini Live)
REST endpoint for choropleth map data
"""

import sys
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# ── Paths (absolute, CWD-independent) ────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

# ── Bootstrap: add backend/ to sys.path, load .env ───────────────────────────
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(PROJECT_DIR / ".env")

import os
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "0")

from agents.dispatch_agent import VoiceSession
from mcp_server.hmda_tools import (
    get_all_boroughs_denial_rates,
    get_borough_denial_rate,
    get_borough_race_breakdown,
    get_nyc_citywide_summary,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

logger.info("BACKEND_DIR : %s", BACKEND_DIR)
logger.info("FRONTEND_DIR: %s (exists=%s)", FRONTEND_DIR, FRONTEND_DIR.exists())

# ── Shared state ──────────────────────────────────────────────────────────────
_current_map_data: dict = {}
_map_data_lock = asyncio.Lock()
_voice_sessions: dict[str, VoiceSession] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Redline Reveal backend starting...")
    try:
        data = await get_all_boroughs_denial_rates(2022)
        async with _map_data_lock:
            _current_map_data.update(data)
        logger.info("Preloaded NYC base map data: %d zip codes", len(data.get("zip_map", {})))
    except Exception as e:
        logger.warning("Could not preload map data: %s", e)
    yield
    for session in _voice_sessions.values():
        await session.close()
    logger.info("Redline Reveal backend shutdown")


app = FastAPI(title="Redline Reveal", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static assets at /static (CSS, JS) ───────────────────────────────────────
# Mounting at /static keeps all API routes unambiguous.
# index.html references /static/style.css and /static/app.js.
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ── REST Endpoints ────────────────────────────────────────────────────────────

@app.get("/config")
async def get_config():
    """Serves Maps API key to browser — keeps it out of committed source."""
    return {"google_maps_api_key": os.environ.get("GOOGLE_MAPS_API_KEY", "")}


@app.get("/health")
async def health():
    return {"status": "ok", "active_sessions": len(_voice_sessions)}


@app.get("/map-data")
async def get_map_data(race: Optional[str] = None, year: int = 2022):
    try:
        if race:
            # Race-filtered: never cache — return fresh data directly
            return await get_all_boroughs_denial_rates(year, race)
        else:
            async with _map_data_lock:
                if _current_map_data:
                    return _current_map_data
            data = await get_all_boroughs_denial_rates(year)
            async with _map_data_lock:
                _current_map_data.update(data)
            return data
    except Exception as e:
        logger.error("Error fetching map data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/borough/{borough}")
async def get_borough_data(
    borough: str,
    race: Optional[str] = None,
    year: int = 2022,
    breakdown: bool = False,
):
    try:
        if breakdown:
            return await get_borough_race_breakdown(borough, year)
        return await get_borough_denial_rate(borough, year, race)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary")
async def get_summary(race: Optional[str] = None, year: int = 2022):
    try:
        return await get_nyc_citywide_summary(year, race)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


def _is_normal_disconnect(msg: str) -> bool:
    """Return True for benign WebSocket close events (e.g. page refresh)."""
    lowered = msg.lower()
    return any(k in lowered for k in ("disconnect", "closed", "1000", "going away", "normal closure"))


# ── WebSocket Voice Handler ───────────────────────────────────────────────────

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id = f"session_{id(websocket)}"
    logger.info("New voice WebSocket connection: %s", session_id)

    async def on_map_update(map_data: dict):
        try:
            await websocket.send_text(json.dumps({"type": "map_update", "data": map_data}))
            async with _map_data_lock:
                _current_map_data.update(map_data)
        except Exception as e:
            logger.warning("Could not send map update: %s", e)

    session = VoiceSession(session_id=session_id, on_map_update=on_map_update)
    _voice_sessions[session_id] = session

    try:
        await session.start()

        async def on_audio_chunk(audio_bytes: bytes):
            await websocket.send_bytes(audio_bytes)

        async def on_text_chunk(text: str):
            await websocket.send_text(json.dumps({"type": "transcript", "text": text}))

        async def _run_agent():
            try:
                await session.run(on_audio_chunk, on_text_chunk)
            except Exception as exc:
                msg = str(exc).lower()
                normal = any(k in msg for k in ("disconnect", "closed", "1000", "going away", "normal closure"))
                if not normal:
                    logger.error("Agent task error [%s]: %s", session_id, exc)

        agent_task = asyncio.create_task(_run_agent())

        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if "bytes" in message and message["bytes"]:
                await session.send_audio(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    ctrl = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue
                msg_type = ctrl.get("type", "")
                if msg_type == "end_of_speech":
                    await session.send_activity_end()
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg_type == "map_request":
                    race = ctrl.get("race")
                    year = ctrl.get("year", 2022)
                    try:
                        data = await get_all_boroughs_denial_rates(year, race)
                        await on_map_update(data)
                    except Exception as e:
                        logger.error("Map request error: %s", e)

        agent_task.cancel()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as e:
        msg = str(e)
        # Suppress clean-close noise (code 1000 = normal closure, client navigated away)
        if _is_normal_disconnect(msg):
            logger.info("Voice session closed normally: %s", session_id)
        else:
            logger.error("Voice session error [%s]: %s", session_id, e)
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": msg}))
            except Exception:
                pass
    finally:
        await session.close()
        _voice_sessions.pop(session_id, None)
        logger.info("Voice session cleaned up: %s", session_id)
