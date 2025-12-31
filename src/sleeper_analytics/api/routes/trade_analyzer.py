"""
Comprehensive Trade Analysis API Routes

Endpoints for analyzing trades with roster needs and value.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Path

from sleeper_analytics.api.dependencies import LeagueContextDep, NFLStatsDep, SleeperClientDep
from sleeper_analytics.models.trade_analyzer import (
    ComprehensiveTradeAnalysis,
    RosterNeedsAnalysis,
)
from sleeper_analytics.services.trade_analyzer import TradeAnalyzerService

router = APIRouter()


@router.get(
    "/{league_id}/roster-needs/{roster_id}",
    response_model=RosterNeedsAnalysis,
    summary="Get roster needs analysis",
    description="Analyze a team's roster depth, position needs, and trade priorities.",
)
async def get_roster_needs(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
) -> RosterNeedsAnalysis:
    """Get comprehensive roster needs analysis."""
    service = TradeAnalyzerService(client, ctx, nfl_stats)
    return await service.analyze_roster_needs(roster_id)


@router.post(
    "/{league_id}/analyze",
    response_model=ComprehensiveTradeAnalysis,
    summary="Analyze trade comprehensively",
    description="Analyze a trade from both value and roster fit perspectives.",
)
async def analyze_trade_comprehensive(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    team_a_roster_id: Annotated[int, Body(description="Team A roster ID")],
    team_a_gives: Annotated[list[str], Body(description="Player IDs Team A gives away")],
    team_b_roster_id: Annotated[int, Body(description="Team B roster ID")],
    team_b_gives: Annotated[list[str], Body(description="Player IDs Team B gives away")],
) -> ComprehensiveTradeAnalysis:
    """Analyze trade with value and roster fit."""
    service = TradeAnalyzerService(client, ctx, nfl_stats)
    return await service.analyze_comprehensive_trade(
        team_a_roster_id,
        team_a_gives,
        team_b_roster_id,
        team_b_gives,
    )
