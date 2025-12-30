"""
Benchwarmer API Routes

Endpoints for analyzing bench performance and identifying benching mistakes.
"""

from typing import Annotated

from fastapi import APIRouter, Path

from sleeper_analytics.api.dependencies import LeagueContextDep, SleeperClientDep, WeeksQuery
from sleeper_analytics.models.benchwarmer import (
    BenchwarmerReport,
    LeagueBenchwarmerReport,
)
from sleeper_analytics.services.benchwarmer import BenchwarmerService

router = APIRouter()


@router.get(
    "/{league_id}/team/{roster_id}",
    response_model=BenchwarmerReport,
    summary="Get team benchwarmer report",
    description="Analyze bench performance for a specific team, identifying high-scoring benched players.",
)
async def get_team_benchwarmer_report(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 17,
) -> BenchwarmerReport:
    """Get benchwarmer analysis for a specific team."""
    service = BenchwarmerService(client, ctx)
    return await service.analyze_team_bench(roster_id, weeks)


@router.get(
    "/{league_id}/league",
    response_model=LeagueBenchwarmerReport,
    summary="Get league benchwarmer report",
    description="Get league-wide benchwarmer analysis with biggest benching mistakes.",
)
async def get_league_benchwarmer_report(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> LeagueBenchwarmerReport:
    """Get league-wide benchwarmer analysis."""
    service = BenchwarmerService(client, ctx)
    return await service.get_league_benchwarmer_report(weeks)
