# Redline Reveal — NYC Mortgage Discrimination Explorer

> A voice-powered investigative platform that exposes racial bias in New York City mortgage lending using real federal data, built live at the GDG NYC Hackathon 2026.

**Live Demo:** https://redline-reveal-969543468135.us-central1.run.app

---

## What This Project Is

Redline Reveal is an AI-powered civic journalism tool. You speak a neighborhood or demographic profile into the app — say *"I'm a Latino homeowner trying to buy in Jackson Heights Queens"* — and within seconds, the map of New York City lights up with real mortgage denial rate data for that community, the browser narrates the discrimination pattern in plain language, and the Investigate tab shows you exactly which banks are responsible by name.

Every number on screen is sourced from the CFPB Home Mortgage Disclosure Act (HMDA) 2022 dataset — the federal data that every mortgage lender in the United States is legally required to file. This is not an estimate, not a model, and not a simulation. It is the actual lending record of New York City.

The name comes from the 1930s federal practice of drawing red lines around minority neighborhoods on city maps, marking them "hazardous" for lending. Banks used those maps to systematically deny home loans to Black, Hispanic, and immigrant families for decades. The Fair Housing Act of 1968 outlawed explicit redlining. HMDA data from 2022 shows the pattern never fully stopped — it just moved into spreadsheets and algorithms.

---

## The Problem Being Solved

Most people who get denied a mortgage never know if race played a role. The data to prove it exists — it is public, it is federal, it is filed every year — but it lives buried in government databases that require technical expertise to query. Civil rights lawyers use it. Academic researchers use it. Investigative journalists occasionally surface it in long-form articles. Individual homebuyers and community advocates almost never access it.

Redline Reveal makes that data conversational. Anyone can walk up, speak a question in plain English, and immediately see — on a live map, with spoken narration — how their community is being treated by the mortgage industry compared to white applicants in the same borough.

---

## Architecture

The system is built in four layers that work together in real time.

### Layer 1 — Browser (Frontend)

The frontend is deliberately minimal: plain HTML, CSS, and vanilla JavaScript with no framework or build step. This was a conscious choice to keep the demo fast, portable, and fully auditable.

The interface has three tabs:

- **Explore** — the main voice interface. A microphone button activates the Web Speech API (Chrome/Edge native speech recognition). The spoken transcript is processed locally in the browser, which parses the demographic group and NYC borough from the query, then fires the appropriate API calls.
- **Investigate** — the lender investigation panel. Shows ranked lists of specific banks with their disparity ratios (minority denial rate divided by white denial rate for the same borough). Users can query by borough and race using dropdowns or pre-built quick chips.
- **Data** — live statistics from the last query, plus educational context about redlining and the HMDA dataset.

The map is rendered using the **Google Maps JavaScript API** with a custom dark-theme choropleth layer. Borough-level polygons are drawn as `google.maps.Polygon` objects and colored by denial rate. A ZIP code view uses the **Google Maps Data Layer** with a full GeoJSON file of 262 NYC ZIP code tabulation areas.

When a voice query mentions a specific neighborhood — Jackson Heights, Crown Heights, Harlem, Flushing — the **Google Geocoding API** resolves that neighborhood name to precise coordinates and zooms the map there, making the connection between the spoken word and the geography immediate and visceral.

### Layer 2 — FastAPI Backend (Cloud Run)

The backend is a Python FastAPI application deployed on Google Cloud Run. It serves:

- The frontend static files (HTML, CSS, JS, GeoJSON)
- A `/config` endpoint that delivers the Maps API key to the browser at runtime, keeping it out of committed source
- A `/map-data` endpoint that returns denial rates by borough and ZIP code, with optional race filtering
- A `/borough/{name}` endpoint for individual borough statistics and race breakdowns
- A `/lenders/{borough}` endpoint that returns the ranked lender bias analysis
- A `/summary` endpoint for citywide summaries by race
- A WebSocket endpoint at `/ws/voice` for maintaining the persistent connection to the Google ADK agent layer

