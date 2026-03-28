"""
Lender Investigation Tools
Identifies which specific banks/lenders show racial bias in NYC mortgage lending.
Uses CFPB HMDA API for lender data + BigQuery for caching results.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from google.cloud import bigquery

logger = logging.getLogger(__name__)

HMDA_V2_BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations"
HMDA_FILERS_BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view/filers"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

BOROUGH_FIPS = {
    "Bronx": "36005",
    "Brooklyn": "36047",
    "Manhattan": "36061",
    "Queens": "36081",
    "Staten Island": "36085",
}

RACE_API_MAP = {
    "Black": "Black or African American",
    "Asian": "Asian",
    "White": "White",
    "Hispanic": None,  # handled via ethnicities
    "Native American": "American Indian or Alaska Native",
}

BQ_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "redline-reveal")
BQ_DATASET = "hmda_analysis"
BQ_TABLE = "lender_rankings"


def _bq_client():
    return bigquery.Client(project=BQ_PROJECT)


async def _fetch_count(counties: str, year: int, action: str, extra: dict) -> int:
    params = {"counties": counties, "years": str(year), "actions_taken": action}
    params.update(extra)
    async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
        try:
            r = await client.get(HMDA_V2_BASE, params=params)
            if r.status_code == 200:
                return sum(int(x.get("count", 0)) for x in r.json().get("aggregations", []))
        except Exception as e:
            logger.warning("HMDA fetch error: %s", e)
    return 0


async def get_top_lenders(borough: str, year: int = 2022, limit: int = 15) -> list[dict]:
    """Get top mortgage lenders in a borough by application volume."""
    fips = BOROUGH_FIPS.get(borough)
    if not fips:
        return []
    async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
        try:
            r = await client.get(HMDA_FILERS_BASE, params={"counties": fips, "years": str(year)})
            if r.status_code == 200:
                institutions = r.json().get("institutions", [])
                # Sort by application count, take top N
                institutions.sort(key=lambda x: x.get("count", 0), reverse=True)
                return institutions[:limit]
        except Exception as e:
            logger.warning("Filers API error: %s", e)
    return []


async def get_lender_denial_stats(lei: str, fips: str, year: int, race: str) -> tuple[int, int]:
    """Get (denied, originated) for a lender + race in a county."""
    if race == "Hispanic":
        extra = {"leis": lei, "ethnicities": "Hispanic or Latino"}
    else:
        api_race = RACE_API_MAP.get(race, race)
        extra = {"leis": lei, "races": api_race}

    denied, originated = await asyncio.gather(
        _fetch_count(fips, year, "3", extra),
        _fetch_count(fips, year, "1", extra),
    )
    return denied, originated


async def get_lender_bias_ranking(
    borough: str,
    race: str = "Black",
    year: int = 2022,
    top_n: int = 5,
) -> dict:
    """
    Rank top lenders in a borough by racial disparity ratio.
    Returns top_n worst offenders with their bias scores.
    """
    # Check BigQuery cache first
    cached = _get_cached_ranking(borough, race, year)
    if cached:
        logger.info("Returning cached lender ranking for %s/%s", borough, race)
        return cached

    fips = BOROUGH_FIPS.get(borough)
    if not fips:
        return {"error": f"Unknown borough: {borough}"}

    # Get top lenders by volume
    top_lenders = await get_top_lenders(borough, year, limit=12)
    if not top_lenders:
        return {"error": "Could not retrieve lender list"}

    logger.info("Analyzing %d lenders in %s for %s bias", len(top_lenders), borough, race)

    # For each lender, fetch race + white denial stats in parallel
    async def analyze_lender(inst: dict) -> Optional[dict]:
        lei = inst["lei"]
        name = inst["name"]
        try:
            (denied_race, orig_race), (denied_white, orig_white) = await asyncio.gather(
                get_lender_denial_stats(lei, fips, year, race),
                get_lender_denial_stats(lei, fips, year, "White"),
            )
            total_race = denied_race + orig_race
            total_white = denied_white + orig_white

            if total_race < 10:  # skip lenders with too few applications
                return None

            rate_race = round(denied_race / total_race * 100, 1) if total_race > 0 else None
            rate_white = round(denied_white / total_white * 100, 1) if total_white > 0 else None
            ratio = round(rate_race / rate_white, 2) if (rate_white and rate_white > 0 and rate_race is not None) else None

            return {
                "lei": lei,
                "institution_name": name,
                "race": race,
                "denied": denied_race,
                "originated": orig_race,
                "total": total_race,
                "denial_rate_pct": rate_race,
                "white_denial_rate_pct": rate_white,
                "disparity_ratio": ratio,
                "year": year,
            }
        except Exception as e:
            logger.warning("Error analyzing lender %s: %s", name, e)
            return None

    results = await asyncio.gather(*[analyze_lender(inst) for inst in top_lenders])
    valid = [r for r in results if r and r.get("disparity_ratio") is not None]

    # Sort by disparity ratio descending
    valid.sort(key=lambda x: x["disparity_ratio"], reverse=True)
    top = valid[:top_n]

    result = {
        "borough": borough,
        "race": race,
        "year": year,
        "lender_rankings": top,
        "total_lenders_analyzed": len(valid),
    }

    # Cache to BigQuery
    _save_to_bigquery(borough, race, year, top)

    return result


def _get_cached_ranking(borough: str, race: str, year: int) -> Optional[dict]:
    """Check BigQuery for a recent cached result (within 24 hours)."""
    try:
        client = _bq_client()
        query = f"""
            SELECT *
            FROM `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`
            WHERE borough = @borough AND race = @race AND year = @year
              AND analysis_timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            ORDER BY disparity_ratio DESC
            LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("borough", "STRING", borough),
                bigquery.ScalarQueryParameter("race", "STRING", race),
                bigquery.ScalarQueryParameter("year", "INT64", year),
            ]
        )
        rows = list(client.query(query, job_config=job_config).result())
        if not rows:
            return None

        lender_rankings = [
            {
                "lei": r.lei,
                "institution_name": r.institution_name,
                "race": r.race,
                "denied": r.denied,
                "originated": r.originated,
                "total": r.total,
                "denial_rate_pct": r.denial_rate_pct,
                "white_denial_rate_pct": r.white_denial_rate_pct,
                "disparity_ratio": r.disparity_ratio,
                "year": r.year,
            }
            for r in rows
        ]
        return {
            "borough": borough,
            "race": race,
            "year": year,
            "lender_rankings": lender_rankings,
            "total_lenders_analyzed": len(lender_rankings),
            "source": "cache",
        }
    except Exception as e:
        logger.warning("BigQuery cache read error: %s", e)
        return None


def _save_to_bigquery(borough: str, race: str, year: int, rankings: list[dict]):
    """Save lender rankings to BigQuery for caching."""
    if not rankings:
        return
    try:
        client = _bq_client()
        table_ref = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
        now = datetime.now(timezone.utc).isoformat()

        rows = [
            {
                "borough": borough,
                "lei": r["lei"],
                "institution_name": r["institution_name"],
                "race": race,
                "denied": r.get("denied", 0),
                "originated": r.get("originated", 0),
                "total": r.get("total", 0),
                "denial_rate_pct": r.get("denial_rate_pct"),
                "white_denial_rate_pct": r.get("white_denial_rate_pct"),
                "disparity_ratio": r.get("disparity_ratio"),
                "year": year,
                "analysis_timestamp": now,
            }
            for r in rankings
        ]
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            logger.warning("BigQuery insert errors: %s", errors)
        else:
            logger.info("Saved %d lender rankings to BigQuery", len(rows))
    except Exception as e:
        logger.warning("BigQuery save error: %s", e)
