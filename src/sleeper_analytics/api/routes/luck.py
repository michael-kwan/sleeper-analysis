"""
Luck Analysis API Routes

Endpoints for analyzing matchup luck and strength of schedule.
"""

from typing import Annotated

from fastapi import APIRouter, Path

from sleeper_analytics.api.dependencies import LeagueContextDep, SleeperClientDep, WeeksQuery
from sleeper_analytics.models.luck import LeagueLuckReport, LuckReport, WeeklyLuckAnalysis
from sleeper_analytics.services.luck_analysis import LuckAnalysisService

router = APIRouter()


@router.get(
    "/{league_id}/weekly/{week}",
    response_model=list[WeeklyLuckAnalysis],
    summary="Get weekly luck analysis",
    description="Analyze luck for all teams in a specific week.",
)
async def get_weekly_luck(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    week: Annotated[int, Path(description="Week number", ge=1, le=18)],
) -> list[WeeklyLuckAnalysis]:
    """Get luck analysis for all teams in a specific week."""
    service = LuckAnalysisService(client, ctx)
    return await service.analyze_weekly_luck(week)


@router.get(
    "/{league_id}/team/{roster_id}",
    response_model=LuckReport,
    summary="Get team luck report",
    description="Get comprehensive luck analysis for a specific team including strength of schedule.",
)
async def get_team_luck_report(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 17,
) -> LuckReport:
    """Get luck report for a specific team."""
    service = LuckAnalysisService(client, ctx)
    return await service.get_luck_report(roster_id, weeks)


@router.get(
    "/{league_id}/league",
    response_model=LeagueLuckReport,
    summary="Get league luck report",
    description="Get league-wide luck analysis with luckiest/unluckiest teams and SOS rankings.",
)
async def get_league_luck_report(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> LeagueLuckReport:
    """Get league-wide luck analysis."""
    service = LuckAnalysisService(client, ctx)
    return await service.get_league_luck_report(weeks)
