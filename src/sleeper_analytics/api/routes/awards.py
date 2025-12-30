"""
Awards API Routes

Endpoints for weekly high/low scorer tracking and payouts.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from sleeper_analytics.api.dependencies import LeagueContextDep, SleeperClientDep, WeeksQuery
from sleeper_analytics.models.awards import SeasonAwardsReport, WeeklyAward
from sleeper_analytics.services.matchups import MatchupService

router = APIRouter()


@router.get(
    "/{league_id}/weekly/{week}",
    response_model=WeeklyAward,
    summary="Get weekly high/low scorers",
    description="Get the highest and lowest scorer for a specific week.",
)
async def get_weekly_awards(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    week: Annotated[int, Path(description="Week number", ge=1, le=18)],
) -> WeeklyAward:
    """Get weekly high and low scorer."""
    matchup_service = MatchupService(client, ctx)
    return await matchup_service.get_weekly_high_low(week)


@router.get(
    "/{league_id}/season",
    response_model=SeasonAwardsReport,
    summary="Get season awards summary",
    description="Get all weekly awards with payout calculations for the entire season.",
)
async def get_season_awards(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> SeasonAwardsReport:
    """Get season-long awards summary with $5/week payout tracking."""
    matchup_service = MatchupService(client, ctx)
    return await matchup_service.get_season_awards(weeks)
