"""
FastMCP server exposing CFPB HMDA API tools.
Uses v2 Data Browser API — county-level data for NYC boroughs.
Run standalone: uv run python -m mcp_server.main
"""

import json
import asyncio
from typing import Optional
from fastmcp import FastMCP
from .hmda_tools import (
    get_borough_denial_rate,
    get_all_boroughs_denial_rates,
    get_borough_race_breakdown,
    get_nyc_citywide_summary,
    NYC_ZIPS,
    NEIGHBORHOOD_BOROUGH,
    BOROUGH_FIPS,
    ALL_NYC_ZIPS,
    _resolve_borough,
)

mcp = FastMCP(
    "hmda-nyc-server",
    instructions=(
        "Tools to query CFPB HMDA mortgage discrimination data for NYC. "
        "Data is from the CFPB Data Browser API v2, county level (boroughs). "
        "Use these tools to analyze mortgage approval/denial patterns by race and location."
    ),
)


@mcp.tool()
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
        JSON with denial rate, application counts, and zip codes in that borough
    """
    result = await get_borough_denial_rate(borough_or_neighborhood, year, race)
    return json.dumps(result, indent=2)


@mcp.tool()
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
        JSON with per-borough denial rates and zip-code-level map data
    """
    result = await get_all_boroughs_denial_rates(year, race)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_race_disparity_analysis(
    borough_or_neighborhood: str,
    year: int = 2022,
) -> str:
    """
    Get mortgage denial rates broken down by every race group for a borough.
    Reveals racial disparity in lending — key for bias analysis.

    Args:
        borough_or_neighborhood: Borough or neighborhood name
        year: HMDA data year (default 2022)

    Returns:
        JSON with denial rates for Asian, Black, Hispanic, White, Native American, Pacific Islander
    """
    result = await get_borough_race_breakdown(borough_or_neighborhood, year)
    return json.dumps(result, indent=2)


@mcp.tool()
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
        JSON with citywide denial rate and per-borough breakdown
    """
    result = await get_nyc_citywide_summary(year, race)
    return json.dumps(result, indent=2)


@mcp.tool()
async def identify_borough_from_location(location: str) -> str:
    """
    Identify which NYC borough a location or neighborhood belongs to.

    Args:
        location: Neighborhood, area, or borough name (e.g. 'Jackson Heights', 'Harlem')

    Returns:
        JSON with resolved borough and FIPS code
    """
    resolved = _resolve_borough(location)
    if resolved:
        return json.dumps({
            "input": location,
            "borough": resolved,
            "county_fips": BOROUGH_FIPS[resolved],
            "zip_codes_count": len(NYC_ZIPS[resolved]),
        })
    return json.dumps({
        "input": location,
        "borough": None,
        "message": "Could not identify borough. Try: Manhattan, Brooklyn, Queens, Bronx, Staten Island",
    })


if __name__ == "__main__":
    mcp.run()
