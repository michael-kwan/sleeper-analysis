"""
Roster Construction Analysis API Routes

Endpoints for analyzing where teams' points came from (draft, trades, waivers, FA).
"""

from typing import Annotated

from fastapi import APIRouter, Path

from sleeper_analytics.api.dependencies import LeagueContextDep, SleeperClientDep, WeeksQuery
from sleeper_analytics.models.roster_construction import (
    LeagueRosterConstructionReport,
    TeamRosterConstruction,
)
from sleeper_analytics.services.roster_construction import RosterConstructionService

router = APIRouter()


@router.get(
    "/{league_id}/team/{roster_id}",
    response_model=TeamRosterConstruction,
    summary="Get team roster construction analysis",
    description="Analyze where a team's points came from (draft, trades, waivers, FA).",
)
async def get_team_roster_construction(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 17,
) -> TeamRosterConstruction:
    """Get roster construction analysis for a specific team."""
    service = RosterConstructionService(client, ctx)
    return await service.analyze_team_roster_construction(roster_id, weeks)


@router.get(
    "/{league_id}/league",
    response_model=LeagueRosterConstructionReport,
    summary="Get league-wide roster construction report",
    description="Analyze roster construction for all teams in the league.",
)
async def get_league_roster_construction_report(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> LeagueRosterConstructionReport:
    """Get league-wide roster construction analysis."""
    service = RosterConstructionService(client, ctx)
    return await service.get_league_roster_construction_report(weeks)
