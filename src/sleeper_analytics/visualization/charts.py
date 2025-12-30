"""
Plotly Chart Generators

Generates interactive charts for fantasy football analytics.
All charts return HTML strings for embedding or standalone use.
"""

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sleeper_analytics.models.matchup import (
    EfficiencyReport,
    SeasonEfficiency,
    Standing,
    TeamPerformance,
)
from sleeper_analytics.models.transaction import TradeAnalysis, TransactionSummary


DARK_THEME = {
    "paper_bgcolor": "#1a1a2e",
    "plot_bgcolor": "#16213e",
    "font_color": "#e8e8e8",
    "gridcolor": "#2d3a4f",
    "colorway": [
        "#00d9ff",
        "#ff6b6b",
        "#4ecdc4",
        "#ffe66d",
        "#a855f7",
        "#f97316",
        "#10b981",
        "#ec4899",
        "#3b82f6",
        "#84cc16",
    ],
}


def _apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply dark theme styling to a figure."""
    fig.update_layout(
        paper_bgcolor=DARK_THEME["paper_bgcolor"],
        plot_bgcolor=DARK_THEME["plot_bgcolor"],
        font={"color": DARK_THEME["font_color"], "family": "Inter, sans-serif"},
        colorway=DARK_THEME["colorway"],
        margin={"l": 60, "r": 40, "t": 60, "b": 60},
    )
    fig.update_xaxes(
        gridcolor=DARK_THEME["gridcolor"],
        linecolor=DARK_THEME["gridcolor"],
    )
    fig.update_yaxes(
        gridcolor=DARK_THEME["gridcolor"],
        linecolor=DARK_THEME["gridcolor"],
    )
    return fig


def standings_chart(standings: list[Standing], title: str = "League Standings") -> str:
    """
    Create a horizontal bar chart showing league standings.

    Args:
        standings: List of Standing objects
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not standings:
        return "<div>No standings data available</div>"

    teams = [s.team_name for s in reversed(standings)]
    wins = [s.wins for s in reversed(standings)]
    losses = [s.losses for s in reversed(standings)]
    points = [s.points_for for s in reversed(standings)]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Win-Loss Record", "Total Points"),
        horizontal_spacing=0.15,
    )

    fig.add_trace(
        go.Bar(
            y=teams,
            x=wins,
            name="Wins",
            orientation="h",
            marker_color="#10b981",
            text=wins,
            textposition="inside",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            y=teams,
            x=losses,
            name="Losses",
            orientation="h",
            marker_color="#ef4444",
            text=losses,
            textposition="inside",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            y=teams,
            x=points,
            name="Points For",
            orientation="h",
            marker_color="#00d9ff",
            text=[f"{p:.1f}" for p in points],
            textposition="inside",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        barmode="group",
        height=max(400, len(standings) * 45),
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.5, "xanchor": "center"},
    )

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def weekly_scores_chart(
    performances: list[TeamPerformance],
    title: str = "Weekly Scoring Trends",
) -> str:
    """
    Create a line chart showing weekly scoring trends for all teams.

    Args:
        performances: List of TeamPerformance objects
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not performances:
        return "<div>No performance data available</div>"

    fig = go.Figure()

    for perf in performances:
        if perf.weekly_results:
            weeks = [r.week for r in perf.weekly_results]
            points = [r.points for r in perf.weekly_results]

            fig.add_trace(
                go.Scatter(
                    x=weeks,
                    y=points,
                    mode="lines+markers",
                    name=perf.team_name,
                    hovertemplate=(
                        f"<b>{perf.team_name}</b><br>"
                        "Week %{x}<br>"
                        "Points: %{y:.1f}<br>"
                        "<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        xaxis_title="Week",
        yaxis_title="Points",
        height=500,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.3, "x": 0.5, "xanchor": "center"},
        hovermode="x unified",
    )

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def efficiency_chart(
    rankings: list[dict[str, Any]],
    title: str = "Roster Efficiency Rankings",
) -> str:
    """
    Create a combined bar chart showing efficiency and points left on bench.

    Args:
        rankings: List of efficiency ranking dictionaries
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not rankings:
        return "<div>No efficiency data available</div>"

    teams = [r["team_name"] for r in rankings]
    efficiency = [r["efficiency_pct"] for r in rankings]
    bench_points = [r["points_left_on_bench"] for r in rankings]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Efficiency %", "Points Left on Bench"),
        horizontal_spacing=0.15,
    )

    colors = [
        "#10b981" if e >= 90 else "#ffe66d" if e >= 85 else "#ef4444"
        for e in efficiency
    ]

    fig.add_trace(
        go.Bar(
            x=teams,
            y=efficiency,
            name="Efficiency %",
            marker_color=colors,
            text=[f"{e:.1f}%" for e in efficiency],
            textposition="outside",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=teams,
            y=bench_points,
            name="Bench Points",
            marker_color="#ff6b6b",
            text=[f"{b:.1f}" for b in bench_points],
            textposition="outside",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=450,
        showlegend=False,
    )

    fig.update_xaxes(tickangle=45)

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def trade_analysis_chart(
    analyses: list[TradeAnalysis],
    title: str = "Trade Value Analysis",
) -> str:
    """
    Create a chart showing trade fairness distribution and value differences.

    Args:
        analyses: List of TradeAnalysis objects
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not analyses:
        return "<div>No trade data available</div>"

    fairness_counts = {"Fair": 0, "Slightly Uneven": 0, "Uneven": 0, "Lopsided": 0}
    for a in analyses:
        fairness_counts[a.fairness.value] = fairness_counts.get(a.fairness.value, 0) + 1

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Trade Fairness Distribution", "Value Difference by Trade"),
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        horizontal_spacing=0.1,
    )

    colors_pie = {
        "Fair": "#10b981",
        "Slightly Uneven": "#ffe66d",
        "Uneven": "#f97316",
        "Lopsided": "#ef4444",
    }

    fig.add_trace(
        go.Pie(
            labels=list(fairness_counts.keys()),
            values=list(fairness_counts.values()),
            marker_colors=[colors_pie.get(k, "#888") for k in fairness_counts.keys()],
            textinfo="label+percent",
            hole=0.4,
        ),
        row=1,
        col=1,
    )

    trade_labels = [f"Week {a.week}" for a in analyses]
    value_diffs = [a.value_difference for a in analyses]
    bar_colors = [colors_pie.get(a.fairness.value, "#888") for a in analyses]

    fig.add_trace(
        go.Bar(
            x=trade_labels,
            y=value_diffs,
            marker_color=bar_colors,
            text=[f"{v:.1f}" for v in value_diffs],
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Value Diff: %{y:.1f}<br>"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=450,
        showlegend=False,
    )

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def points_distribution_chart(
    performances: list[TeamPerformance],
    title: str = "Points Distribution",
) -> str:
    """
    Create a box plot showing points distribution for each team.

    Args:
        performances: List of TeamPerformance objects
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not performances:
        return "<div>No performance data available</div>"

    fig = go.Figure()

    sorted_perfs = sorted(performances, key=lambda x: x.avg_points, reverse=True)

    for perf in sorted_perfs:
        if perf.weekly_results:
            points = [r.points for r in perf.weekly_results]
            fig.add_trace(
                go.Box(
                    y=points,
                    name=perf.team_name,
                    boxpoints="all",
                    jitter=0.3,
                    pointpos=-1.8,
                    hovertemplate=(
                        f"<b>{perf.team_name}</b><br>"
                        "Points: %{y:.1f}<br>"
                        "<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        yaxis_title="Points",
        height=500,
        showlegend=False,
    )

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def head_to_head_heatmap(
    h2h_matrix: dict[str, dict[str, dict[str, int]]],
    title: str = "Head-to-Head Records",
) -> str:
    """
    Create a heatmap showing head-to-head win/loss records.

    Args:
        h2h_matrix: Nested dict {team1: {team2: {"wins": n, "losses": n}}}
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not h2h_matrix:
        return "<div>No head-to-head data available</div>"

    teams = list(h2h_matrix.keys())
    n = len(teams)

    z = []
    text = []
    for team1 in teams:
        row = []
        text_row = []
        for team2 in teams:
            if team1 == team2:
                row.append(0)
                text_row.append("-")
            else:
                record = h2h_matrix.get(team1, {}).get(team2, {"wins": 0, "losses": 0})
                wins = record.get("wins", 0)
                losses = record.get("losses", 0)
                row.append(wins - losses)
                text_row.append(f"{wins}-{losses}")
        z.append(row)
        text.append(text_row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=teams,
            y=teams,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 12},
            colorscale=[
                [0, "#ef4444"],
                [0.5, "#1a1a2e"],
                [1, "#10b981"],
            ],
            showscale=True,
            colorbar={"title": "Win Diff"},
            hovertemplate=(
                "<b>%{y} vs %{x}</b><br>"
                "Record: %{text}<br>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=max(400, n * 50),
        xaxis={"tickangle": 45},
    )

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def transaction_activity_chart(
    summary: TransactionSummary,
    title: str = "Transaction Activity",
) -> str:
    """
    Create charts showing transaction activity over time and by team.

    Args:
        summary: TransactionSummary object
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not summary.by_week and not summary.by_team:
        return "<div>No transaction data available</div>"

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Transactions by Week", "Transactions by Type"),
        specs=[[{"type": "scatter"}, {"type": "pie"}]],
        horizontal_spacing=0.15,
    )

    weeks = sorted(summary.by_week.keys())
    counts = [summary.by_week[w] for w in weeks]

    fig.add_trace(
        go.Scatter(
            x=weeks,
            y=counts,
            mode="lines+markers+text",
            text=counts,
            textposition="top center",
            line={"width": 3},
            marker={"size": 10},
            hovertemplate=(
                "Week %{x}<br>"
                "Transactions: %{y}<br>"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    type_colors = {
        "trade": "#a855f7",
        "waiver": "#00d9ff",
        "free_agent": "#10b981",
        "commissioner": "#ffe66d",
    }

    fig.add_trace(
        go.Pie(
            labels=list(summary.by_type.keys()),
            values=list(summary.by_type.values()),
            marker_colors=[type_colors.get(t, "#888") for t in summary.by_type.keys()],
            textinfo="label+percent",
            hole=0.4,
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=400,
        showlegend=False,
    )

    fig.update_xaxes(title_text="Week", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def team_activity_chart(
    summary: TransactionSummary,
    title: str = "Team Transaction Activity",
) -> str:
    """
    Create a stacked bar chart showing transaction activity by team.

    Args:
        summary: TransactionSummary object
        title: Chart title

    Returns:
        HTML string containing the chart
    """
    if not summary.by_team:
        return "<div>No transaction data available</div>"

    teams = list(summary.by_team.keys())
    totals = [(t, sum(summary.by_team[t].values())) for t in teams]
    teams = [t for t, _ in sorted(totals, key=lambda x: x[1], reverse=True)]

    txn_types = ["trade", "waiver", "free_agent"]
    type_colors = {
        "trade": "#a855f7",
        "waiver": "#00d9ff",
        "free_agent": "#10b981",
    }

    fig = go.Figure()

    for txn_type in txn_types:
        counts = [summary.by_team[t].get(txn_type, 0) for t in teams]
        fig.add_trace(
            go.Bar(
                x=teams,
                y=counts,
                name=txn_type.replace("_", " ").title(),
                marker_color=type_colors[txn_type],
            )
        )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        barmode="stack",
        height=450,
        xaxis={"tickangle": 45},
        yaxis_title="Transactions",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.5, "xanchor": "center"},
    )

    _apply_dark_theme(fig)
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def generate_dashboard(
    standings_html: str,
    weekly_scores_html: str,
    efficiency_html: str,
    trades_html: str,
    distribution_html: str,
    transactions_html: str,
    league_name: str = "Fantasy Football",
    season: int = 2024,
) -> str:
    """
    Generate a full dashboard HTML page with all charts.

    Args:
        standings_html: Standings chart HTML
        weekly_scores_html: Weekly scores chart HTML
        efficiency_html: Efficiency chart HTML
        trades_html: Trades chart HTML
        distribution_html: Points distribution chart HTML
        transactions_html: Transaction activity chart HTML
        league_name: League name for title
        season: Season year

    Returns:
        Complete HTML page as string
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{league_name} - {season} Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
            color: #e8e8e8;
            min-height: 100vh;
            padding: 20px;
        }}

        .header {{
            text-align: center;
            padding: 30px 20px;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }}

        .header h1 {{
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d9ff, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}

        .header p {{
            color: #a0a0a0;
            font-size: 1.1rem;
        }}

        .nav {{
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 30px;
        }}

        .nav a {{
            padding: 10px 20px;
            background: rgba(0, 217, 255, 0.1);
            border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 8px;
            color: #00d9ff;
            text-decoration: none;
            transition: all 0.3s ease;
        }}

        .nav a:hover {{
            background: rgba(0, 217, 255, 0.2);
            transform: translateY(-2px);
        }}

        .dashboard {{
            display: grid;
            gap: 30px;
            max-width: 1600px;
            margin: 0 auto;
        }}

        .chart-section {{
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .chart-section h2 {{
            font-size: 1.3rem;
            margin-bottom: 15px;
            color: #00d9ff;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .chart-section h2::before {{
            content: '';
            display: inline-block;
            width: 4px;
            height: 24px;
            background: linear-gradient(180deg, #00d9ff, #a855f7);
            border-radius: 2px;
        }}

        .row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }}

        .footer {{
            text-align: center;
            padding: 30px;
            margin-top: 40px;
            color: #666;
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .row {{
                grid-template-columns: 1fr;
            }}

            .header h1 {{
                font-size: 1.8rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{league_name}</h1>
        <p>{season} Season Analytics Dashboard</p>
    </div>

    <nav class="nav">
        <a href="#standings">Standings</a>
        <a href="#scores">Weekly Scores</a>
        <a href="#efficiency">Efficiency</a>
        <a href="#trades">Trades</a>
        <a href="#distribution">Distribution</a>
        <a href="#transactions">Transactions</a>
    </nav>

    <div class="dashboard">
        <section id="standings" class="chart-section">
            <h2>League Standings</h2>
            {standings_html}
        </section>

        <div class="row">
            <section id="scores" class="chart-section">
                <h2>Weekly Scoring Trends</h2>
                {weekly_scores_html}
            </section>

            <section id="distribution" class="chart-section">
                <h2>Points Distribution</h2>
                {distribution_html}
            </section>
        </div>

        <section id="efficiency" class="chart-section">
            <h2>Roster Efficiency</h2>
            {efficiency_html}
        </section>

        <div class="row">
            <section id="trades" class="chart-section">
                <h2>Trade Analysis</h2>
                {trades_html}
            </section>

            <section id="transactions" class="chart-section">
                <h2>Transaction Activity</h2>
                {transactions_html}
            </section>
        </div>
    </div>

    <footer class="footer">
        <p>Generated by Sleeper Analytics API • Data from Sleeper.app</p>
    </footer>
</body>
</html>"""