The backend also handles a 24-hour in-memory cache of the base map data so the first map load is instant on repeat visits.

### Layer 3 — Google ADK Agent Pipeline (A2A)

This is the core AI layer. Three agents are wired together using the Google Agent Development Kit (ADK) in an Agent-to-Agent (A2A) pattern.

**DispatchAgent** (`gemini-2.0-flash-live-001`)
The orchestrator. It maintains the live WebSocket session and routes incoming queries to the appropriate specialist agent. It decides whether a query is about general denial patterns (routes to HMDAAnalystAgent) or about specific bank behavior (routes to LenderInvestigatorAgent). It is also responsible for sending map update events back to the browser as the conversation progresses.

**HMDAAnalystAgent** (`gemini-2.5-flash`)
The data analyst. Called via ADK's `AgentTool` pattern (A2A). It receives structured queries about specific boroughs and demographic groups, calls the MCP tools to fetch HMDA data, and returns narrative analysis with specific numbers, disparity ratios, and context about what the data means.

**LenderInvestigatorAgent** (`gemini-2.5-flash`)
The investigative journalist. Also called via `AgentTool`. When a user asks which specific banks are responsible for discriminatory patterns, this agent fetches the top mortgage lenders active in a borough from the HMDA filers endpoint, queries each lender's denial rates for the target racial group versus white applicants in parallel, ranks them by disparity ratio, and returns a ranked list of offenders with names and numbers.

### Layer 4 — Data Sources

**FastMCP Server** wraps the CFPB HMDA REST API as callable tools for the ADK agents. The key endpoints used are:
- `/view/aggregations` — returns application counts by action taken (originated vs. denied), geography, and race
- `/view/filers` — returns active mortgage lenders by county and year, identified by their LEI (Legal Entity Identifier)

**Google BigQuery** caches the lender bias rankings. The lender analysis for a single borough and race requires approximately 12 parallel API calls to the HMDA service. BigQuery stores the results with a 24-hour TTL so repeat queries within the same day are instant. The cache table schema stores borough, race, year, computed rankings as JSON, and a timestamp.

**Google Cloud Secret Manager** stores the Gemini API key and Google Maps API key. These are injected into the Cloud Run container at runtime via `--set-secrets` and never appear in source code or environment files committed to the repository.

### Architecture Diagram Description (for visual rendering)

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER (Frontend)                        │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  Web Speech API │  │ Google Maps JS   │  │ Geocoding API  │  │
│  │  (Voice Input)  │  │ (Choropleth Map) │  │ (Nbhd Zoom)    │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘  │
│           │                    │                      │           │
│           └──────────┬─────────┘                      │           │
│                      │                                │           │
│         3-Tab UI: Explore / Investigate / Data        │           │
└──────────────────────┼────────────────────────────────┘           │
                       │ HTTP REST + WebSocket                       │
                       ▼                                             │
┌─────────────────────────────────────────────────────────────────┐ │
│              FastAPI Backend — Google Cloud Run                  │ │
│                                                                   │ │
│   /map-data   /borough   /lenders   /summary   /ws/voice         │ │
│                     │                                             │ │
│            Google Cloud Secret Manager                           │ │
└─────────────────────┼─────────────────────────────────────────── ┘ │
                       │ ADK AgentTool (A2A)                          │
                       ▼                                              │
┌─────────────────────────────────────────────────────────────────┐  │
│                    Google ADK Agent Layer                        │  │
│                                                                   │  │
│  ┌─────────────────────────────────────────────────────────┐    │  │
│  │  DispatchAgent  (gemini-2.0-flash-live-001)             │    │  │
│  │  Orchestrates routing, maintains WebSocket session       │    │  │
│  └─────────────────┬──────────────────────┬────────────────┘    │  │
│                     │ AgentTool            │ AgentTool           │  │
│          ┌──────────▼──────────┐  ┌───────▼──────────────────┐  │  │
│          │  HMDAAnalystAgent   │  │  LenderInvestigatorAgent  │  │  │
│          │  gemini-2.5-flash   │  │  gemini-2.5-flash         │  │  │
│          │  Denial rates,      │  │  Bank bias rankings,      │  │  │
│          │  race breakdowns    │  │  disparity ratios         │  │  │
│          └──────────┬──────────┘  └───────┬──────────────────┘  │  │
└─────────────────────┼────────────────────-┼─────────────────────┘  │
                       │ MCP Tools           │ MCP Tools               │
                       ▼                     ▼                         │
