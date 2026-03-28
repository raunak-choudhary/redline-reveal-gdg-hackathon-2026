# Judges Instructions — Redline Reveal
### GDG NYC Hackathon 2026

**Live URL:** https://redline-reveal-969543468135.us-central1.run.app

**Browser Required:** Google Chrome or Microsoft Edge (Web Speech API for voice recognition is not supported in Safari or Firefox)

---

## What You Are Looking At

Redline Reveal is a voice-powered civic journalism platform that exposes racial bias in New York City mortgage lending using real federal HMDA 2022 data. You speak a neighborhood or demographic profile, the map updates in real time, and the app narrates the discrimination pattern back to you using actual numbers from the federal lending record.

Everything you see on screen — every percentage, every denial count, every bank name — is pulled live from the CFPB's public HMDA API or cached in Google BigQuery. Nothing is mocked or hardcoded.

---

## Quick Setup Before Testing

1. Open the URL above in **Chrome or Edge**
2. Wait for the map to fully load (dark NYC map with colored borough polygons — takes 2–3 seconds)
3. When the map appears, the status indicator in the top right should show **"Connected"**
4. Allow microphone access when the browser prompts — this is needed for voice features
5. Make sure your **device volume is turned up** — the app speaks responses aloud

---

## Feature 1 — Voice Exploration (Core Feature)

**What to test:** Click the red microphone button, speak one of the statements below, then click it again to stop.

The app will:
- Show your spoken words in the transcript panel on the left
- Update the map with real denial rate data colored by severity (green = low, red = high)
- Speak a narrative response describing the discrimination pattern out loud
- Update the Data tab with live statistics

### Test Statements — speak these one at a time

**Statement 1 — Neighborhood + Demographics (Best Demo Statement)**
> *"I'm a Latino homeowner trying to buy in Jackson Heights Queens"*

Expected: Map updates for Hispanic applicants. Transcript shows spoken words + AI response with specific denial rate numbers for Queens. Browser speaks the response aloud. Data tab updates with denial rate, white comparison rate, and disparity ratio.

---

**Statement 2 — Race + Borough**
> *"Show me Black mortgage applicants in Brooklyn"*

Expected: Map recolors to show Black applicant denial rates across all five boroughs. Response includes the denial rate for Black applicants in Brooklyn specifically and compares it to the White applicant rate in the same borough.

---

**Statement 3 — Borough Only (No Race)**
> *"What's happening in the Bronx?"*

Expected: Map resets to all-applicant view. Response identifies which racial group faces the highest denial rates in the Bronx and names the disparity compared to White applicants.

---

**Statement 4 — Citywide Race Comparison**
> *"Compare Asian mortgage applicants across all five boroughs"*

Expected: Map updates for Asian applicants citywide. Response names the denial rate for Asian applicants in each of the five boroughs.

---

**Statement 5 — Harlem / Manhattan Neighborhood**
> *"What do Black families face trying to buy a home in Harlem?"*

Expected: Map updates for Black applicants. Response covers Manhattan denial rates with specific numbers. The **Google Geocoding API** resolves "Harlem" to its precise geographic coordinates, enabling location-aware data retrieval for that specific neighborhood.

---

**Statement 6 — Off-Topic Rejection (Guardrail Test)**
> *"What is the weather like today?"*

Expected: App politely declines and redirects. Response says it focuses on NYC mortgage discrimination data and suggests a relevant query. Map does not change.

---

## Feature 2 — Example Chips (No Mic Needed)

**What to test:** Click any of the gray chip buttons under "Try asking:" in the Explore tab. These run preset queries without voice.

Chips available:
- 🏠 Jackson Heights Latino
- 📊 Black applicants Brooklyn
- 🗺️ Compare all boroughs
- 🏙️ Asian applicants Queens

Expected: Each chip updates the map, adds an entry to the transcript, and pulls real data. Good way to demo if there are microphone issues in the demo environment.

---

## Feature 3 — ZIP Code vs Borough Toggle

**What to test:** Look for the **Borough / ZIP Code** toggle buttons overlaid on the map (top-left of map area).

1. Click **ZIP Code**
2. The map switches from 5 borough polygons → 262 individual NYC ZIP code areas, each colored by denial rate
3. Hover over individual ZIP codes to see neighborhood-level statistics
4. Click **Borough** to switch back

Expected: The ZIP code view shows granular neighborhood-level variance within boroughs. Some ZIP codes inside a single borough show dramatically different rates — revealing how discrimination concentrates in specific neighborhoods even within the same borough.

---

## Feature 4 — Borough Hover Tooltips

**What to test:** Hover your mouse slowly over each of the five borough polygons on the map.

Expected: A tooltip appears showing:
- Borough name
- Denial rate percentage
- Number of applications denied vs. total applications

---

## Feature 5 — Lender Investigation Tab (A2A Agent Feature)

**What to test:** Click the **Investigate** tab in the left panel.

### Option A — Quick Chips
Click any of the pre-built investigation chips:
- 🏦 Worst banks · Brooklyn · Black
- 🏦 Worst banks · Queens · Hispanic
- 🏦 Worst banks · Bronx · Black

Expected: The lender ranking list populates with real bank names, their denial rates for the queried group, white applicant denial rates for comparison, and a disparity ratio colored by severity (red = severe, yellow = moderate, green = low). Source label shows whether results came from live HMDA data or BigQuery cache.

### Option B — Manual Analysis
1. Use the **Borough** dropdown to select any borough
2. Use the **Group** dropdown to select Black, Hispanic, or Asian applicants
3. Click **Analyze**

Expected: Same ranked lender list as above, customized to your selection.

### Option C — Via Voice (Auto-switches tab)
Go back to Explore tab, click mic, say:
> *"Which banks are discriminating against Black applicants in Manhattan?"*

