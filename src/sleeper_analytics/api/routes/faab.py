"""
FAAB Analysis API Routes

Endpoints for analyzing FAAB spending and player lifecycle.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from sleeper_analytics.api.dependencies import LeagueContextDep, SleeperClientDep, WeeksQuery
from sleeper_analytics.models.faab import (
    LeagueFAABReport,
    OwnerFAABPerformance,
    PlayerLifecycle,
)
from sleeper_analytics.services.faab import FAABService

router = APIRouter()


@router.get(
    "/{league_id}/player/{player_id}/lifecycle",
    response_model=PlayerLifecycle,
    summary="Get player lifecycle",
    description="Track a player's complete journey through the league with all ownership periods and FAAB spent.",
)
async def get_player_lifecycle(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    player_id: Annotated[str, Path(description="Sleeper player ID")],
    weeks: WeeksQuery = 17,
) -> PlayerLifecycle:
    """Get complete player lifecycle through the league."""
    service = FAABService(client, ctx)
    return await service.get_player_lifecycle(player_id, weeks)


@router.get(
    "/{league_id}/owner/{roster_id}",
    response_model=OwnerFAABPerformance,
    summary="Get owner FAAB performance",
    description="Analyze FAAB efficiency for a specific owner with ROI calculations.",
)
async def get_owner_faab_performance(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Owner roster ID")],
    weeks: WeeksQuery = 17,
) -> OwnerFAABPerformance:
    """Get FAAB performance analysis for an owner."""
    service = FAABService(client, ctx)
    return await service.get_owner_faab_performance(roster_id, weeks)


@router.get(
    "/{league_id}/report",
    response_model=LeagueFAABReport,
    summary="Get league FAAB report",
    description="Get league-wide FAAB analysis with efficiency rankings and best/worst pickups.",
)
async def get_league_faab_report(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> LeagueFAABReport:
    """Get comprehensive league-wide FAAB analysis."""
    service = FAABService(client, ctx)
    return await service.get_league_faab_report(weeks)
