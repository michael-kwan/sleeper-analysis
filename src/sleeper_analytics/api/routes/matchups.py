"""
Matchup API Routes

Endpoints for matchup analysis, team performance, and head-to-head records.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from sleeper_analytics.api.dependencies import (
    LeagueContextDep,
    SleeperClientDep,
    WeeksQuery,
)
from sleeper_analytics.models import Matchup, Standing, TeamPerformance
from sleeper_analytics.services.matchups import MatchupService

router = APIRouter()


@router.get(
    "/{league_id}/week/{week}",
    response_model=list[dict[str, Any]],
    summary="Get weekly matchups",
    description="Get all matchups for a specific week with scores.",
)
async def get_weekly_matchups(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    week: Annotated[int, Path(description="Week number", ge=1, le=18)],
) -> list[dict[str, Any]]:
    """Get matchups for a specific week."""
    service = MatchupService(client, ctx)
    matchups = await service.get_weekly_matchups(week)

    result = []
    for m in matchups:
        winner = m.winner
        result.append({
            "week": m.week,
            "matchup_id": m.matchup_id,
            "team1": {
                "name": m.team1.team_name,
                "roster_id": m.team1.roster_id,
                "points": m.team1.points,
            },
            "team2": {
                "name": m.team2.team_name,
                "roster_id": m.team2.roster_id,
                "points": m.team2.points,
            },
            "margin": round(m.margin, 2),
            "winner": winner.team_name if winner else "Tie",
        })

    return result


@router.get(
    "/{league_id}/season",
    response_model=dict[int, list[dict[str, Any]]],
    summary="Get season matchups",
    description="Get all matchups for the entire season.",
)
async def get_season_matchups(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> dict[int, list[dict[str, Any]]]:
    """Get all matchups for the season."""
    service = MatchupService(client, ctx)
    matchups_by_week = await service.get_season_matchups(1, weeks)

    result = {}
    for week, matchups in matchups_by_week.items():
        week_results = []
        for m in matchups:
            winner = m.winner
            week_results.append({
                "matchup_id": m.matchup_id,
                "team1": m.team1.team_name,
                "team1_points": m.team1.points,
                "team2": m.team2.team_name,
                "team2_points": m.team2.points,
                "winner": winner.team_name if winner else "Tie",
            })
        result[week] = week_results

    return result


@router.get(
    "/{league_id}/team/{roster_id}",
    response_model=TeamPerformance,
    summary="Get team performance",
    description="Get detailed performance metrics for a specific team.",
)
async def get_team_performance(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 17,
) -> TeamPerformance:
    """Get performance metrics for a team."""
    service = MatchupService(client, ctx)
    return await service.get_team_performance(roster_id, weeks)


@router.get(
    "/{league_id}/close-games",
    response_model=list[dict[str, Any]],
    summary="Get close games",
    description="Find all games decided by a small margin.",
)
async def get_close_games(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    threshold: Annotated[
        float, Query(description="Maximum point margin for close game")
    ] = 10.0,
    weeks: WeeksQuery = 17,
) -> list[dict[str, Any]]:
    """Get close games within the threshold."""
    service = MatchupService(client, ctx)
    return await service.get_close_games(threshold, weeks)


@router.get(
    "/{league_id}/team/{roster_id}/best-worst",
    response_model=dict[str, Any],
    summary="Get best/worst weeks",
    description="Find a team's best and worst scoring weeks.",
)
async def get_best_worst_weeks(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 17,
) -> dict[str, Any]:
    """Get best and worst weeks for a team."""
    service = MatchupService(client, ctx)
    result = await service.get_best_worst_weeks(roster_id, weeks)

    return {
        "team": ctx.get_team_name(roster_id),
        "best_week": result["best_week"].model_dump() if result["best_week"] else None,
        "worst_week": result["worst_week"].model_dump() if result["worst_week"] else None,
    }


@router.get(
    "/{league_id}/head-to-head/{roster_id_1}/{roster_id_2}",
    response_model=dict[str, Any],
    summary="Get head-to-head record",
    description="Get head-to-head record between two teams.",
)
async def get_head_to_head(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id_1: Annotated[int, Path(description="First team roster ID")],
    roster_id_2: Annotated[int, Path(description="Second team roster ID")],
    weeks: WeeksQuery = 17,
) -> dict[str, Any]:
    """Get head-to-head record between two teams."""
    service = MatchupService(client, ctx)
    return await service.get_head_to_head(roster_id_1, roster_id_2, weeks)


@router.get(
    "/{league_id}/standings",
    response_model=list[Standing],
    summary="Get standings",
    description="Get league standings with detailed stats.",
)
async def get_standings(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> list[Standing]:
    """Get league standings."""
    service = MatchupService(client, ctx)
    return await service.get_league_standings(weeks)