Expected: App automatically switches to the Investigate tab and populates the lender rankings. No manual navigation needed.

---

## Feature 6 — Data Tab

**What to test:** Click the **Data** tab after running any voice query.

Expected:
- **Queried Group** — the demographic group from the last query
- **Denial Rate** — their mortgage denial rate in percentage
- **White Rate (same area)** — white applicant denial rate in the same geography for direct comparison
- **Disparity Ratio** — how many times higher the denial rate is vs. white applicants
- **Applications** — total application count from the federal dataset

The two context boxes below explain redlining history and the HMDA data source.

---

## Feature 7 — Google Geocoding API Integration

The app integrates the **Google Geocoding API** to perform location intelligence on neighborhood mentions within voice queries. When a user mentions a specific neighborhood — Jackson Heights, Crown Heights, Harlem, Flushing, Bed-Stuy, Astoria, Mott Haven — the Geocoding API resolves that neighborhood name to precise geographic coordinates. This enables the app to anchor its data queries to specific geographic locations rather than treating all borough-level queries as equivalent.

**To see this in action:**

Say: *"I'm a Latino homeowner trying to buy in Jackson Heights Queens"*

Then say: *"What about Crown Heights Brooklyn for Black applicants?"*

The Geocoding API resolves each neighborhood name to its real-world coordinates, and the system uses that location context to serve geographically precise data. This is what makes neighborhood-specific queries more accurate than borough-level queries alone.

Neighborhoods supported by the Geocoding integration:
- **Queens**: Jackson Heights, Flushing, Astoria, Jamaica, Long Island City, Bayside, Forest Hills, Ridgewood, Sunnyside, Woodside
- **Brooklyn**: Bedford-Stuyvesant, Crown Heights, Flatbush, Bushwick, East New York, Canarsie, Williamsburg, Greenpoint, Bay Ridge, Brownsville, Sunset Park
- **Manhattan**: Harlem, East Harlem, Washington Heights, Inwood, Upper East Side, Upper West Side, Lower East Side, Chinatown, Hell's Kitchen, Morningside Heights
- **Bronx**: Mott Haven, Fordham, Pelham Bay, South Bronx, Tremont, Hunts Point
- **Staten Island**: St. George, Port Richmond, New Dorp

---

## Feature 8 — Mobile Responsive Layout

**What to test:** Open the URL on a phone or use Chrome DevTools device emulation (F12 → toggle device toolbar → iPhone 12).

Expected:
- Map appears at the top of the screen, full width
- Control panel stacks below the map
- Tab navigation sticks to the top of the panel as you scroll
- Microphone button is larger and centered for thumb access
- Example chips wrap horizontally

---

## Complete Google APIs and Technologies Used

| Technology | Role in the Demo |
|------------|-----------------|
| Google Maps JavaScript API | Interactive choropleth map, borough polygons, ZIP code Data Layer |
| Google Geocoding API | Resolves neighborhood names to geographic coordinates for location-aware queries |
| Google ADK (Agent Development Kit) | Three-agent A2A pipeline: DispatchAgent → HMDAAnalystAgent + LenderInvestigatorAgent |
| Gemini 2.0 Flash Live | Real-time bidirectional voice agent (DispatchAgent) |
| Gemini 2.5 Flash | Data analysis agents — denial rates and lender bias rankings |
| Google BigQuery | Caches lender bias analysis results with 24-hour TTL |
| Google Cloud Run | Serverless deployment of the FastAPI backend |
| Google Cloud Build | Container image build pipeline |
| Google Cloud Secret Manager | Secure API key injection at runtime |
| Web Speech API | Browser-native voice recognition and text-to-speech |
| CFPB HMDA REST API | Real federal mortgage data — queried live via FastMCP tools |

---

## Scoring Notes for Judges

### UX / Innovation (40%)
The interface removes the technical barrier between the public and federal lending data entirely. A community activist, a first-time homebuyer, or a civil rights attorney can walk up, speak a question in plain English, and get the answer in seconds. The voice + map combination makes the data visceral in a way that a data table never could.

### Technical Implementation (30%)
- Three Google ADK agents wired in A2A pattern (not a chatbot, not RAG)
- Live HMDA API queries via FastMCP server — no static dataset
- Google BigQuery caching layer for lender analysis
- Google Geocoding API for location intelligence on neighborhood mentions
- Real-time choropleth at both borough and ZIP code granularity
- Deployed on Cloud Run with Secret Manager — production-grade infrastructure

### Demo Quality (30%)
Every feature in this document is live and working. The data is real. The voice works. The map updates in real time. The lender names are real institutions from federal records. There are no loading screens that hide pre-computed answers.

---

## If Something Doesn't Work

| Issue | Fix |
|-------|-----|
| Mic button does nothing | Make sure you're using Chrome or Edge, not Safari |
| No voice audio response | Turn up system volume; check browser isn't muted |
| Map shows grey polygons | Wait 3–4 seconds for HMDA API prefetch to complete |
| Lender list shows "investigating" | First query hits live HMDA API — takes 8–12 seconds. Subsequent queries for same borough/race are instant from BigQuery cache |
| "Connected" not showing | Refresh the page; WebSocket reconnects automatically |

---

## Data Integrity Statement

Every statistic shown in Redline Reveal is sourced from the **CFPB HMDA 2022 public dataset** — federal data filed by mortgage lenders under the Home Mortgage Disclosure Act. The API is queried live during the demo. No numbers are hardcoded, estimated, or generated by AI. The AI agents analyze and narrate the data — they do not fabricate it.

---

*Built solo · GDG NYC Hackathon · March 28, 2026 · Raunak Choudhary*
