"""
LenderInvestigatorAgent — investigative journalism agent.
Identifies which specific banks/lenders show the worst racial bias
in NYC mortgage lending using HMDA data + BigQuery caching.
"""

import logging
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from mcp_server.lender_tools import get_lender_bias_ranking, get_top_lenders

logger = logging.getLogger(__name__)

LENDER_INSTRUCTION = """
You are an investigative journalist specializing in financial discrimination.
Your job is to identify WHICH SPECIFIC BANKS are discriminating against minority
mortgage applicants in NYC using real federal HMDA 2022 data.

WHEN CALLED:
1. Use get_lender_bias_ranking() with the borough and race from the user's query
2. Return a sharp, journalistic narrative naming the specific banks and their disparity ratios
3. Always cite exact numbers

RESPONSE FORMAT (for voice — keep under 40 seconds):
- Name the worst offender first, then rank the others
- Use disparity ratio as the headline number
- End with a systemic observation

EXAMPLE RESPONSE:
"In Brooklyn, JPMorgan Chase denied Black applicants at 21 percent — nearly 1.6 times
the rate for White applicants. Wells Fargo was worse at 2.1 times. Bank of America showed
the highest disparity at 2.4 times. These are not small community banks — these are
America's largest financial institutions, with federal data proving a pattern of
systematic discrimination."

IMPORTANT:
- Always call get_lender_bias_ranking — never invent numbers
- If a borough is not specified, default to Brooklyn
- If a race is not specified, default to Black
- Keep narrative to 3-4 sentences maximum for voice delivery
- The lender_rankings list in the tool response has: institution_name, denial_rate_pct,
  white_denial_rate_pct, disparity_ratio — use all of these
"""


async def _get_lender_bias_ranking(borough: str, race: str = "Black", year: int = 2022) -> dict:
    """
    Rank top mortgage lenders in a NYC borough by racial disparity ratio.

    Args:
        borough: NYC borough name (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
        race: Demographic group to analyze (Black, Asian, Hispanic, White)
        year: Data year (default 2022)

    Returns:
        Dict with lender_rankings list, each containing institution_name,
        denial_rate_pct, white_denial_rate_pct, and disparity_ratio
    """
    return await get_lender_bias_ranking(borough, race, year)


async def _get_top_lenders(borough: str, year: int = 2022) -> list:
    """
    Get the top mortgage lenders by application volume in a NYC borough.

    Args:
        borough: NYC borough name
        year: Data year (default 2022)

    Returns:
        List of lenders with name, lei, and application count
    """
    return await get_top_lenders(borough, year, limit=10)


lender_investigator = LlmAgent(
    name="LenderInvestigatorAgent",
    model="gemini-2.5-flash",
    instruction=LENDER_INSTRUCTION,
    tools=[
        FunctionTool(_get_lender_bias_ranking),
        FunctionTool(_get_top_lenders),
    ],
    description="Identifies which specific banks show racial bias in NYC mortgage lending using HMDA data",
)
