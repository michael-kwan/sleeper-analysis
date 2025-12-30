"""
Visualization API Routes

Endpoints for generating interactive Plotly charts and dashboards.
All endpoints return HTML content for embedding or viewing directly.
"""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from sleeper_analytics.api.dependencies import (
    LeagueContextDep,
    NFLStatsDep,
    SleeperClientDep,
)
from sleeper_analytics.services.efficiency import EfficiencyService
from sleeper_analytics.services.matchups import MatchupService
from sleeper_analytics.services.nfl_stats import NFLStatsService
from sleeper_analytics.services.trades import TransactionService
from sleeper_analytics.visualization import charts


router = APIRouter()


@router.get(
    "/{league_id}/standings",
    response_class=HTMLResponse,
    summary="Standings chart",
    description="Generate an interactive bar chart showing league standings.",
)
async def get_standings_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 17,
) -> HTMLResponse:
    """Generate a standings bar chart."""
    matchup_service = MatchupService(client, ctx)
    standings = await matchup_service.get_league_standings(weeks)

    html = charts.standings_chart(
        standings, title=f"{ctx.league.name} - Standings (Week {weeks})"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/weekly-scores",
    response_class=HTMLResponse,
    summary="Weekly scores chart",
    description="Generate a line chart showing weekly scoring trends for all teams.",
)
async def get_weekly_scores_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 17,
) -> HTMLResponse:
    """Generate a weekly scores line chart."""
    matchup_service = MatchupService(client, ctx)

    performances = []
    for roster in ctx.rosters:
        perf = await matchup_service.get_team_performance(roster.roster_id, weeks)
        performances.append(perf)

    html = charts.weekly_scores_chart(
        performances, title=f"{ctx.league.name} - Weekly Scores"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/efficiency",
    response_class=HTMLResponse,
    summary="Efficiency chart",
    description="Generate a chart showing roster efficiency rankings.",
)
async def get_efficiency_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 17,
) -> HTMLResponse:
    """Generate an efficiency rankings chart."""
    efficiency_service = EfficiencyService(client, ctx)
    rankings = await efficiency_service.get_league_efficiency_rankings(weeks)

    html = charts.efficiency_chart(
        rankings, title=f"{ctx.league.name} - Roster Efficiency"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/trade-summary",
    response_class=HTMLResponse,
    summary="Trade analysis chart",
    description="Generate a chart showing trade fairness and value differences.",
)
async def get_trade_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    nfl_stats: NFLStatsDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 18,
) -> HTMLResponse:
    """Generate a trade analysis chart."""
    txn_service = TransactionService(client, ctx, nfl_stats)
    analyses = await txn_service.analyze_trades(weeks)

    html = charts.trade_analysis_chart(
        analyses, title=f"{ctx.league.name} - Trade Analysis"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/distribution",
    response_class=HTMLResponse,
    summary="Points distribution chart",
    description="Generate a box plot showing points distribution for each team.",
)
async def get_distribution_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 17,
) -> HTMLResponse:
    """Generate a points distribution box plot."""
    matchup_service = MatchupService(client, ctx)

    performances = []
    for roster in ctx.rosters:
        perf = await matchup_service.get_team_performance(roster.roster_id, weeks)
        performances.append(perf)

    html = charts.points_distribution_chart(
        performances, title=f"{ctx.league.name} - Points Distribution"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/head-to-head",
    response_class=HTMLResponse,
    summary="Head-to-head heatmap",
    description="Generate a heatmap showing head-to-head records between teams.",
)
async def get_head_to_head_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 17,
) -> HTMLResponse:
    """Generate a head-to-head heatmap."""
    matchup_service = MatchupService(client, ctx)

    h2h_matrix: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"wins": 0, "losses": 0})
    )

    for i, roster1 in enumerate(ctx.rosters):
        for roster2 in ctx.rosters[i + 1 :]:
            h2h = await matchup_service.get_head_to_head(
                roster1.roster_id, roster2.roster_id, weeks
            )

            team1 = h2h["team1"]
            team2 = h2h["team2"]

            h2h_matrix[team1][team2] = {
                "wins": h2h["team1_wins"],
                "losses": h2h["team2_wins"],
            }
            h2h_matrix[team2][team1] = {
                "wins": h2h["team2_wins"],
                "losses": h2h["team1_wins"],
            }

    html = charts.head_to_head_heatmap(
        dict(h2h_matrix), title=f"{ctx.league.name} - Head-to-Head"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/transactions",
    response_class=HTMLResponse,
    summary="Transaction activity chart",
    description="Generate charts showing transaction activity over time.",
)
async def get_transactions_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    nfl_stats: NFLStatsDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 18,
) -> HTMLResponse:
    """Generate a transaction activity chart."""
    txn_service = TransactionService(client, ctx, nfl_stats)
    summary = await txn_service.get_transaction_summary(weeks)

    html = charts.transaction_activity_chart(
        summary, title=f"{ctx.league.name} - Transaction Activity"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/team-activity",
    response_class=HTMLResponse,
    summary="Team transaction activity chart",
    description="Generate a stacked bar chart showing transactions by team.",
)
async def get_team_activity_chart(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    nfl_stats: NFLStatsDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 18,
) -> HTMLResponse:
    """Generate a team transaction activity chart."""
    txn_service = TransactionService(client, ctx, nfl_stats)
    summary = await txn_service.get_transaction_summary(weeks)

    html = charts.team_activity_chart(
        summary, title=f"{ctx.league.name} - Team Activity"
    )
    return HTMLResponse(content=html)


@router.get(
    "/{league_id}/dashboard",
    response_class=HTMLResponse,
    summary="Full dashboard",
    description="Generate a complete dashboard with all charts.",
)
async def get_dashboard(
    league_id: str,
    client: SleeperClientDep,
    ctx: LeagueContextDep,
    nfl_stats: NFLStatsDep,
    weeks: Annotated[int, Query(ge=1, le=18)] = 17,
) -> HTMLResponse:
    """Generate a full dashboard with all analytics charts."""
    matchup_service = MatchupService(client, ctx)
    efficiency_service = EfficiencyService(client, ctx)
    txn_service = TransactionService(client, ctx, nfl_stats)

    standings = await matchup_service.get_league_standings(weeks)
    standings_html = charts.standings_chart(standings)

    performances = []
    for roster in ctx.rosters:
        perf = await matchup_service.get_team_performance(roster.roster_id, weeks)
        performances.append(perf)

    weekly_scores_html = charts.weekly_scores_chart(performances)
    distribution_html = charts.points_distribution_chart(performances)

    efficiency_rankings = await efficiency_service.get_league_efficiency_rankings(weeks)
    efficiency_html = charts.efficiency_chart(efficiency_rankings)

    trades = await txn_service.analyze_trades(weeks + 1)
    trades_html = charts.trade_analysis_chart(trades)

    txn_summary = await txn_service.get_transaction_summary(weeks + 1)
    transactions_html = charts.transaction_activity_chart(txn_summary)

    season = ctx.league.season if ctx.league.season else 2024

    html = charts.generate_dashboard(
        standings_html=standings_html,
        weekly_scores_html=weekly_scores_html,
        efficiency_html=efficiency_html,
        trades_html=trades_html,
        distribution_html=distribution_html,
        transactions_html=transactions_html,
        league_name=ctx.league.name,
        season=int(season) if isinstance(season, str) else season,
    )

    return HTMLResponse(content=html)
