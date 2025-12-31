"""
Trade API Routes

Endpoints for trade analysis and value calculations.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from sleeper_analytics.api.dependencies import (
    LeagueContextDep,
    NFLStatsDep,
    SleeperClientDep,
    WeeksQuery,
)
from sleeper_analytics.models import TradeAnalysis
from sleeper_analytics.models.lopsided_trades import LopsidedTradesReport
from sleeper_analytics.services.trades import TransactionService

router = APIRouter()


@router.get(
    "/{league_id}/analyze",
    response_model=list[TradeAnalysis],
    summary="Analyze all trades",
    description="Analyze all trades with value calculations and fairness ratings.",
)
async def analyze_trades(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> list[TradeAnalysis]:
    """Analyze all trades in the league."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.analyze_trades(weeks)


@router.get(
    "/{league_id}/timeline",
    response_model=list[dict[str, Any]],
    summary="Get trade timeline",
    description="Get trades over time with value differences.",
)
async def get_trade_timeline(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> list[dict[str, Any]]:
    """Get trade timeline."""
    service = TransactionService(client, ctx, nfl_stats)
    analyses = await service.analyze_trades(weeks)

    timeline = []
    for analysis in analyses:
        teams = [s.team_name for s in analysis.sides]
        timeline.append({
            "week": analysis.week,
            "teams": teams,
            "value_difference": analysis.value_difference,
            "fairness": analysis.fairness.value,
            "winner": analysis.winner,
        })

    return sorted(timeline, key=lambda x: x["week"])


@router.get(
    "/{league_id}/winners-losers",
    response_model=dict[str, list[dict[str, Any]]],
    summary="Get trade winners and losers",
    description="Identify teams that have won or lost the most value in trades.",
)
async def get_trade_winners_losers(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> dict[str, list[dict[str, Any]]]:
    """Get trade winners and losers."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_trade_winners_losers(weeks)


@router.get(
    "/{league_id}/waivers",
    response_model=list[dict[str, Any]],
    summary="Get best waiver pickups",
    description="Rank waiver pickups by player value.",
)
async def get_waiver_analysis(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
    top_n: Annotated[
        int, Query(description="Number of results", ge=1, le=50)
    ] = 20,
) -> list[dict[str, Any]]:
    """Get best waiver pickups."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_waiver_analysis(weeks, top_n)


@router.post(
    "/{league_id}/evaluate",
    response_model=dict[str, Any],
    summary="Evaluate hypothetical trade",
    description="Evaluate a proposed trade between two teams.",
)
async def evaluate_trade(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    trade_proposal: Annotated[
        dict[str, Any],
        Body(
            description="Trade proposal with team_a and team_b details",
            examples=[
                {
                    "team_a_roster_id": 1,
                    "team_a_player_ids": ["4046", "6786"],
                    "team_a_picks": [],
                    "team_b_roster_id": 2,
                    "team_b_player_ids": ["4034"],
                    "team_b_picks": [[1, 6]],
                }
            ],
        ),
    ],
) -> dict[str, Any]:
    """Evaluate a hypothetical trade."""
    service = TransactionService(client, ctx, nfl_stats)

    return await service.evaluate_hypothetical_trade(
        team_a_roster_id=trade_proposal["team_a_roster_id"],
        team_a_player_ids=trade_proposal.get("team_a_player_ids", []),
        team_a_picks=[tuple(p) for p in trade_proposal.get("team_a_picks", [])],
        team_b_roster_id=trade_proposal["team_b_roster_id"],
        team_b_player_ids=trade_proposal.get("team_b_player_ids", []),
        team_b_picks=[tuple(p) for p in trade_proposal.get("team_b_picks", [])],
    )


@router.get(
    "/{league_id}/summary",
    response_model=dict[str, Any],
    summary="Get trade summary",
    description="Get summary statistics about trades in the league.",
)
async def get_trade_summary(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> dict[str, Any]:
    """Get trade summary statistics."""
    service = TransactionService(client, ctx, nfl_stats)
    analyses = await service.analyze_trades(weeks)

    if not analyses:
        return {
            "total_trades": 0,
            "message": "No trades found",
        }

    fairness_counts: dict[str, int] = {}
    total_value_moved = 0.0

    for a in analyses:
        f = a.fairness.value
        fairness_counts[f] = fairness_counts.get(f, 0) + 1
        total_value_moved += sum(s.total_value for s in a.sides)

    winners_losers = await service.get_trade_winners_losers(weeks)

    return {
        "league": ctx.league_name,
        "total_trades": len(analyses),
        "fairness_breakdown": fairness_counts,
        "total_value_moved": round(total_value_moved, 1),
        "avg_value_difference": round(
            sum(a.value_difference for a in analyses) / len(analyses), 1
        ),
        "biggest_winner": winners_losers["winners"][0] if winners_losers["winners"] else None,
        "biggest_loser": winners_losers["losers"][-1] if winners_losers["losers"] else None,
    }


@router.get(
    "/{league_id}/lopsided",
    response_model=LopsidedTradesReport,
    summary="Get lopsided trades analysis",
    description="Identify the most one-sided trades based on post-trade point performance.",
)
async def get_lopsided_trades(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> LopsidedTradesReport:
    """Analyze trades to find the most lopsided based on results."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_lopsided_trades_report(weeks)
