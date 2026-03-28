# REDLINE REVEAL — NYC Hackathon Project
## Mission Briefing for Claude Code

### What We're Building
"Redline Reveal" — A voice-powered mortgage bias explorer for NYC.
User speaks a neighborhood/demographic profile → Live AI voice agent queries HMDA data →
Speaks back narrative analysis of mortgage discrimination patterns →
Google Maps choropleth updates in real-time showing denial rates by race/income across NYC zip codes.

### Hackathon Context
- GDG NYC Hackathon, March 28 2026
- Submission deadline: 2:30 PM today
- Solo hacker
- Judging: 40% UX/Innovation, 30% Tech Implementation, 30% Demo
- Bonus points: Google ADK + A2A + Cloud Run deployment
- STRICTLY PROHIBITED: Basic RAG, standard chatbots, mockups

### Tech Stack (LOCKED)
- Frontend: Vanilla JS + HTML/CSS (NO React, NO bundler)
- Maps: Google Maps JS API choropleth (zip code level)
- Voice: Gemini Live API via WebSocket (bidirectional audio)
- Backend: Python FastAPI + WebSocket handler
- Agents: Google ADK
  - DispatchAgent: gemini-2.0-flash-live-001 (BiDi voice streaming)
  - HMDAAnalystAgent: gemini-2.5-flash (data analysis, called via A2A AgentTool)
- MCP: FastMCP server exposing CFPB HMDA API tools
- Deployment: Google Cloud Run
- Python env: uv

### Architecture
Browser (JS)
    | WebSocket (PCM audio chunks)
    v
FastAPI (main.py) + LiveRequestQueue
    |
    v
DispatchAgent [gemini-2.0-flash-live-001, ADK BiDi] -- voice in/out
    | AgentTool (A2A)
    v
HMDAAnalystAgent [gemini-2.5-flash, ADK]
    | MCP Tool
    v
FastMCP Server --> CFPB HMDA REST API
    
Frontend also polls /map-data for choropleth updates

### Project Structure
redline-reveal/
├── CLAUDE.md
├── .env
├── .gitignore
├── README.md
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── backend/
│   ├── pyproject.toml
│   ├── main.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── dispatch_agent.py
│   │   └── hmda_analyst.py
│   ├── tools/
│   │   ├── __init__.py
│   │   └── mcp_tools.py
│   ├── mcp_server/
│   │   ├── main.py
│   │   └── hmda_tools.py
│   └── data/
│       └── nyc_zip_codes.json
├── Dockerfile
└── deploy.sh

### HMDA Data API (NO FILE DOWNLOADS)
Base: https://ffiec.cfpb.gov/api/public/hmda/
Key endpoint: /aggregations
Parameters: year=2022, geography_type=zip_code
Filter: derived_race, state_code=NY, action_taken=1,3

### Environment Variables (already in .env)
GEMINI_API_KEY=AIzaSyB5toWw_YwJDMjtNG813Jqk5b_BEEflgKM
GOOGLE_MAPS_API_KEY=AIzaSyCeZyqzMPKR6MlTmVUf-H6eTNd94FpVWro
GOOGLE_CLOUD_PROJECT=redline-reveal
GOOGLE_CLOUD_REGION=us-central1

### Demo Flow (judges watch this)
1. NYC map loads with neutral zip code coloring
2. User clicks mic button
3. Says: "I'm a Latino homeowner trying to buy in Jackson Heights Queens"
4. Map lights up with denial rate data for Queens zip codes
5. Voice responds with narrative about discrimination patterns
6. Map updates IN REAL TIME as voice speaks

### ADK Pattern (from lab Level 4)
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents.live_request_queue import LiveRequestQueue

dispatch_agent = LlmAgent(
    name="DispatchAgent",
    model="gemini-2.0-flash-live-001",
    instruction="...",
    tools=[AgentTool(agent=hmda_analyst)]
)

hmda_analyst = LlmAgent(
    name="HMDAAnalystAgent",
    model="gemini-2.5-flash",
    instruction="...",
    tools=[get_hmda_tool()]
)

### Build Order
1. FastMCP server with HMDA API tool (30 min)
2. HMDAAnalystAgent with MCP tool (30 min)
3. DispatchAgent with LiveAPI + A2A (45 min)
4. FastAPI WebSocket backend (30 min)
5. Frontend: voice UI + Google Maps choropleth (90 min)
6. Integration test (30 min)
7. STOP — user handles Cloud Run deployment

### Rules
- Build sequentially
- Test each layer before moving on
- Use uv for all Python packages
- Single HTML+JS frontend, no framework
- Map visualization is the VISUAL WOW
- Voice must actually work, no mocks
- Stop and tell user before any gcloud deployment commands

### Git Strategy (IMPORTANT)
- Repo: https://github.com/raunak-choudhary/redline-reveal-gdg-hackathon-2026.git
- Commit after EVERY major step completion
- Push to GitHub after every commit
- Commit messages must be descriptive:
  "feat: add FastMCP server with HMDA API integration"
  "feat: implement HMDAAnalystAgent with zip code analysis"
  "feat: add DispatchAgent with Gemini Live bidirectional streaming"
  "feat: build FastAPI WebSocket backend"
  "feat: add Google Maps choropleth frontend"
  "fix: handle HMDA API rate limiting"
- NEVER commit .env file
- Add all new files with git add before committing