┌─────────────────────────────────────────────────────────────────┐   │
│                       Data Layer                                 │   │
│                                                                   │   │
│  ┌──────────────────────┐      ┌───────────────────────────┐    │   │
│  │  FastMCP Server      │      │  Google BigQuery           │    │   │
│  │  CFPB HMDA REST API  │      │  Lender rankings cache     │    │   │
│  │  /view/aggregations  │      │  24-hour TTL               │    │   │
│  │  /view/filers        │      │                            │    │   │
│  └──────────────────────┘      └───────────────────────────┘    │   │
└─────────────────────────────────────────────────────────────────┘   │
                                                                        │
        Google Maps Platform (Maps JS API + Geocoding API) ────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vanilla HTML5 / CSS3 / JavaScript (no framework) |
| Maps | Google Maps JavaScript API — choropleth polygons + Data Layer |
| Geocoding | Google Geocoding API — neighborhood-level map zoom |
| Voice Input | Web Speech API (SpeechRecognition, SpeechSynthesis) |
| Voice Output | Web Speech API (SpeechSynthesis — browser TTS) |
| Backend | Python 3.11 / FastAPI / Uvicorn |
| AI Agents | Google ADK (Agent Development Kit) |
| LLM — Voice | Gemini 2.0 Flash Live (gemini-2.0-flash-live-001) |
| LLM — Analysis | Gemini 2.5 Flash (gemini-2.5-flash) |
| Agent Pattern | ADK AgentTool (A2A — Agent to Agent) |
| MCP Tools | FastMCP server wrapping CFPB HMDA REST API |
| Data | CFPB HMDA 2022 — real federal mortgage disclosure data |
| Caching | Google BigQuery (lender bias rankings, 24hr TTL) |
| Secrets | Google Cloud Secret Manager |
| Deployment | Google Cloud Run (containerized, serverless) |
| Container | Docker (python:3.11-slim base) |
| Package Manager | uv |
| GeoJSON | NYC ZIP Code Tabulation Areas (262 ZIP codes) |

---

## Project Structure

```
redline-reveal/
├── README.md                        # This file
├── CLAUDE.md                        # AI assistant project context
├── Dockerfile                       # Container definition for Cloud Run
├── deploy.sh                        # One-command Cloud Run deployment script
├── run.sh                           # Local development startup script
├── .env                             # Local secrets (never committed)
├── .gitignore
│
├── frontend/
│   ├── index.html                   # Single-page app shell, 3-tab layout
│   ├── app.js                       # All frontend logic (~1000 lines)
│   │   ├── initMap()                # Google Maps setup + borough polygons
│   │   ├── loadZipGeoJson()         # ZIP code Data Layer setup
│   │   ├── setViewMode()            # Borough ↔ ZIP toggle
│   │   ├── geocodeNeighborhood()    # Geocoding API zoom
│   │   ├── handleVoiceQuery()       # Central voice query router
│   │   ├── loadLenderRankings()     # Fetch + render lender bias table
│   │   ├── switchTab()              # Tab navigation
│   │   └── speakResponse()         # Browser TTS output
│   ├── style.css                    # Dark theme, responsive, 3-tab layout
│   └── nyc_zips.geojson             # 262 NYC ZIP code polygons (606KB)
│
└── backend/
    ├── main.py                      # FastAPI app, all REST + WebSocket routes
    ├── pyproject.toml               # Python project config (uv)
    │
    ├── agents/
    │   ├── dispatch_agent.py        # DispatchAgent — ADK BiDi, A2A orchestrator
    │   ├── hmda_analyst.py          # HMDAAnalystAgent — denial rate analysis
    │   └── lender_investigator.py   # LenderInvestigatorAgent — bank bias ranking
    │
    ├── mcp_server/
    │   ├── main.py                  # FastMCP server entry point
    │   ├── hmda_tools.py            # CFPB HMDA API tools (denial rates, breakdowns)
    │   └── lender_tools.py          # HMDA filer tools + BigQuery caching
    │
    ├── tools/
    │   └── mcp_tools.py             # MCP tool wrappers for ADK agents
    │
    └── data/
        └── nyc_zip_codes.json       # NYC ZIP → borough mapping reference
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- `uv` package manager (`pip install uv` or `brew install uv`)
- A `.env` file in the project root with the following keys:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
GOOGLE_CLOUD_PROJECT=redline-reveal
GOOGLE_CLOUD_REGION=us-central1
```

