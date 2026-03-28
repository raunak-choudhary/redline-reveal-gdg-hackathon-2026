"""
HMDA API tools — uses CFPB Data Browser API v2.
Endpoint: https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations
- Race filters use `races` param (not Hispanic)
- Hispanic uses `ethnicities` param
- Data is county-level; NYC boroughs = counties
"""

import httpx
import asyncio
from typing import Optional

HMDA_V2_BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations"

# NYC Borough → 5-digit FIPS county code
BOROUGH_FIPS = {
    "Bronx": "36005",
    "Brooklyn": "36047",
    "Manhattan": "36061",
    "Queens": "36081",
    "Staten Island": "36085",
}

FIPS_BOROUGH = {v: k for k, v in BOROUGH_FIPS.items()}
NYC_FIPS_LIST = ",".join(BOROUGH_FIPS.values())

# Valid races for the `races` API parameter
RACE_OPTIONS = {
    "Asian": "Asian",
    "Black": "Black or African American",
    "White": "White",
    "Native American": "American Indian or Alaska Native",
    "Pacific Islander": "Native Hawaiian or Other Pacific Islander",
    "Two or More": "2 or more minority races",
    "Joint": "Joint",
}

# Hispanic is handled via `ethnicities` param
ETHNICITY_OPTIONS = {
    "Hispanic": "Hispanic or Latino",
    "Latino": "Hispanic or Latino",
    "Non-Hispanic": "Not Hispanic or Latino",
}

# Zip codes by borough (used for choropleth map — borough rate applied to all its zips)
NYC_ZIPS = {
    "Manhattan": [
        "10001","10002","10003","10004","10005","10006","10007","10009","10010",
        "10011","10012","10013","10014","10016","10017","10018","10019","10020",
        "10021","10022","10023","10024","10025","10026","10027","10028","10029",
        "10030","10031","10032","10033","10034","10035","10036","10037","10038",
        "10039","10040","10044","10065","10069","10075","10128",
    ],
    "Brooklyn": [
        "11201","11203","11204","11205","11206","11207","11208","11209","11210",
        "11211","11212","11213","11214","11215","11216","11217","11218","11219",
        "11220","11221","11222","11223","11224","11225","11226","11228","11229",
        "11230","11231","11232","11233","11234","11235","11236","11237","11238",
        "11239","11249",
    ],
    "Queens": [
        "11101","11102","11103","11104","11105","11106","11354","11355","11356",
        "11357","11358","11359","11360","11361","11362","11363","11364","11365",
        "11366","11367","11368","11369","11370","11372","11373","11374","11375",
        "11377","11378","11379","11385","11411","11412","11413","11414","11415",
        "11416","11417","11418","11419","11420","11421","11422","11423","11426",
        "11427","11428","11429","11432","11433","11434","11435","11436",
    ],
    "Bronx": [
        "10451","10452","10453","10454","10455","10456","10457","10458","10459",
        "10460","10461","10462","10463","10464","10465","10466","10467","10468",
        "10469","10470","10471","10472","10473","10474","10475",
    ],
    "Staten Island": [
        "10301","10302","10303","10304","10305","10306","10307","10308","10309",
        "10310","10311","10312","10314",
    ],
}

ALL_NYC_ZIPS = [z for zips in NYC_ZIPS.values() for z in zips]

# Neighborhood → borough for natural language resolution
NEIGHBORHOOD_BOROUGH = {
    "jackson heights": "Queens",
    "astoria": "Queens",
    "flushing": "Queens",
    "jamaica": "Queens",
    "elmhurst": "Queens",
    "corona": "Queens",
    "forest hills": "Queens",
    "rego park": "Queens",
    "woodside": "Queens",
    "sunnyside": "Queens",
    "long island city": "Queens",
    "harlem": "Manhattan",
    "east harlem": "Manhattan",
    "washington heights": "Manhattan",
    "upper west side": "Manhattan",
    "upper east side": "Manhattan",
    "chelsea": "Manhattan",
    "hell's kitchen": "Manhattan",
    "financial district": "Manhattan",
    "tribeca": "Manhattan",
    "soho": "Manhattan",
    "east village": "Manhattan",
    "lower east side": "Manhattan",
    "chinatown": "Manhattan",
    "inwood": "Manhattan",
    "bed stuy": "Brooklyn",
    "bedford stuyvesant": "Brooklyn",
    "crown heights": "Brooklyn",
    "brownsville": "Brooklyn",
    "east new york": "Brooklyn",
    "flatbush": "Brooklyn",
    "williamsburg": "Brooklyn",
    "bushwick": "Brooklyn",
    "sunset park": "Brooklyn",
    "bay ridge": "Brooklyn",
    "greenpoint": "Brooklyn",
    "park slope": "Brooklyn",
    "prospect heights": "Brooklyn",
    "borough park": "Brooklyn",
    "bensonhurst": "Brooklyn",
    "coney island": "Brooklyn",
    "brighton beach": "Brooklyn",
    "south bronx": "Bronx",
    "mott haven": "Bronx",
    "hunts point": "Bronx",
    "tremont": "Bronx",
    "morrisania": "Bronx",
    "fordham": "Bronx",
    "norwood": "Bronx",
    "pelham bay": "Bronx",
    "riverdale": "Bronx",
    "staten island": "Staten Island",
}


def _resolve_borough(name: str) -> Optional[str]:
    """Fuzzy-match a borough or neighborhood name."""
    name_lower = name.lower().strip()
    for borough in BOROUGH_FIPS:
        if name_lower in borough.lower() or borough.lower() in name_lower:
            return borough
    for neighborhood, borough in NEIGHBORHOOD_BOROUGH.items():
        if name_lower in neighborhood or neighborhood in name_lower:
            return borough
    return None


