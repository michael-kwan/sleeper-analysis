"""
Transaction API Routes

Endpoints for viewing and analyzing transactions (trades, waivers, FA).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from sleeper_analytics.api.dependencies import (
    LeagueContextDep,
    NFLStatsDep,
    SleeperClientDep,
    WeeksQuery,
)
from sleeper_analytics.models import Transaction, TransactionSummary, TransactionType
from sleeper_analytics.services.trades import TransactionService

router = APIRouter()


@router.get(
    "/{league_id}",
    response_model=list[dict[str, Any]],
    summary="Get all transactions",
    description="Get all transactions for a league with player names resolved.",
)
async def get_all_transactions(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> list[dict[str, Any]]:
    """Get all transactions for the league."""
    service = TransactionService(client, ctx, nfl_stats)
    transactions = await service.get_all_transactions(weeks)

    # Format for response with player names
    result = []
    for txn in transactions:
        adds = {}
        if txn.adds:
            for player_id, roster_id in txn.adds.items():
                adds[ctx.get_player_name(player_id)] = ctx.get_team_name(roster_id)

        drops = {}
        if txn.drops:
            for player_id, roster_id in txn.drops.items():
                drops[ctx.get_player_name(player_id)] = ctx.get_team_name(roster_id)

        result.append({
            "transaction_id": txn.transaction_id,
            "type": txn.type.value,
            "week": txn.week,
            "teams": [ctx.get_team_name(r) for r in txn.roster_ids],
            "adds": adds,
            "drops": drops,
            "draft_picks": [
                {
                    "round": p.round,
                    "season": p.season,
                    "from": ctx.get_team_name(p.previous_owner_id) if p.previous_owner_id else None,
                    "to": ctx.get_team_name(p.owner_id),
                }
                for p in txn.draft_picks
            ],
        })

    return result


@router.get(
    "/{league_id}/summary",
    response_model=TransactionSummary,
    summary="Get transaction summary",
    description="Get aggregated statistics about league transactions.",
)
async def get_transaction_summary(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> TransactionSummary:
    """Get transaction summary statistics."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_transaction_summary(weeks)


@router.get(
    "/{league_id}/by-type/{txn_type}",
    response_model=list[dict[str, Any]],
    summary="Get transactions by type",
    description="Filter transactions by type (trade, waiver, free_agent).",
)
async def get_transactions_by_type(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    txn_type: Annotated[
        str,
        Path(description="Transaction type: trade, waiver, or free_agent"),
    ],
    weeks: WeeksQuery = 18,
) -> list[dict[str, Any]]:
    """Get transactions filtered by type."""
    # Validate type
    try:
        transaction_type = TransactionType(txn_type)
    except ValueError:
        return []

    service = TransactionService(client, ctx, nfl_stats)
    transactions = await service.get_transactions_by_type(transaction_type, weeks)

    result = []
    for txn in transactions:
        adds = {}
        if txn.adds:
            for player_id, roster_id in txn.adds.items():
                adds[ctx.get_player_name(player_id)] = ctx.get_team_name(roster_id)

        result.append({
            "transaction_id": txn.transaction_id,
            "week": txn.week,
            "teams": [ctx.get_team_name(r) for r in txn.roster_ids],
            "adds": adds,
        })

    return result


@router.get(
    "/{league_id}/by-team/{roster_id}",
    response_model=list[dict[str, Any]],
    summary="Get team transactions",
    description="Get all transactions for a specific team.",
)
async def get_team_transactions(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    roster_id: Annotated[int, Path(description="Team roster ID")],
    weeks: WeeksQuery = 18,
) -> list[dict[str, Any]]:
    """Get transactions for a specific team."""
    service = TransactionService(client, ctx, nfl_stats)
    transactions = await service.get_team_transactions(roster_id, weeks)

    result = []
    for txn in transactions:
        adds = {}
        if txn.adds:
            for player_id, rid in txn.adds.items():
                adds[ctx.get_player_name(player_id)] = ctx.get_team_name(rid)

        drops = {}
        if txn.drops:
            for player_id, rid in txn.drops.items():
                drops[ctx.get_player_name(player_id)] = ctx.get_team_name(rid)

        result.append({
            "transaction_id": txn.transaction_id,
            "type": txn.type.value,
            "week": txn.week,
            "adds": adds,
            "drops": drops,
        })

    return result


@router.get(
    "/{league_id}/activity",
    response_model=list[dict[str, Any]],
    summary="Get team activity ranking",
    description="Rank teams by transaction activity.",
)
async def get_team_activity(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
) -> list[dict[str, Any]]:
    """Get teams ranked by transaction activity."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_most_active_teams(weeks)


@router.get(
    "/{league_id}/most-transacted",
    response_model=list[dict[str, Any]],
    summary="Get most transacted players",
    description="Get players with the most adds/drops/trades.",
)
async def get_most_transacted_players(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    weeks: WeeksQuery = 18,
    limit: Annotated[int, Query(description="Number of players to return")] = 20,
) -> list[dict[str, Any]]:
    """Get most transacted players."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_most_transacted_players(weeks, limit)


@router.get(
    "/{league_id}/player-tree/{player_id}",
    response_model=dict[str, Any],
    summary="Get player trade tree",
    description="Track a player's complete ownership history through the league.",
)
async def get_player_trade_tree(
    ctx: LeagueContextDep,
    client: SleeperClientDep,
    nfl_stats: NFLStatsDep,
    player_id: Annotated[str, Path(description="Player ID")],
    weeks: WeeksQuery = 18,
) -> dict[str, Any]:
    """Get player's complete trade/ownership tree."""
    service = TransactionService(client, ctx, nfl_stats)
    return await service.get_player_trade_tree(player_id, weeks)