To get these keys:
- **GEMINI_API_KEY**: Google AI Studio → API Keys → Create key
- **GOOGLE_MAPS_API_KEY**: Google Cloud Console → APIs & Services → Credentials → Maps JavaScript API key (enable Maps JS API + Geocoding API)

### Install Dependencies

```bash
cd backend
uv venv
uv pip install -e .
```

### Start the Server

From the project root:

```bash
bash run.sh
```

This starts the FastAPI server at `http://localhost:8080` with hot reload enabled.

Open Chrome or Edge (required for Web Speech API) and navigate to `http://localhost:8080`.

### What Runs on Startup

1. FastAPI loads and mounts the frontend at `/static`
2. The backend pre-fetches base NYC denial rate data from the CFPB HMDA API
3. The browser loads, fetches `/config` for the Maps API key, and initializes Google Maps
4. Borough polygons render with initial denial rate coloring
5. The WebSocket connection to the ADK agent layer is established

---

## Deploying to Google Cloud Run

### Prerequisites

- Google Cloud CLI (`gcloud`) installed and authenticated
- Project `redline-reveal` created in Google Cloud Console
- APIs enabled: Cloud Run, Cloud Build, Container Registry, BigQuery, Secret Manager
- Secrets stored:

```bash
echo -n "your_gemini_key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your_maps_key"   | gcloud secrets create maps-api-key   --data-file=-
```

### Deploy

```bash
bash deploy.sh
```

This builds the Docker image via Cloud Build, pushes it to Container Registry, and deploys a new Cloud Run revision. The live URL is printed at the end.

### Google Maps API Key Setup

After deploying, add the Cloud Run URL to the Maps API key's HTTP referrer restrictions in Google Cloud Console:

```
https://your-cloud-run-url.run.app/*
```

This prevents unauthorized use of your Maps API key from other domains.

---

## Features

### Voice Exploration
Speak any question about NYC mortgage lending in plain English. The app understands borough names, neighborhood names (Jackson Heights, Crown Heights, Harlem, Flushing, etc.), racial and ethnic groups, and general housing-related queries. Voice recognition runs entirely in the browser via the Web Speech API.

### Real-Time Map Choropleth
The NYC map updates instantly after each query. Borough polygons are colored on a green-to-red gradient based on mortgage denial rates. The ZIP Code view switches to 262 individual ZIP code boundaries for neighborhood-level granularity. Hovering over any polygon shows exact numbers.

### Neighborhood Zoom (Geocoding API)
When a specific neighborhood is mentioned in a voice query, the Geocoding API resolves it to precise coordinates and the map animates there — from "Jackson Heights" to the exact blocks of Jackson Heights in Queens, zoomed in to street level.

### Lender Investigation
The Investigate tab identifies which specific banks showed the worst racial disparity ratios in a given borough. Rankings show the institution name, denial rate for the queried group, white applicant denial rate for comparison, and the disparity ratio. Results are cached in BigQuery for 24 hours.

### Race Breakdown by Borough
Clicking any borough on the map or asking about it by voice returns a full racial breakdown — denial rates for Black, Hispanic, Asian, White, and other groups side by side.

