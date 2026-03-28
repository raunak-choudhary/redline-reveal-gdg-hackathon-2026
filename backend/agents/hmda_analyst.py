"""
HMDAAnalystAgent — gemini-2.5-flash
Analyzes NYC mortgage discrimination data from HMDA CFPB API.
Called as an A2A sub-agent by DispatchAgent via AgentTool.
"""

import os
import sys

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Import HMDA tool functions directly (avoids relative import issues when run standalone)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_server.hmda_tools import (
    get_borough_denial_rate,
    get_all_boroughs_denial_rates,
    get_borough_race_breakdown,
    get_nyc_citywide_summary,
    _resolve_borough,
    NYC_ZIPS,
    BOROUGH_FIPS,
)

HMDA_ANALYST_INSTRUCTION = """
You are an expert mortgage discrimination analyst specializing in NYC housing data.
You have access to real CFPB HMDA (Home Mortgage Disclosure Act) data for New York City.

YOUR MISSION:
Analyze mortgage approval and denial patterns by race, ethnicity, and neighborhood.
Reveal systemic discrimination patterns backed by real data.

AVAILABLE TOOLS:
- get_borough_mortgage_stats: Get denial rate for a borough/neighborhood, optionally by race
- get_all_nyc_boroughs_data: Get denial rates across all 5 boroughs + zip-code map for choropleth
- get_race_disparity_analysis: Get denial rates broken down by ALL race groups for a borough
- get_nyc_mortgage_summary: Get citywide NYC summary with borough breakdown

WORKFLOW:
1. Parse the user's location/demographic (neighborhood, borough, race/ethnicity)
2. Call the appropriate HMDA tool(s) to get real data
3. ALWAYS call get_all_nyc_boroughs_data to provide map data for the choropleth
4. Synthesize the data into a compelling narrative about discrimination patterns

NARRATIVE STYLE:
- Speak as a knowledgeable expert revealing systemic injustice
- Quote specific percentages and numbers from the data
- Compare denial rates across racial groups (White vs. Black, Hispanic, etc.)
- Reference historical context: redlining, Fair Housing Act, CRA
- Be clear about what the numbers mean for real families
- Keep analysis focused and specific to the queried location/group

OUTPUT FORMAT:
Always return a JSON object with:
{
  "narrative": "...", // 2-4 sentence spoken analysis for the voice agent
  "map_data": {       // from get_all_nyc_boroughs_data
    "zip_map": {...},
    "borough_data": {...}
  },
  "highlight_borough": "...", // primary borough being discussed
  "key_stats": {              // extracted numbers for display
    "queried_denial_rate": X,
    "white_denial_rate": Y,
    "disparity_ratio": Z
  }
}

EXAMPLE NARRATIVE:
"In Queens, Hispanic and Latino applicants faced a mortgage denial rate of 38.1% in 2022 —
nearly two and a half times the 15.7% rate for White applicants in the same borough.
Jackson Heights, one of NYC's most diverse neighborhoods, sits in a county where
3,199 minority applications were processed, with 1,220 denials.
This pattern echoes the legacy of redlining that historically excluded communities
of color from wealth-building through homeownership."
"""


def get_hmda_tools() -> list:
    """Return ADK FunctionTool list for the HMDA analyst."""
    from mcp_server.hmda_tools import (
        get_borough_denial_rate as _bdr,
        get_all_boroughs_denial_rates as _abdr,
        get_borough_race_breakdown as _brb,
        get_nyc_citywide_summary as _ncs,
    )

    async def get_borough_mortgage_stats(
        borough_or_neighborhood: str,
        year: int = 2022,
        race: str = None,
    ) -> str:
        """
        Get mortgage denial rate for a NYC borough or neighborhood, optionally by race/ethnicity.

        Args:
            borough_or_neighborhood: Borough (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
                                     or neighborhood (Jackson Heights, Harlem, Bed Stuy, etc.)
            year: Data year (default 2022)
            race: Optional — Asian, Black, Hispanic, White, Native American, Pacific Islander

        Returns:
            JSON with denial_rate_pct, originated, denied counts, and zip_codes list
        """
        import json
        result = await _bdr(borough_or_neighborhood, year, race)
        return json.dumps(result)

    async def get_all_nyc_boroughs_data(
        year: int = 2022,
        race: str = None,
    ) -> str:
        """
        Get mortgage denial rates for all 5 NYC boroughs + zip_map for choropleth.
        ALWAYS call this to provide map visualization data.

        Args:
            year: Data year (default 2022)
            race: Optional — Asian, Black, Hispanic, White, Native American, Pacific Islander

        Returns:
            JSON with borough_data and zip_map (zip_code -> denial_rate_pct)
        """
        import json
        result = await _abdr(year, race)
        return json.dumps(result)

    async def get_race_disparity_analysis(
        borough_or_neighborhood: str,
        year: int = 2022,
    ) -> str:
        """
        Get denial rates for EVERY race group in a borough side by side.
        Use this to show disparity (e.g. White 14.9% vs Black 40% in same borough).

        Args:
            borough_or_neighborhood: Borough or neighborhood name
            year: Data year (default 2022)

        Returns:
            JSON with race_breakdown dict showing denial_rate_pct per group
        """
        import json
        result = await _brb(borough_or_neighborhood, year)
        return json.dumps(result)

    async def get_nyc_mortgage_summary(
        year: int = 2022,
        race: str = None,
    ) -> str:
        """
        Get citywide NYC mortgage lending summary with per-borough breakdown.

        Args:
            year: Data year (default 2022)
            race: Optional race/ethnicity filter

        Returns:
            JSON with citywide_denial_rate_pct and borough_summaries
        """
        import json
        result = await _ncs(year, race)
        return json.dumps(result)

    return [
        FunctionTool(get_borough_mortgage_stats),
        FunctionTool(get_all_nyc_boroughs_data),
        FunctionTool(get_race_disparity_analysis),
        FunctionTool(get_nyc_mortgage_summary),
    ]


def create_hmda_analyst() -> LlmAgent:
    """Create and return the HMDAAnalystAgent."""
    return LlmAgent(
        name="HMDAAnalystAgent",
        model="gemini-2.5-flash",
        instruction=HMDA_ANALYST_INSTRUCTION,
        tools=get_hmda_tools(),
        description=(
            "Expert NYC mortgage discrimination analyst. "
            "Queries live CFPB HMDA data and returns narrative analysis + map data."
        ),
    )


# Module-level singleton (imported by dispatch_agent and main.py)
hmda_analyst = create_hmda_analyst()
