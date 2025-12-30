"""
League API Routes

Endpoints for league information, rosters, and standings.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from sleeper_analytics.api.dependencies import (
    LeagueContextDep,
    SleeperClientDep,
    WeeksQuery,
)
from sleeper_analytics.models import League, Roster, Standing, User
from sleeper_analytics.services.matchups import MatchupService

router = APIRouter()


@router.get(
    "/user/{username}",
    response_model=list[League],
    summary="Get user's leagues",
    description="Get all leagues for a user in a given season.",
)
async def get_user_leagues(
    username: Annotated[str, Path(description="Sleeper username")],
    client: SleeperClientDep,
    season: Annotated[
        int, Query(description="NFL season year", ge=2020, le=2030)
    ] = 2024,
) -> list[League]:
    """Get all leagues for a user."""
    user = await client.get_user(username)
    if not user:
        return []

    leagues = await client.get_user_leagues(user.user_id, season)
    return leagues


@router.get(
    "/{league_id}",
    response_model=League,
    summary="Get league details",
    description="Get detailed information about a specific league.",
)
async def get_league(
    ctx: LeagueContextDep,
) -> League:
    """Get league information."""
    return ctx.league


@router.get(
    "/{league_id}/users",
    response_model=list[User],
    summary="Get league users",
    description="Get all users/managers in a league.",
)
async def get_league_users(
    ctx: LeagueContextDep,
) -> list[User]:
    """Get all users in the league."""
    return ctx.users


@router.get(
    "/{league_id}/rosters",
    response_model=list[Roster],
    summary="Get league rosters",
    description="Get all rosters in a league with player lists.",
)
async def get_league_rosters(
    ctx: LeagueContextDep,
) -> list[Roster]:
    """Get all rosters in the league."""
    return ctx.rosters


@router.get(
    "/{league_id}/rosters/{roster_id}",
    response_model=dict[str, Any],
    summary="Get roster details",
    description="Get detailed roster information including player names.",
)
async def get_roster_details(
    ctx: LeagueContextDep,
    roster_id: Annotated[int, Path(description="Roster ID")],
) -> dict[str, Any]:
    """Get detailed roster information."""
    roster = ctx.get_roster(roster_id)
    if not roster:
        return {"error": f"Roster {roster_id} not found"}

    # Enrich player data with names and positions
    players_detail = []
    for player_id in roster.players:
        player = ctx.get_player(player_id)
        if player:
            players_detail.append({
                "player_id": player_id,
                "name": player.display_name,
                "position": player.position,
                "team": player.team,
                "is_starter": player_id in roster.starters,
            })

    return {
        "roster_id": roster.roster_id,
        "team_name": ctx.get_team_name(roster_id),
        "owner": ctx.get_user_display_name(roster_id),
        "record": f"{roster.wins}-{roster.losses}-{roster.ties}",
        "points_for": roster.fpts,
        "points_against": roster.fpts_against,
        "players": players_detail,
        "starters": roster.starters,
    }


@router.get(
    "/{league_id}/standings",
    response_model=list[Standing],
    summary="Get league standings",
    description="Get current league standings with win/loss records and points.",
)
async def get_standings(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> list[Standing]:
    """Get league standings."""
    matchup_service = MatchupService(client, ctx)
    standings = await matchup_service.get_league_standings(weeks)
    return standings


@router.get(
    "/{league_id}/teams",
    response_model=list[dict[str, Any]],
    summary="Get team summary",
    description="Get a summary of all teams with key stats.",
)
async def get_teams_summary(
    ctx: LeagueContextDep,
) -> list[dict[str, Any]]:
    """Get summary of all teams."""
    teams = []
    for roster in ctx.rosters:
        teams.append({
            "roster_id": roster.roster_id,
            "team_name": ctx.get_team_name(roster.roster_id),
            "owner": ctx.get_user_display_name(roster.roster_id),
            "record": f"{roster.wins}-{roster.losses}-{roster.ties}",
            "points_for": roster.fpts,
            "points_against": roster.fpts_against,
            "roster_size": len(roster.players),
        })

    # Sort by wins, then points
    teams.sort(key=lambda x: (
        int(x["record"].split("-")[0]),
        x["points_for"]
    ), reverse=True)

    return teams


@router.get(
    "/{league_id}/settings",
    response_model=dict[str, Any],
    summary="Get league settings",
    description="Get league settings including scoring and roster configuration.",
)
async def get_league_settings(
    ctx: LeagueContextDep,
) -> dict[str, Any]:
    """Get league settings."""
    league = ctx.league

    return {
        "league_id": league.league_id,
        "name": league.name,
        "season": league.season,
        "status": league.status,
        "total_rosters": league.total_rosters,
        "roster_positions": league.roster_positions,
        "scoring_settings": league.scoring_settings,
        "is_ppr": league.is_ppr,
        "is_superflex": league.is_superflex,
        "settings": league.settings,
    }
