#!/usr/bin/env python3
"""
Generate static HTML reports for GitHub Pages.

This script:
1. Reads leagues.json
2. Fetches all analytics data for each league
3. Generates static HTML reports
4. Saves to docs/ folder for GitHub Pages
"""

import asyncio
import json
from pathlib import Path

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.services.benchwarmer import BenchwarmerService
from sleeper_analytics.services.draft import DraftAnalysisService
from sleeper_analytics.services.faab import FAABService
from sleeper_analytics.services.luck_analysis import LuckAnalysisService
from sleeper_analytics.services.matchups import MatchupService
from sleeper_analytics.services.nfl_stats import get_nfl_stats_service
from sleeper_analytics.services.roster_construction import RosterConstructionService
from sleeper_analytics.services.trades import TransactionService


async def generate_league_report(league_id: str, league_name: str, season: int):
    """Generate a comprehensive HTML report for a league."""
    print(f"\n{'='*60}")
    print(f"Generating report for: {league_name}")
    print(f"League ID: {league_id}")
    print(f"Season: {season}")
    print(f"{'='*60}\n")

    async with SleeperClient() as client:
        # Create league context
        print("📊 Creating league context...")
        ctx = await LeagueContext.create(client, league_id)
        print(f"   ✅ League: {ctx.league_name}")
        print(f"   ✅ Teams: {len(ctx.rosters)}")
        print(f"   ✅ Players cached: {len(ctx.players)}")

        # Determine current week (use 14 for now, can be dynamic)
        weeks = 14

        # Initialize services
        nfl_stats = get_nfl_stats_service(season)
        matchup_service = MatchupService(client, ctx)
        benchwarmer_service = BenchwarmerService(client, ctx)
        luck_service = LuckAnalysisService(client, ctx)
        faab_service = FAABService(client, ctx)
        roster_construction_service = RosterConstructionService(client, ctx)
        trades_service = TransactionService(client, ctx, nfl_stats)
        draft_service = DraftAnalysisService(client, ctx)

        # Fetch all data
        print(f"\n📈 Fetching analytics data (weeks 1-{weeks})...\n")

        print("   🏆 Fetching standings...")
        standings = await matchup_service.get_league_standings(weeks)

        print("   🎖️  Fetching awards (high/low scorers)...")
        awards = await matchup_service.get_season_awards(weeks)

        print("   💺 Fetching benchwarmer analysis...")
        benchwarmers = await benchwarmer_service.get_league_benchwarmer_report(weeks)

        print("   🍀 Fetching luck analysis...")
        luck = await luck_service.get_league_luck_report(weeks)

        print("   💰 Fetching FAAB analysis...")
        faab = await faab_service.get_league_faab_report(weeks)

        print("   📊 Fetching roster construction analysis...")
        roster_construction = await roster_construction_service.get_league_roster_construction_report(weeks)

        print("   🤝 Fetching trade analysis...")
        trades = await trades_service.get_lopsided_trades_report(weeks)

        print("   🎓 Fetching draft analysis...")
        draft = await draft_service.analyze_draft(weeks)

        print("   📋 Fetching transaction activity...")
        transactions = await client.get_all_transactions(ctx.league_id, weeks)

        # Generate HTML
        print("\n📝 Generating HTML report...")
        html = generate_html(ctx, standings, awards, benchwarmers, luck, faab, roster_construction, trades, draft, transactions, weeks)

        # Save to file
        output_dir = Path("docs")
        output_dir.mkdir(exist_ok=True)

        # Create sanitized filename
        filename = league_name.lower().replace(" ", "-").replace("'", "")
        output_path = output_dir / f"{filename}.html"

        output_path.write_text(html)
        print(f"   ✅ Saved to: {output_path}")

        return output_path


