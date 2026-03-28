"""
Redline Reveal — FastAPI backend
WebSocket handler for bidirectional voice (PCM audio ↔ Gemini Live)
REST endpoint for choropleth map data
"""

import os
import sys
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load .env before importing ADK
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "0")

from agents.dispatch_agent import VoiceSession
from mcp_server.hmda_tools import (
    get_all_boroughs_denial_rates,
    get_borough_denial_rate,
    get_borough_race_breakdown,
    get_nyc_citywide_summary,
    NYC_ZIPS,
    BOROUGH_FIPS,
    _resolve_borough,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# --- In-memory map state (shared across WebSocket sessions) ---
_current_map_data: dict = {}
_map_data_lock = asyncio.Lock()

# Active voice sessions: session_id → VoiceSession
_voice_sessions: dict[str, VoiceSession] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Redline Reveal backend starting...")
    # Preload base NYC map data (no race filter)
    try:
        data = await get_all_boroughs_denial_rates(2022)
        async with _map_data_lock:
            _current_map_data.update(data)
        logger.info("Preloaded NYC base map data: %d zip codes", len(data.get("zip_map", {})))
    except Exception as e:
        logger.warning("Could not preload map data: %s", e)
    yield
    # Cleanup sessions on shutdown
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

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/config")
async def get_config():
    """
    Returns non-secret client config (Google Maps key is low-risk — browser-visible by design).
    Keeps the key out of committed HTML source.
    """
    return {
        "google_maps_api_key": os.environ.get("GOOGLE_MAPS_API_KEY", ""),
    }


@app.get("/")
async def root():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "service": "Redline Reveal"}


@app.get("/health")
async def health():
    return {"status": "ok", "active_sessions": len(_voice_sessions)}


@app.get("/map-data")
async def get_map_data(
    race: Optional[str] = None,
    year: int = 2022,
):
    """
    Returns choropleth map data: denial rates per zip code for all NYC boroughs.
    Frontend polls this to update the map in real-time.
    """
    try:
        if race:
            data = await get_all_boroughs_denial_rates(year, race)
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
    """
    Get detailed HMDA data for a specific NYC borough.
    ?breakdown=true returns per-race breakdown.
    """
    try:
        if breakdown:
            return await get_borough_race_breakdown(borough, year)
        return await get_borough_denial_rate(borough, year, race)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary")
async def get_summary(race: Optional[str] = None, year: int = 2022):
    """Citywide NYC mortgage lending summary."""
    try:
        return await get_nyc_citywide_summary(year, race)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── WebSocket Voice Handler ───────────────────────────────────────────────────

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    Bidirectional WebSocket for voice I/O.

    Browser sends:
      - Binary frames: raw PCM audio chunks (16kHz, 16-bit, mono)
      - Text frames: JSON control messages
        {"type": "end_of_speech"}
        {"type": "ping"}

    Server sends:
      - Binary frames: PCM audio response from Gemini
      - Text frames: JSON
        {"type": "transcript", "text": "..."}
        {"type": "map_update", "data": {...}}
        {"type": "error", "message": "..."}
        {"type": "pong"}
    """
    await websocket.accept()
    session_id = f"session_{id(websocket)}"
    logger.info("New voice WebSocket connection: %s", session_id)

    async def on_map_update(map_data: dict):
        """Called when agent produces map data — push to frontend."""
        try:
            await websocket.send_text(json.dumps({
                "type": "map_update",
                "data": map_data,
            }))
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
            await websocket.send_text(json.dumps({
                "type": "transcript",
                "text": text,
            }))

        # Run agent in background task
        agent_task = asyncio.create_task(
            session.run(on_audio_chunk, on_text_chunk)
        )

        # Receive loop: browser → agent
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if "bytes" in message and message["bytes"]:
                # PCM audio chunk from microphone
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
                    # Manual map refresh
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
        logger.error("Voice session error [%s]: %s", session_id, e)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        await session.close()
        _voice_sessions.pop(session_id, None)
        logger.info("Voice session cleaned up: %s", session_id)