### Citywide Comparison
Queries without a specific borough return citywide summaries across all five boroughs, letting users compare how a particular racial group is treated across Manhattan, Brooklyn, Queens, the Bronx, and Staten Island simultaneously.

### Three-Tab Interface
- **Explore**: Voice mic, example query chips, and conversation transcript
- **Investigate**: Lender rankings table with manual controls and quick-access chips
- **Data**: Live statistics from the last query with educational context about redlining

### Mobile Responsive
The layout stacks vertically on phones — map on top, controls below. The mic button is sized for thumb use. All tabs work on mobile. Tested at 375px (iPhone) and 768px (iPad).

---

## Data Source

All mortgage data comes from the **CFPB Home Mortgage Disclosure Act (HMDA) 2022 dataset**.

HMDA is a federal law enacted in 1975. Every mortgage lender that meets volume thresholds must file detailed records of every mortgage application they receive, including the applicant's race, ethnicity, income, loan amount, property location, and whether the loan was approved or denied. The Consumer Financial Protection Bureau (CFPB) publishes this data publicly at `ffiec.cfpb.gov`.

The 2022 filing covers approximately 14 million mortgage applications nationwide. This project queries the NYC subset in real time via the CFPB's public REST API — no data is downloaded or stored locally beyond the 24-hour BigQuery lender cache.

---

## What the Data Shows

In 2022, across New York City's five boroughs:

- **Black applicants** were denied mortgages at rates 2 to 3 times higher than white applicants in the same boroughs
- **Hispanic/Latino applicants** faced similar disparities, particularly in Queens and the Bronx
- The Bronx consistently shows the highest overall denial rates of any NYC borough
- These disparities persist even when controlling for geography — the comparison is always within the same borough, not across different housing markets

These are not allegations. These are the lenders' own reported numbers.

---

## Google APIs Used

| API | Purpose |
|-----|---------|
| Google Maps JavaScript API | Interactive choropleth map rendering |
| Google Geocoding API | Resolves neighborhood names to coordinates for map zoom |
| Google ADK (Agent Development Kit) | Multi-agent orchestration with A2A pattern |
| Gemini 2.0 Flash Live | Real-time voice agent (DispatchAgent) |
| Gemini 2.5 Flash | Data analysis agents (HMDA + Lender) |
| Google BigQuery | Lender bias rankings cache with 24-hour TTL |
| Google Cloud Run | Serverless container deployment |
| Google Cloud Build | CI/CD container image builds |
| Google Cloud Secret Manager | Secure API key storage at runtime |

---

## Hackathon Context

Built solo at the **GDG NYC Hackathon, March 28 2026**.

This project was built entirely in a single day — architecture design, backend agents, MCP server, BigQuery integration, frontend choropleth, voice pipeline, mobile responsive layout, and Cloud Run deployment. Every feature shown in the demo is running live on real federal data with no mocked responses.

---

## Future Work

The current build is a working proof of concept. There are several directions worth pursuing:

- **Historical trend analysis** — HMDA data goes back decades. Showing how denial rate disparities have changed from 2010 to 2022 on an animated timeline map would be a powerful addition.
- **Income-controlled analysis** — The current disparity calculations are raw rates. Controlling for income bracket would answer the common objection that denial disparities reflect income differences rather than race.
- **Lender detail pages** — Clicking a bank name could open a full profile: their lending history, geographic footprint, and disparity trend over multiple years.
- **Alert system** — Community organizations could subscribe to alerts when a lender's disparity ratio crosses a threshold in their borough.
- **Multi-city expansion** — The HMDA API covers the entire United States. The architecture generalizes to any metropolitan area with minimal changes.
- **Legal referral integration** — Connecting users who identify discriminatory patterns in their own application history to fair housing legal aid organizations.
- **Multilingual voice support** — Many of the most affected communities in NYC are Spanish-dominant or Mandarin-dominant. The Web Speech API supports both.

---

## License

MIT License. Data is public domain (federal government CFPB HMDA dataset).

---

## Author

**Raunak Choudhary**
**NYU MS CS Grad Student**
GDG NYC Hackathon 2026