def _resolve_filter(group: str) -> dict:
    """
    Parse a demographic filter string like 'Hispanic', 'Black', 'Asian'.
    Returns dict with either {'races': '...'} or {'ethnicities': '...'} or {}.
    """
    if not group:
        return {}
    g_lower = group.lower()
    for label, val in ETHNICITY_OPTIONS.items():
        if g_lower in label.lower() or label.lower() in g_lower:
            return {"ethnicities": val}
    for label, val in RACE_OPTIONS.items():
        if g_lower in label.lower() or label.lower() in g_lower:
            return {"races": val}
    return {}


def _sum_count(data: dict) -> int:
    try:
        agg_list = data.get("aggregations", [])
        if isinstance(agg_list, list):
            return sum(int(item.get("count", 0)) for item in agg_list)
        return 0
    except Exception:
        return 0


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


async def _fetch(counties: str, year: int, action: str, extra: dict = None) -> int:
    """Single HMDA v2 API call; returns application count."""
    params = {
        "counties": counties,
        "years": str(year),
        "actions_taken": action,
    }
    if extra:
        params.update(extra)
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        try:
            r = await client.get(HMDA_V2_BASE, params=params)
            if r.status_code == 200:
                return _sum_count(r.json())
        except Exception:
            pass
    return 0


async def get_borough_denial_rate(
    borough: str,
    year: int = 2022,
    demographic: Optional[str] = None,
) -> dict:
    """Get mortgage originated vs denied + denial rate for one NYC borough."""
    resolved = _resolve_borough(borough)
    if not resolved:
        return {"error": f"Could not identify borough for: '{borough}'"}

    fips = BOROUGH_FIPS[resolved]
    demo_filter = _resolve_filter(demographic) if demographic else {}

    originated, denied = await asyncio.gather(
        _fetch(fips, year, "1", demo_filter),
        _fetch(fips, year, "3", demo_filter),
    )

    total = originated + denied
    denial_rate = round(denied / total * 100, 1) if total > 0 else None

    return {
        "borough": resolved,
        "county_fips": fips,
        "year": year,
        "demographic_filter": demographic,
        "originated": originated,
        "denied": denied,
        "total": total,
        "denial_rate_pct": denial_rate,
        "zip_codes": NYC_ZIPS[resolved],
    }


async def get_all_boroughs_denial_rates(
    year: int = 2022,
    demographic: Optional[str] = None,
) -> dict:
    """Get denial rates for all 5 NYC boroughs. Returns zip_map for choropleth."""
    demo_filter = _resolve_filter(demographic) if demographic else {}

    async def fetch_borough(borough: str, fips: str):
        originated, denied = await asyncio.gather(
            _fetch(fips, year, "1", demo_filter),
            _fetch(fips, year, "3", demo_filter),
        )
        total = originated + denied
        rate = round(denied / total * 100, 1) if total > 0 else None
        return borough, {"originated": originated, "denied": denied, "total": total, "denial_rate_pct": rate}

    results = await asyncio.gather(*[fetch_borough(b, f) for b, f in BOROUGH_FIPS.items()])
    borough_data = dict(results)

    # Build zip-code-level map: each zip gets its borough's rate
    zip_map = {}
    for borough, stats in borough_data.items():
        for zip_code in NYC_ZIPS.get(borough, []):
            zip_map[zip_code] = {
                "borough": borough,
                "denial_rate_pct": stats["denial_rate_pct"],
                "originated": stats["originated"],
                "denied": stats["denied"],
                "total": stats["total"],
            }

    return {
        "year": year,
        "demographic_filter": demographic,
        "borough_data": borough_data,
        "zip_map": zip_map,
    }


async def get_borough_race_breakdown(
    borough: str,
    year: int = 2022,
) -> dict:
    """Denial rates broken down by race AND ethnicity for a borough."""
    resolved = _resolve_borough(borough)
    if not resolved:
        return {"error": f"Could not identify borough: '{borough}'"}

    fips = BOROUGH_FIPS[resolved]

    # Build list of (label, filter_dict)
    filters = [(label, {"races": val}) for label, val in RACE_OPTIONS.items() if label not in ("Joint",)]
    filters += [("Hispanic/Latino", {"ethnicities": "Hispanic or Latino"})]

    async def fetch_group(label: str, filt: dict):
        originated, denied = await asyncio.gather(
            _fetch(fips, year, "1", filt),
            _fetch(fips, year, "3", filt),
        )
        total = originated + denied
        rate = round(denied / total * 100, 1) if total > 0 else None
        return label, {"originated": originated, "denied": denied, "total": total, "denial_rate_pct": rate}

    results = await asyncio.gather(*[fetch_group(l, f) for l, f in filters])

    return {
        "borough": resolved,
        "year": year,
        "race_breakdown": dict(results),
    }


async def get_nyc_citywide_summary(
    year: int = 2022,
    demographic: Optional[str] = None,
) -> dict:
    """Overall NYC summary: citywide rate + per-borough breakdown."""
    data = await get_all_boroughs_denial_rates(year, demographic)
    total_orig = sum(b["originated"] for b in data["borough_data"].values())
    total_denied = sum(b["denied"] for b in data["borough_data"].values())
    total = total_orig + total_denied
    citywide_rate = round(total_denied / total * 100, 1) if total > 0 else None

    return {
        "year": year,
        "demographic_filter": demographic,
        "citywide_denial_rate_pct": citywide_rate,
        "total_applications": total,
        "borough_summaries": data["borough_data"],
    }
