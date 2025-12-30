"""
Efficiency API Routes

Endpoints for roster efficiency analysis.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Path

from sleeper_analytics.api.dependencies import (
    LeagueContextDep,
    SleeperClientDep,
    WeeksQuery,
)
from sleeper_analytics.models import EfficiencyReport, SeasonEfficiency
from sleeper_analytics.services.efficiency import EfficiencyService

router = APIRouter()


@router.get(
    "/{league_id}/rankings",
    response_model=list[dict[str, Any]],
    summary="Get efficiency rankings",
    description="Rank all teams by roster efficiency percentage.",
)
async def get_efficiency_rankings(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> list[dict[str, Any]]:
    """Get teams ranked by roster efficiency."""
    service = EfficiencyService(client, ctx)
    return await service.get_league_efficiency_rankings(weeks)


@router.get(
    "/{league_id}/team/{roster_id}",
    response_model=SeasonEfficiency,
    summary="Get team efficiency",
    description="Get season-long efficiency metrics for a team.",
)
async def get_team_efficiency(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 17,
) -> SeasonEfficiency:
    """Get efficiency metrics for a specific team."""
    service = EfficiencyService(client, ctx)
    return await service.get_season_efficiency(roster_id, weeks)


@router.get(
    "/{league_id}/team/{roster_id}/week/{week}",
    response_model=EfficiencyReport,
    summary="Get weekly efficiency",
    description="Get efficiency report for a team in a specific week.",
)
async def get_weekly_efficiency(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    week: Annotated[int, Path(description="Week number", ge=1, le=18)],
) -> EfficiencyReport:
    """Get weekly efficiency report for a team."""
    service = EfficiencyService(client, ctx)
    return await service.analyze_weekly_efficiency(roster_id, week)


@router.get(
    "/{league_id}/missed-starts",
    response_model=list[dict[str, Any]],
    summary="Get biggest missed starts",
    description="Find the biggest start/sit mistakes across the league.",
)
async def get_missed_starts(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
    top_n: Annotated[int, Path(description="Number of results")] = 10,
) -> list[dict[str, Any]]:
    """Get biggest missed start/sit decisions."""
    service = EfficiencyService(client, ctx)
    return await service.get_biggest_missed_starts(weeks, top_n)


@router.get(
    "/{league_id}/summary",
    response_model=dict[str, Any],
    summary="Get efficiency summary",
    description="Get league-wide efficiency summary.",
)
async def get_efficiency_summary(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    weeks: WeeksQuery = 17,
) -> dict[str, Any]:
    """Get league efficiency summary."""
    service = EfficiencyService(client, ctx)
    rankings = await service.get_league_efficiency_rankings(weeks)

    if not rankings:
        return {"error": "No data available"}

    efficiencies = [r["efficiency_pct"] for r in rankings]
    total_bench_pts = sum(r["points_left_on_bench"] for r in rankings)

    return {
        "league": ctx.league_name,
        "weeks_analyzed": weeks,
        "teams_count": len(rankings),
        "avg_efficiency": round(sum(efficiencies) / len(efficiencies), 1),
        "max_efficiency": max(efficiencies),
        "min_efficiency": min(efficiencies),
        "total_points_left_on_bench": round(total_bench_pts, 2),
        "most_efficient_team": rankings[0]["team_name"] if rankings else None,
        "least_efficient_team": rankings[-1]["team_name"] if rankings else None,
    }
