"""
MCP tool wrappers — plain async functions registered as ADK FunctionTools.
HMDAAnalystAgent uses these to query CFPB HMDA data.
"""

import json
from typing import Optional
from google.adk.tools import FunctionTool

from ..mcp_server.hmda_tools import (
    get_borough_denial_rate,
    get_all_boroughs_denial_rates,
    get_borough_race_breakdown,
    get_nyc_citywide_summary,
)


async def get_borough_mortgage_stats(
    borough_or_neighborhood: str,
    year: int = 2022,
    race: Optional[str] = None,
) -> str:
    """
    Get mortgage originated vs denied counts and denial rate for a NYC borough or neighborhood.

    Args:
        borough_or_neighborhood: Borough name (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
                                 OR neighborhood (e.g. Jackson Heights, Harlem, Bed Stuy)
        year: HMDA data year (default 2022, range 2018-2022)
        race: Optional race filter — Asian, Black, Hispanic, White, Native American, Pacific Islander

    Returns:
        JSON string with denial rate and application counts
    """
    result = await get_borough_denial_rate(borough_or_neighborhood, year, race)
    return json.dumps(result, indent=2)


async def get_all_nyc_boroughs_data(
    year: int = 2022,
    race: Optional[str] = None,
) -> str:
    """
    Get mortgage denial rates for ALL 5 NYC boroughs simultaneously.
    Also returns zip_map for choropleth visualization.

    Args:
        year: HMDA data year (default 2022)
        race: Optional race filter — Asian, Black, Hispanic, White, Native American, Pacific Islander

    Returns:
        JSON string with per-borough denial rates and zip-code-level map data
    """
    result = await get_all_boroughs_denial_rates(year, race)
    return json.dumps(result, indent=2)


async def get_race_disparity_analysis(
    borough_or_neighborhood: str,
    year: int = 2022,
) -> str:
    """
    Get mortgage denial rates broken down by every race group for a borough.
    Reveals racial disparity in mortgage lending patterns.

    Args:
        borough_or_neighborhood: Borough or neighborhood name
        year: HMDA data year (default 2022)

    Returns:
        JSON string with denial rates for Asian, Black, Hispanic, White, Native American, Pacific Islander
    """
    result = await get_borough_race_breakdown(borough_or_neighborhood, year)
    return json.dumps(result, indent=2)


async def get_nyc_mortgage_summary(
    year: int = 2022,
    race: Optional[str] = None,
) -> str:
    """
    Get a citywide NYC mortgage lending summary across all boroughs.

    Args:
        year: HMDA data year (default 2022)
        race: Optional race filter — Asian, Black, Hispanic, White, Native American, Pacific Islander

    Returns:
        JSON string with citywide denial rate and per-borough breakdown
    """
    result = await get_nyc_citywide_summary(year, race)
    return json.dumps(result, indent=2)


def get_hmda_tools() -> list:
    """Return list of ADK FunctionTool objects for HMDA data access."""
    return [
        FunctionTool(get_borough_mortgage_stats),
        FunctionTool(get_all_nyc_boroughs_data),
        FunctionTool(get_race_disparity_analysis),
        FunctionTool(get_nyc_mortgage_summary),
    ]