def generate_html(ctx, standings, awards, benchwarmers, luck, faab, roster_construction, trades, draft, transactions, weeks):
    """Generate HTML report with all analytics."""
    # Create summary stats
    total_teams = len(ctx.rosters)
    total_faab_spent = faab.total_faab_spent if faab else 0

    # Calculate transaction activity breakdown
    from collections import defaultdict
    transaction_counts = defaultdict(lambda: {'trades': 0, 'waivers': 0, 'free_agents': 0, 'total': 0})

    for txn in transactions:
        if txn.adds:
            for player_id, roster_id in txn.adds.items():
                if txn.type == 'trade':
                    transaction_counts[roster_id]['trades'] += 1
                    transaction_counts[roster_id]['total'] += 1
                elif txn.is_waiver:
                    transaction_counts[roster_id]['waivers'] += 1
                    transaction_counts[roster_id]['total'] += 1
                else:
                    transaction_counts[roster_id]['free_agents'] += 1
                    transaction_counts[roster_id]['total'] += 1

    # Generate charts
    roster_construction_chart = generate_roster_construction_chart(roster_construction)
    luck_chart = generate_luck_chart(luck)
    draft_chart = generate_draft_chart(draft)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ctx.league_name} - Analytics Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.3);
        }}

        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(to right, #fff, #e0e7ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            color: #e0e7ff;
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #60a5fa;
            margin-bottom: 5px;
        }}

        .stat-label {{
            color: #94a3b8;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .section {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
        }}

        .section h2 {{
            color: #60a5fa;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 2px solid rgba(96, 165, 250, 0.3);
            padding-bottom: 10px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}

        th {{
            background: rgba(96, 165, 250, 0.2);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #60a5fa;
            border-bottom: 2px solid rgba(96, 165, 250, 0.3);
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        tr:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}

        .highlight {{
            color: #34d399;
            font-weight: bold;
        }}

        .lowlight {{
            color: #f87171;
            font-weight: bold;
        }}

        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #64748b;
            font-size: 0.9em;
        }}

        .emoji {{
            font-size: 1.3em;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><span class="emoji">🏈</span>{ctx.league_name}</h1>
            <div class="subtitle">Analytics Report - Weeks 1-{weeks} | {len(ctx.rosters)} Teams</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_teams}</div>
                <div class="stat-label">Teams</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{weeks}</div>
                <div class="stat-label">Weeks Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${total_faab_spent}</div>
                <div class="stat-label">Total FAAB Spent</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(awards.weekly_awards)}</div>
                <div class="stat-label">Weeks with Data</div>
            </div>
        </div>

        <!-- Standings -->
        <div class="section">
            <h2><span class="emoji">🏆</span>Standings</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Record</th>
                        <th>Points For</th>
                        <th>Points Against</th>
                        <th>Avg Points</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{s.rank}</td>
                        <td><strong>{s.team_name}</strong></td>
                        <td>{s.wins}-{s.losses}-{s.ties}</td>
                        <td>{s.points_for}</td>
                        <td>{s.points_against}</td>
                        <td>{s.avg_points}</td>
                    </tr>
                    ''' for s in standings)}
                </tbody>
            </table>
        </div>

        <!-- Awards -->
        <div class="section">
            <h2><span class="emoji">🎖️</span>Weekly Awards ($5/week)</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value highlight">${awards.total_payout_high}</div>
                    <div class="stat-label">High Scorer Payouts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value lowlight">${awards.total_payout_low}</div>
                    <div class="stat-label">Low Scorer Fees</div>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Team</th>
                        <th>High Scores</th>
                        <th>Low Scores</th>
                        <th>Net Payout</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td><strong>{team}</strong></td>
                        <td class="highlight">{awards.high_score_leaders.get(team, 0)}</td>
                        <td class="lowlight">{awards.low_score_leaders.get(team, 0)}</td>
                        <td class="{'highlight' if awards.payout_by_team.get(team, 0) > 0 else 'lowlight'}">${awards.payout_by_team.get(team, 0):.0f}</td>
                    </tr>
                    ''' for team in sorted(set(list(awards.high_score_leaders.keys()) + list(awards.low_score_leaders.keys()))))}
                </tbody>
            </table>
        </div>

        <!-- Benchwarmers -->
        <div class="section">
            <h2><span class="emoji">💺</span>Benchwarmer Analysis</h2>
            <p><strong>Champion:</strong> <span class="highlight">{benchwarmers.benchwarmer_champion}</span> ({benchwarmers.benchwarmer_champion_points:.2f} total unoptimized points)</p>
            <p style="color: #94a3b8; font-size: 0.9em; margin-top: 10px;">
                <em>Note: "Total unoptimized points" = sum of all points left on bench when a better player could have started.
                This measures lineup optimization mistakes, not just bench production.</em>
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Total Unoptimized Points</th>
                        <th>Avg/Week</th>
                        <th>Worst Benching</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{idx + 1}</td>
                        <td><strong>{team.team_name}</strong></td>
                        <td class="lowlight">{team.total_bench_points:.2f}</td>
                        <td>{team.avg_bench_points_per_week:.2f}</td>
                        <td>{'N/A' if not team.worst_benching_decision else f'{team.worst_benching_decision.player_name} - Week {team.worst_benching_decision.week} ({team.worst_benching_decision.points:.2f} pts)'}</td>
                    </tr>
                    ''' for idx, team in enumerate(sorted(benchwarmers.all_teams, key=lambda x: x.total_bench_points, reverse=True)))}
                </tbody>
            </table>
        </div>

        <!-- Luck Analysis -->
        <div class="section">
            <h2><span class="emoji">🍀</span>Luck Analysis</h2>
            <p><strong>Luckiest:</strong> <span class="highlight">{luck.luckiest_team}</span> (+{luck.luckiest_score} wins)</p>
            <p><strong>Unluckiest:</strong> <span class="lowlight">{luck.unluckiest_team}</span> ({luck.unluckiest_score} wins)</p>
            <table>
                <thead>
                    <tr>
                        <th>Team</th>
                        <th>Actual Record</th>
                        <th>Expected Record</th>
                        <th>Luck Score</th>
                        <th>Lucky Wins</th>
                        <th>Unlucky Losses</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td><strong>{team.team_name}</strong></td>
                        <td>{team.actual_record}</td>
                        <td>{team.expected_record}</td>
                        <td class="{'highlight' if team.luck_score > 0 else 'lowlight' if team.luck_score < 0 else ''}">{team.luck_score:+.1f}</td>
                        <td>{len(team.lucky_wins)}</td>
                        <td>{len(team.unlucky_losses)}</td>
                    </tr>
                    ''' for team in sorted(luck.team_reports, key=lambda x: x.luck_score, reverse=True))}
                </tbody>
            </table>

            <div style="margin-top: 30px;">
                {luck_chart}
            </div>
        </div>

        <!-- Roster Construction -->
        <div class="section">
            <h2><span class="emoji">📊</span>Roster Construction</h2>
            <p><strong>Best Drafter:</strong> <span class="highlight">{roster_construction.best_drafter}</span> ({roster_construction.best_drafter_pct}% from draft)</p>
            <p><strong>Most Active Trader:</strong> <span class="highlight">{roster_construction.most_active_trader}</span> ({roster_construction.most_active_trader_count} trades)</p>
            <p><strong>Waiver Wire King:</strong> <span class="highlight">{roster_construction.waiver_wire_king}</span> ({roster_construction.waiver_wire_king_points} pts from waivers)</p>

            <div style="margin-top: 30px;">
                {roster_construction_chart}
            </div>

            <table style="margin-top: 30px;">
                <thead>
                    <tr>
                        <th>Team</th>
                        <th>Draft %</th>
                        <th>Trade %</th>
                        <th>Waiver %</th>
                        <th>FA %</th>
                        <th>Primary Source</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td><strong>{team.team_name}</strong></td>
                        <td>{team.breakdown.draft_percentage}%</td>
                        <td>{team.breakdown.trade_percentage}%</td>
                        <td>{team.breakdown.waiver_percentage}%</td>
                        <td>{team.breakdown.free_agent_percentage}%</td>
                        <td class="highlight">{team.primary_source.value.title()}</td>
                    </tr>
                    ''' for team in sorted(roster_construction.all_teams, key=lambda x: x.breakdown.draft_percentage, reverse=True))}
                </tbody>
            </table>
        </div>

        <!-- FAAB Analysis -->
        <div class="section">
            <h2><span class="emoji">💰</span>FAAB Efficiency</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>FAAB Spent</th>
                        <th>FAAB Remaining</th>
                        <th>Points Gained</th>
                        <th>Avg ROI</th>
                        <th>Best Pickup</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f'''
                    <tr>
                        <td>{team.faab_efficiency_rank}</td>
                        <td><strong>{team.owner_name}</strong></td>
                        <td>${team.total_faab_spent}</td>
                        <td>${team.faab_remaining}</td>
                        <td>{team.total_points_from_faab}</td>
                        <td class="highlight">{team.avg_roi:.2f}</td>
                        <td>{team.best_pickup.player_name if team.best_pickup else "N/A"} ({team.best_pickup.points_during_ownership if team.best_pickup else 0} pts)</td>
                    </tr>
                    ''' for team in faab.owner_rankings)}
                </tbody>
            </table>
        </div>

        <!-- Trade Analysis -->
        {'<div class="section">' + f'''
            <h2><span class="emoji">🤝</span>Trade Analysis</h2>
            <p><strong>Best Trader:</strong> <span class="highlight">{trades.best_overall_trader}</span> (Net: +{trades.best_overall_trader_net_points:.1f} pts)</p>
            <p><strong>Worst Trader:</strong> <span class="lowlight">{trades.worst_overall_trader}</span> (Net: {trades.worst_overall_trader_net_points:.1f} pts)</p>
            <p><strong>Biggest Trade Winner:</strong> {trades.biggest_trade_winner} (+{trades.biggest_trade_winner_differential:.1f} pts)</p>
            <p><strong>Biggest Trade Loser:</strong> {trades.biggest_trade_loser} (-{trades.biggest_trade_loser_differential:.1f} pts)</p>

            <table style="margin-top: 30px;">
                <thead>
                    <tr>
                        <th>Week</th>
                        <th>Winner (Players Received)</th>
                        <th>Loser (Players Received)</th>
                        <th>Point Differential</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{trade.week}</td>
                        <td>
                            <strong>{trade.winner}</strong><br>
                            <span style="color: #94a3b8; font-size: 0.85em;">
                                {'<br>'.join(f'{p.player_name} ({p.position}): {p.points_after_trade:.1f} pts' for p in (trade.team_a_players if trade.winner == trade.team_a else trade.team_b_players))}
                            </span>
                        </td>
                        <td>
                            <strong>{trade.loser}</strong><br>
                            <span style="color: #94a3b8; font-size: 0.85em;">
                                {'<br>'.join(f'{p.player_name} ({p.position}): {p.points_after_trade:.1f} pts' for p in (trade.team_b_players if trade.winner == trade.team_a else trade.team_a_players))}
                            </span>
                        </td>
                        <td class="highlight">+{trade.point_differential:.1f}</td>
                    </tr>
                    """ for trade in trades.most_lopsided_trades[:10])}
                </tbody>
            </table>
        ''' + '</div>' if trades.total_trades > 0 else ''}

        <!-- Draft Analysis -->
        <div class="section">
            <h2><span class="emoji">🎓</span>Draft Analysis</h2>
            <p><strong>Best Drafter:</strong> <span class="highlight">{draft.best_drafter}</span> ({draft.best_drafter_avg_ppick:.1f} pts/pick)</p>
            <p><strong>Worst Drafter:</strong> <span class="lowlight">{draft.worst_drafter}</span> ({draft.worst_drafter_avg_ppick:.1f} pts/pick)</p>
            <p><strong>League Average:</strong> {draft.league_avg_points_per_pick:.1f} pts/pick</p>

            <div style="margin-top: 30px;">
                {draft_chart}
            </div>

            <h3 style="margin-top: 40px; color: #10b981;">Top 5 Best Picks (vs Expected)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Pick #</th>
                        <th>Player</th>
                        <th>Team</th>
                        <th>Position</th>
                        <th>Points</th>
                        <th>PPG</th>
                        <th>Rating</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{pick.pick_number}</td>
                        <td><strong>{pick.player_name}</strong></td>
                        <td>{pick.team_name}</td>
                        <td>{pick.position}</td>
                        <td class="highlight">{pick.points_scored:.1f}</td>
                        <td>{pick.points_per_game:.1f}</td>
                        <td><span style="color: #10b981;">{pick.value_rating}</span></td>
                    </tr>
                    """ for pick in sorted([p for team in draft.team_grades for p in team.picks], key=lambda x: x.points_scored / (x.pick_number + 1), reverse=True)[:5])}
                </tbody>
            </table>

            <h3 style="margin-top: 40px; color: #f87171;">Top 5 Worst Picks (vs Expected)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Pick #</th>
                        <th>Player</th>
                        <th>Team</th>
                        <th>Position</th>
                        <th>Points</th>
                        <th>PPG</th>
                        <th>Rating</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{pick.pick_number}</td>
                        <td><strong>{pick.player_name}</strong></td>
                        <td>{pick.team_name}</td>
                        <td>{pick.position}</td>
                        <td class="lowlight">{pick.points_scored:.1f}</td>
                        <td>{pick.points_per_game:.1f}</td>
                        <td><span style="color: #f87171;">{pick.value_rating}</span></td>
                    </tr>
                    """ for pick in sorted([p for team in draft.team_grades for p in team.picks if p.pick_number <= 60], key=lambda x: x.points_scored / max(61 - x.pick_number, 1))[:5])}
                </tbody>
            </table>
        </div>

        <!-- Transaction Activity -->
        <div class="section">
            <h2><span class="emoji">📋</span>Transaction Activity</h2>
            <p style="color: #94a3b8; margin-bottom: 20px;">Who made the most moves?</p>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Total Moves</th>
                        <th>Trades</th>
                        <th>Waivers</th>
                        <th>Free Agents</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{idx + 1}</td>
                        <td><strong>{ctx.get_team_name(roster_id)}</strong></td>
                        <td class="highlight">{counts['total']}</td>
                        <td>{counts['trades']}</td>
                        <td>{counts['waivers']}</td>
                        <td>{counts['free_agents']}</td>
                    </tr>
                    """ for idx, (roster_id, counts) in enumerate(sorted(transaction_counts.items(), key=lambda x: x[1]['total'], reverse=True)))}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated with <a href="https://github.com/anthropics/claude-code" style="color: #60a5fa;">Claude Code</a></p>
            <p>Sleeper Analytics | {ctx.league_name}</p>
        </div>
    </div>
