"""
DispatchAgent — gemini-2.0-flash-live-001
Bidirectional voice streaming agent.
Receives PCM audio from browser, calls HMDAAnalystAgent via A2A AgentTool,
speaks narrative response back, emits map data for frontend choropleth.
"""

import os
import sys
import json
import asyncio
import logging

from google.adk.agents import LlmAgent
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.tools.agent_tool import AgentTool
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from .hmda_analyst import hmda_analyst

logger = logging.getLogger(__name__)

DISPATCH_INSTRUCTION = """
You are REDLINE REVEAL — a voice-powered NYC mortgage bias analyst.
You receive voice input from users describing their neighborhood or demographic profile,
then expose real mortgage discrimination patterns using HMDA federal data.

YOUR VOICE PERSONALITY:
- Authoritative but empathetic — like a journalist uncovering systemic injustice
- Concise for voice: 2-4 sentences max per response
- Always cite specific percentages from the data
- Make comparisons (e.g., "nearly 3x higher than White applicants")

HOW TO RESPOND:
1. Listen to the user describe their location/demographics (e.g., "I'm a Latino homeowner in Jackson Heights")
2. Call the HMDAAnalystAgent tool to get real discrimination data and map visualization
3. Speak a compelling 2-4 sentence narrative about what the numbers reveal
4. The map data from HMDAAnalystAgent will automatically update the visualization

EXAMPLE INTERACTION:
User: "I'm a Latino homeowner trying to buy in Jackson Heights Queens"
You call HMDAAnalystAgent with this profile, get the HMDA data, then respond:
"In Queens, Hispanic and Latino applicants were denied mortgages at a rate of 38 percent in 2022 —
nearly two and a half times the rate for White applicants in the same borough.
Jackson Heights sits in Queens County, where over 1,200 minority families had their dreams denied.
These numbers reflect a systemic pattern that echoes decades of discriminatory lending in NYC."

IMPORTANT:
- Always call HMDAAnalystAgent — never make up statistics
- Keep responses short enough to be spoken naturally (under 30 seconds of speech)
- After speaking, wait for the next user query
- If the user mentions a specific neighborhood, pass that to HMDAAnalystAgent
- If they mention a race/ethnicity, pass that as the demographic filter

You have access to:
- HMDAAnalystAgent: Call this with the user's location and demographic profile
"""


def create_dispatch_agent() -> LlmAgent:
    """Create the DispatchAgent with A2A AgentTool wrapping HMDAAnalystAgent."""
    return LlmAgent(
        name="DispatchAgent",
        model="gemini-2.0-flash-live-001",
        instruction=DISPATCH_INSTRUCTION,
        tools=[AgentTool(agent=hmda_analyst)],
        description="Voice-powered NYC mortgage bias explorer using Gemini Live + HMDA data",
    )


# Module-level singleton
dispatch_agent = create_dispatch_agent()


class VoiceSession:
    """
    Manages a single user's bidirectional voice session.
    Bridges browser WebSocket PCM audio ↔ Gemini Live ADK agent.
    Extracts map_data from agent responses and emits via callback.
    """

    def __init__(self, session_id: str, on_map_update=None):
        self.session_id = session_id
        self.on_map_update = on_map_update  # async callback(map_data: dict)
        self.runner = InMemoryRunner(agent=dispatch_agent, app_name="redline-reveal")
        self.live_queue: LiveRequestQueue | None = None
        self._session = None
        self._task: asyncio.Task | None = None

    async def start(self):
        """Initialize ADK session and LiveRequestQueue."""
        self._session = await self.runner.session_service.create_session(
            app_name="redline-reveal",
            user_id=self.session_id,
        )
        self.live_queue = LiveRequestQueue()
        logger.info("VoiceSession started: %s", self.session_id)

    async def send_audio(self, pcm_data: bytes):
        """Push a PCM audio chunk into the agent's live queue."""
        if self.live_queue is None:
            return
        blob = genai_types.Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
        self.live_queue.send_realtime(blob)

    async def send_activity_end(self):
        """Signal end of user speech turn."""
        if self.live_queue:
            self.live_queue.send_realtime(
                genai_types.ActivityEnd()
            )

    async def run(self, on_audio_chunk, on_text_chunk):
        """
        Run the agent loop.
        on_audio_chunk(bytes): called with each PCM response chunk to send to browser
        on_text_chunk(str): called with text responses (for display/logging)
        """
        if not self._session or not self.live_queue:
            raise RuntimeError("VoiceSession.start() must be called first")

        async for event in self.runner.run_live(
            user_id=self.session_id,
            session_id=self._session.id,
            live_request_queue=self.live_queue,
        ):
            # Audio output → send to browser
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        await on_audio_chunk(part.inline_data.data)

                    elif hasattr(part, "text") and part.text:
                        await on_text_chunk(part.text)

                        # Check for map data in agent text output
                        if self.on_map_update:
                            map_data = _extract_map_data(part.text)
                            if map_data:
                                await self.on_map_update(map_data)

            # Tool call responses may contain map data
            if hasattr(event, "tool_response") and event.tool_response:
                if self.on_map_update:
                    map_data = _extract_map_data_from_tool(event)
                    if map_data:
                        await self.on_map_update(map_data)

    async def close(self):
        """Shut down the live session."""
        if self.live_queue:
            self.live_queue.close()
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("VoiceSession closed: %s", self.session_id)


def _extract_map_data(text: str) -> dict | None:
    """Try to parse map_data JSON embedded in agent text response."""
    try:
        # Agent may return JSON with zip_map
        if "zip_map" in text or "borough_data" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                if "zip_map" in data or "borough_data" in data:
                    return data
    except Exception:
        pass
    return None


def _extract_map_data_from_tool(event) -> dict | None:
    """Extract map data from tool response events."""
    try:
        if hasattr(event, "tool_response") and event.tool_response:
            resp = event.tool_response
            if hasattr(resp, "output") and resp.output:
                output = resp.output
                if isinstance(output, str):
                    data = json.loads(output)
                    if "zip_map" in data or "borough_data" in data:
                        return data
                elif isinstance(output, dict):
                    if "zip_map" in output or "borough_data" in output:
                        return output
    except Exception:
        pass
    return None