</body>
</html>
"""
    return html


async def main():
    """Main entry point."""
    # Read leagues.json
    with open("leagues.json") as f:
        config = json.load(f)

    # Generate reports for each league
    for league in config["leagues"]:
        try:
            await generate_league_report(
                league["id"],
                league["name"],
                league["season"]
            )
        except Exception as e:
            print(f"\n❌ Error generating report for {league['name']}: {e}")
            import traceback
            traceback.print_exc()

    # Generate index page
    print("\n📝 Generating index page...")
    generate_index(config["leagues"])
    print("   ✅ Saved to: docs/index.html")

    print("\n✅ All reports generated successfully!")
    print("\n📂 Files created in docs/ folder")
    print("🌐 Ready for GitHub Pages!")


def generate_index(leagues):
    """Generate index page with league ID input and pre-generated reports."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sleeper Analytics</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            max-width: 800px;
            text-align: center;
        }}
        h1 {{
            font-size: 3em;
            margin-bottom: 20px;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            color: #94a3b8;
            font-size: 1.2em;
            margin-bottom: 50px;
        }}
        .input-section {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 40px;
        }}
        .input-group {{ margin-bottom: 20px; }}
        label {{
            display: block;
            color: #94a3b8;
            margin-bottom: 10px;
            font-size: 0.9em;
        }}
        input {{
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(96, 165, 250, 0.3);
            background: rgba(15, 23, 42, 0.8);
            color: #e2e8f0;
            border-radius: 8px;
            font-size: 1em;
            transition: all 0.3s ease;
        }}
        input:focus {{
            outline: none;
            border-color: #60a5fa;
            box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
        }}
        .example {{
            color: #64748b;
            font-size: 0.85em;
            margin-top: 8px;
            text-align: left;
        }}
        .example code {{
            background: rgba(96, 165, 250, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            color: #60a5fa;
        }}
        button {{
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 8px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(96, 165, 250, 0.4);
        }}
        .divider {{
            margin: 50px 0;
            text-align: center;
            color: #64748b;
            position: relative;
        }}
        .divider::before, .divider::after {{
            content: '';
            position: absolute;
            top: 50%;
            width: 40%;
            height: 1px;
            background: rgba(255, 255, 255, 0.1);
        }}
        .divider::before {{ left: 0; }}
        .divider::after {{ right: 0; }}
        .leagues {{ display: grid; gap: 20px; }}
        .league-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 16px;
            text-decoration: none;
            color: inherit;
            display: block;
            transition: all 0.3s ease;
        }}
        .league-card:hover {{
            transform: translateY(-5px);
            border-color: #60a5fa;
            box-shadow: 0 10px 40px rgba(96, 165, 250, 0.3);
        }}
        .league-name {{
            font-size: 1.8em;
            color: #60a5fa;
            margin-bottom: 10px;
        }}
        .league-season {{ color: #94a3b8; }}
        .footer {{
            margin-top: 50px;
            color: #64748b;
            font-size: 0.9em;
        }}
        .error {{
            color: #f87171;
            margin-top: 10px;
            font-size: 0.9em;
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 Sleeper Analytics</h1>
        <div class="subtitle">Advanced Fantasy Football Analytics</div>

        <div class="input-section">
            <h2 style="color: #e2e8f0; margin-bottom: 20px;">Enter Your League</h2>
            <div class="input-group">
                <label for="leagueInput">Paste your Sleeper league URL or ID</label>
                <input type="text" id="leagueInput" placeholder="https://sleeper.com/leagues/1257152597513490432/matchup">
                <div class="example">
                    Example: <code>https://sleeper.com/leagues/1257152597513490432/matchup</code><br>
                    Or just the ID: <code>1257152597513490432</code>
                </div>
                <div class="error" id="error">Please enter a valid league URL or ID</div>
            </div>
            <button onclick="goToLeague()">View Analytics</button>
        </div>

        <div class="divider">OR</div>

        <h3 style="color: #94a3b8; margin-bottom: 20px;">Pre-Generated Reports</h3>
        <div class="leagues">
            {''.join(f'''
            <a href="{league['name'].lower().replace(' ', '-').replace("'", '')}.html" class="league-card">
                <div class="league-name">{league['name']}</div>
                <div class="league-season">Season {league['season']}</div>
            </a>
            ''' for league in leagues)}
        </div>

        <div class="footer">
            <p>Generated with Claude Code</p>
        </div>
    </div>

    <script>
        function extractLeagueId(input) {{
            input = input.trim();
            const urlMatch = input.match(/leagues\\/(\\d+)/);
            if (urlMatch) return urlMatch[1];
            if (/^\\d+$/.test(input)) return input;
            return null;
        }}
        function goToLeague() {{
            const input = document.getElementById('leagueInput').value;
            const errorDiv = document.getElementById('error');
            const leagueId = extractLeagueId(input);
            if (!leagueId) {{
                errorDiv.style.display = 'block';
                return;
            }}
            errorDiv.style.display = 'none';
            window.location.href = `app.html?league_id=${{leagueId}}`;
        }}
        document.getElementById('leagueInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') goToLeague();
        }});
    </script>
</body>
</html>
"""
    Path("docs/index.html").write_text(html)


def generate_roster_construction_chart(roster_construction):
    """Generate stacked bar chart for roster construction (sorted by points for)."""
    import plotly.graph_objects as go

    # Sort teams by total points (descending)
    teams_sorted = sorted(roster_construction.all_teams, key=lambda x: x.breakdown.total_points, reverse=True)

    teams = [team.team_name for team in teams_sorted]
    draft_pts = [team.breakdown.draft_points for team in teams_sorted]
    trade_pts = [team.breakdown.trade_points for team in teams_sorted]
    waiver_pts = [team.breakdown.waiver_points for team in teams_sorted]
    fa_pts = [team.breakdown.free_agent_points for team in teams_sorted]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Draft',
        x=teams,
        y=draft_pts,
        marker_color='#3b82f6',
        hovertemplate='<b>%{x}</b><br>Draft: %{y:.1f} pts<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Trades',
        x=teams,
        y=trade_pts,
        marker_color='#8b5cf6',
        hovertemplate='<b>%{x}</b><br>Trades: %{y:.1f} pts<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Waivers',
        x=teams,
        y=waiver_pts,
        marker_color='#10b981',
        hovertemplate='<b>%{x}</b><br>Waivers: %{y:.1f} pts<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Free Agents',
        x=teams,
        y=fa_pts,
        marker_color='#f59e0b',
        hovertemplate='<b>%{x}</b><br>Free Agents: %{y:.1f} pts<extra></extra>'
    ))

    fig.update_layout(
        barmode='stack',
        title='Roster Construction: Point Sources by Team (Sorted by Total Points)',
        xaxis_title='Team',
        yaxis_title='Points',
        plot_bgcolor='rgba(15, 23, 42, 0.8)',
        paper_bgcolor='rgba(15, 23, 42, 0)',
        font=dict(color='#e2e8f0'),
        xaxis=dict(tickangle=-45),
        height=500,
        hovermode='x unified'
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_draft_chart(draft):
    """Generate scatter plot with trend line for draft picks."""
    import plotly.graph_objects as go
    import numpy as np

    # Collect all picks with their actual points
    pick_numbers = []
    actual_points = []
    player_names = []
    teams = []
    value_ratings = []

    for team_grade in draft.team_grades:
        for pick in team_grade.picks:
            pick_numbers.append(pick.pick_number)
            actual_points.append(pick.points_scored)
            player_names.append(pick.player_name)
            teams.append(pick.team_name)
            value_ratings.append(pick.value_rating)

    # Calculate expected points (trend line using polynomial fit)
    if len(pick_numbers) > 0:
        z = np.polyfit(pick_numbers, actual_points, 2)  # 2nd degree polynomial
        p = np.poly1d(z)
        pick_range = np.linspace(min(pick_numbers), max(pick_numbers), 100)
        expected_points = p(pick_range)

    # Create color mapping for value ratings
    color_map = {'Hit': '#10b981', 'Solid': '#fbbf24', 'Bust': '#f87171'}
    colors = [color_map.get(rating, '#64748b') for rating in value_ratings]

    fig = go.Figure()

    # Add expected points trend line
    if len(pick_numbers) > 0:
        fig.add_trace(go.Scatter(
            x=pick_range,
            y=expected_points,
            mode='lines',
            name='Expected Points',
            line=dict(color='#94a3b8', width=3, dash='dash'),
            hoverinfo='skip'
        ))

    # Add actual picks as scatter points
    fig.add_trace(go.Scatter(
        x=pick_numbers,
        y=actual_points,
        mode='markers',
        name='Actual Points',
        marker=dict(size=10, color=colors, line=dict(color='#ffffff', width=1)),
        text=[f"{name}<br>{team}<br>{rating}" for name, team, rating in zip(player_names, teams, value_ratings)],
        hovertemplate='<b>Pick %{x}</b><br>%{text}<br>Points: %{y:.1f}<extra></extra>'
    ))

    fig.update_layout(
        title='Draft Pick Performance: Expected vs Actual Points',
        xaxis=dict(
            title='Pick Number',
            gridcolor='#374151',
            gridwidth=1
        ),
        yaxis=dict(
            title='Points Scored',
            gridcolor='#374151',
            gridwidth=1
        ),
        plot_bgcolor='rgba(15, 23, 42, 0.8)',
        paper_bgcolor='rgba(15, 23, 42, 0)',
        font=dict(color='#e2e8f0'),
        height=500,
        showlegend=True,
        hovermode='closest'
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_luck_chart(luck):
    """Generate luck vs wins visualization with teams on Y-axis."""
    import plotly.graph_objects as go

    # Sort teams by actual wins (descending)
    teams_sorted = sorted(luck.team_reports, key=lambda x: x.actual_wins, reverse=True)

    teams = [t.team_name for t in teams_sorted]
    actual_wins = [t.actual_wins for t in teams_sorted]
    expected_wins = [t.expected_wins for t in teams_sorted]

    fig = go.Figure()

    # Add horizontal lines connecting actual to expected wins for each team
    for i in range(len(teams)):
        fig.add_trace(go.Scatter(
            x=[expected_wins[i], actual_wins[i]],
            y=[i, i],
            mode='lines',
            line=dict(color='#ffffff', width=2),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Add expected wins markers
    fig.add_trace(go.Scatter(
        x=expected_wins,
        y=list(range(len(teams))),
        mode='markers',
        name='Expected Wins',
        marker=dict(size=12, color='#10b981', symbol='diamond'),
        hovertemplate='<b>%{text}</b><br>Expected: %{x:.1f} wins<extra></extra>',
        text=teams
    ))

    # Add actual wins markers
    fig.add_trace(go.Scatter(
        x=actual_wins,
        y=list(range(len(teams))),
        mode='markers',
        name='Actual Wins',
        marker=dict(size=12, color='#3b82f6', symbol='circle'),
        hovertemplate='<b>%{text}</b><br>Actual: %{x:.1f} wins<extra></extra>',
        text=teams
    ))

    fig.update_layout(
        title='Actual vs Expected Wins (Sorted by Actual Wins)',
        xaxis=dict(
            title='Wins',
            gridcolor='#374151',  # Grey grid lines
            gridwidth=1
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(len(teams))),
            ticktext=teams,
            title='',
            gridcolor='#374151',  # Grey grid lines
            gridwidth=1
        ),
        plot_bgcolor='rgba(15, 23, 42, 0.8)',
        paper_bgcolor='rgba(15, 23, 42, 0)',
        font=dict(color='#e2e8f0'),
        height=500,
        hovermode='x unified',
        showlegend=True
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


if __name__ == "__main__":
    asyncio.run(main())
