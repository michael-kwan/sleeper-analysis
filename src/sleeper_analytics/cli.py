"""
Sleeper Analytics CLI

Command-line interface for analyzing fantasy football leagues
without running the API server.
"""

import argparse
import asyncio
import sys
import webbrowser
from pathlib import Path
from typing import Any

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.services.efficiency import EfficiencyService
from sleeper_analytics.services.matchups import MatchupService
from sleeper_analytics.services.nfl_stats import NFLStatsService, get_nfl_stats_service
from sleeper_analytics.services.trades import TransactionService
from sleeper_analytics.visualization import charts


class SleeperAnalytics:
    """
    Main class for analyzing Sleeper fantasy football leagues.

    Can be used as a library or via CLI.

    Example:
        async with SleeperAnalytics() as analytics:
            leagues = await analytics.get_user_leagues("michaelburps", 2025)
            for league in leagues:
                print(league["name"], league["league_id"])

            # Analyze a specific league
            await analytics.set_league("1127116641403351040")
            standings = await analytics.get_standings()
            dashboard = await analytics.generate_dashboard()
    """

    def __init__(self, season: int = 2024):
        self.season = season
        self.client: SleeperClient | None = None
        self.ctx: LeagueContext | None = None
        self.nfl_stats: NFLStatsService | None = None

    async def __aenter__(self):
        self.client = SleeperClient()
        await self.client.__aenter__()
        self.nfl_stats = get_nfl_stats_service(self.season)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_user(self, username: str) -> dict[str, Any] | None:
        """Get user info by username."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")
        user = await self.client.get_user(username)
        if user:
            return user.model_dump()
        return None

    async def get_user_leagues(
        self, username: str, season: int | None = None
    ) -> list[dict[str, Any]]:
        """Get all leagues for a user in a given season."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        season = season or self.season
        leagues = await self.client.get_user_leagues(username, season)
        return [league.model_dump() for league in leagues]

    async def set_league(self, league_id: str) -> dict[str, Any]:
        """Set the active league for analysis."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        self.ctx = await LeagueContext.create(self.client, league_id)
        return self.ctx.league.model_dump()

    def _require_league(self):
        """Ensure a league is set."""
        if not self.ctx:
            raise RuntimeError("No league set. Call set_league() first.")
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

    async def get_standings(self, weeks: int = 17) -> list[dict[str, Any]]:
        """Get league standings."""
        self._require_league()
        service = MatchupService(self.client, self.ctx)
        standings = await service.get_league_standings(weeks)
        return [s.model_dump() for s in standings]

    async def get_team_performance(
        self, roster_id: int, weeks: int = 17
    ) -> dict[str, Any]:
        """Get detailed performance for a specific team."""
        self._require_league()
        service = MatchupService(self.client, self.ctx)
        perf = await service.get_team_performance(roster_id, weeks)
        return perf.model_dump()

    async def get_all_performances(self, weeks: int = 17) -> list[dict[str, Any]]:
        """Get performance for all teams."""
        self._require_league()
        service = MatchupService(self.client, self.ctx)

        performances = []
        for roster in self.ctx.rosters:
            perf = await service.get_team_performance(roster.roster_id, weeks)
            performances.append(perf)
        return performances

    async def get_matchups(self, week: int) -> list[dict[str, Any]]:
        """Get matchups for a specific week."""
        self._require_league()
        service = MatchupService(self.client, self.ctx)
        matchups = await service.get_weekly_matchups(week)
        return [m.model_dump() for m in matchups]

    async def get_close_games(
        self, threshold: float = 10.0, weeks: int = 17
    ) -> list[dict[str, Any]]:
        """Get all close games within threshold."""
        self._require_league()
        service = MatchupService(self.client, self.ctx)
        return await service.get_close_games(threshold, weeks)

    async def get_efficiency_rankings(self, weeks: int = 17) -> list[dict[str, Any]]:
        """Get roster efficiency rankings."""
        self._require_league()
        service = EfficiencyService(self.client, self.ctx)
        return await service.get_league_efficiency_rankings(weeks)

    async def get_team_efficiency(
        self, roster_id: int, weeks: int = 17
    ) -> dict[str, Any]:
        """Get efficiency report for a specific team."""
        self._require_league()
        service = EfficiencyService(self.client, self.ctx)
        eff = await service.get_season_efficiency(roster_id, weeks)
        return eff.model_dump()

    async def get_trade_analysis(self, weeks: int = 18) -> list[dict[str, Any]]:
        """Analyze all trades in the league."""
        self._require_league()
        service = TransactionService(self.client, self.ctx, self.nfl_stats)
        analyses = await service.analyze_trades(weeks)
        return [a.model_dump() for a in analyses]

    async def get_transaction_summary(self, weeks: int = 18) -> dict[str, Any]:
        """Get transaction summary."""
        self._require_league()
        service = TransactionService(self.client, self.ctx, self.nfl_stats)
        summary = await service.get_transaction_summary(weeks)
        return summary.model_dump()

    async def get_waiver_analysis(
        self, weeks: int = 18, top_n: int = 20
    ) -> list[dict[str, Any]]:
        """Analyze best waiver pickups."""
        self._require_league()
        service = TransactionService(self.client, self.ctx, self.nfl_stats)
        return await service.get_waiver_analysis(weeks, top_n)

    async def generate_dashboard(
        self, weeks: int = 17, output_path: str | None = None
    ) -> str:
        """
        Generate a full HTML dashboard.

        Args:
            weeks: Number of weeks to analyze
            output_path: Optional path to save the HTML file

        Returns:
            HTML string of the dashboard
        """
        self._require_league()

        matchup_service = MatchupService(self.client, self.ctx)
        efficiency_service = EfficiencyService(self.client, self.ctx)
        txn_service = TransactionService(self.client, self.ctx, self.nfl_stats)

        # Generate all chart data
        standings = await matchup_service.get_league_standings(weeks)
        standings_html = charts.standings_chart(standings)

        performances = []
        for roster in self.ctx.rosters:
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

        season = self.ctx.league.season if self.ctx.league.season else self.season

        html = charts.generate_dashboard(
            standings_html=standings_html,
            weekly_scores_html=weekly_scores_html,
            efficiency_html=efficiency_html,
            trades_html=trades_html,
            distribution_html=distribution_html,
            transactions_html=transactions_html,
            league_name=self.ctx.league.name,
            season=int(season) if isinstance(season, str) else season,
        )

        if output_path:
            Path(output_path).write_text(html)
            print(f"📊 Dashboard saved to: {output_path}")

        return html


async def cli_main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sleeper Fantasy Football Analytics CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List leagues for a user
  sleeper-cli leagues michaelburps --season 2025

  # Show standings for a league
  sleeper-cli standings 1127116641403351040

  # Generate dashboard
  sleeper-cli dashboard 1127116641403351040 --output dashboard.html --open

  # Show efficiency rankings
  sleeper-cli efficiency 1127116641403351040

  # Analyze trades
  sleeper-cli trades 1127116641403351040
        """,
    )

    parser.add_argument(
        "--season",
        type=int,
        default=2024,
        help="NFL season year (default: 2024)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=17,
        help="Number of weeks to analyze (default: 17)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # leagues command
    leagues_parser = subparsers.add_parser("leagues", help="List user's leagues")
    leagues_parser.add_argument("username", help="Sleeper username")
    leagues_parser.add_argument(
        "--season", "-s",
        type=int,
        default=2024,
        help="NFL season year (default: 2024)",
    )

    # standings command
    standings_parser = subparsers.add_parser("standings", help="Show league standings")
    standings_parser.add_argument("league_id", help="Sleeper league ID")

    # efficiency command
    efficiency_parser = subparsers.add_parser(
        "efficiency", help="Show roster efficiency rankings"
    )
    efficiency_parser.add_argument("league_id", help="Sleeper league ID")

    # trades command
    trades_parser = subparsers.add_parser("trades", help="Analyze trades")
    trades_parser.add_argument("league_id", help="Sleeper league ID")

    # transactions command
    txn_parser = subparsers.add_parser("transactions", help="Transaction summary")
    txn_parser.add_argument("league_id", help="Sleeper league ID")

    # close-games command
    close_parser = subparsers.add_parser("close-games", help="Show close games")
    close_parser.add_argument("league_id", help="Sleeper league ID")
    close_parser.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        help="Point threshold for close games (default: 10)",
    )

    # dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="Generate HTML dashboard"
    )
    dashboard_parser.add_argument("league_id", help="Sleeper league ID")
    dashboard_parser.add_argument(
        "--output", "-o", default="dashboard.html", help="Output file path"
    )
    dashboard_parser.add_argument(
        "--open", action="store_true", help="Open dashboard in browser"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    async with SleeperAnalytics(season=args.season) as analytics:
        if args.command == "leagues":
            print(f"🔍 Looking up leagues for {args.username} ({args.season})...\n")
            leagues = await analytics.get_user_leagues(args.username, args.season)

            if not leagues:
                print(f"No leagues found for {args.season}.")
                return

            print(f"Found {len(leagues)} league(s):\n")
            for i, league in enumerate(leagues, 1):
                print(f"  {i}. {league['name']}")
                print(f"     ID: {league['league_id']}")
                print(f"     Teams: {league['total_rosters']}")
                print(f"     Status: {league['status']}")
                print()

        elif args.command == "standings":
            await analytics.set_league(args.league_id)
            print(f"📊 {analytics.ctx.league.name} - Standings\n")

            standings = await analytics.get_standings(args.weeks)

            print(f"{'Rank':<5} {'Team':<25} {'Record':<10} {'PF':<10} {'PA':<10}")
            print("-" * 60)
            for s in standings:
                record = f"{s['wins']}-{s['losses']}"
                if s['ties']:
                    record += f"-{s['ties']}"
                print(
                    f"{s['rank']:<5} {s['team_name']:<25} {record:<10} "
                    f"{s['points_for']:<10.1f} {s['points_against']:<10.1f}"
                )

        elif args.command == "efficiency":
            await analytics.set_league(args.league_id)
            print(f"📊 {analytics.ctx.league.name} - Efficiency Rankings\n")

            rankings = await analytics.get_efficiency_rankings(args.weeks)

            print(f"{'Rank':<5} {'Team':<25} {'Eff %':<10} {'Bench Pts':<12} {'Missed':<8}")
            print("-" * 60)
            for r in rankings:
                print(
                    f"{r['rank']:<5} {r['team_name']:<25} {r['efficiency_pct']:<10.1f} "
                    f"{r['points_left_on_bench']:<12.1f} {r['missed_opportunities']:<8}"
                )

        elif args.command == "trades":
            await analytics.set_league(args.league_id)
            print(f"📊 {analytics.ctx.league.name} - Trade Analysis\n")

            trades = await analytics.get_trade_analysis(args.weeks + 1)

            if not trades:
                print("No trades found.")
                return

            for trade in trades:
                print(f"Week {trade['week']} - {trade['fairness']}")
                for side in trade['sides']:
                    assets = ", ".join(
                        a.get('player_name') or f"Round {a.get('pick_round')} Pick"
                        for a in side['assets_received']
                    )
                    print(f"  {side['team_name']} receives: {assets}")
                    print(f"    Total value: {side['total_value']}")
                if trade['winner']:
                    print(f"  Winner: {trade['winner']}")
                print()

        elif args.command == "transactions":
            await analytics.set_league(args.league_id)
            print(f"📊 {analytics.ctx.league.name} - Transaction Summary\n")

            summary = await analytics.get_transaction_summary(args.weeks + 1)

            print(f"Total transactions: {summary['total']}\n")
            print("By type:")
            for t, count in summary['by_type'].items():
                print(f"  {t}: {count}")

            print("\nBy team:")
            for team, counts in sorted(
                summary['by_team'].items(),
                key=lambda x: sum(x[1].values()),
                reverse=True,
            ):
                total = sum(counts.values())
                print(f"  {team}: {total}")

        elif args.command == "close-games":
            await analytics.set_league(args.league_id)
            print(f"📊 {analytics.ctx.league.name} - Close Games (<{args.threshold} pts)\n")

            games = await analytics.get_close_games(args.threshold, args.weeks)

            if not games:
                print("No close games found.")
                return

            for game in games[:20]:
                print(
                    f"Week {game['week']}: {game['team1']} ({game['team1_points']:.1f}) vs "
                    f"{game['team2']} ({game['team2_points']:.1f}) - "
                    f"Margin: {game['margin']:.1f}"
                )

        elif args.command == "dashboard":
            await analytics.set_league(args.league_id)
            print(f"📊 Generating dashboard for {analytics.ctx.league.name}...")

            html = await analytics.generate_dashboard(args.weeks, args.output)

            if args.open:
                output_path = Path(args.output).absolute()
                webbrowser.open(f"file://{output_path}")
                print(f"🌐 Opened in browser: {output_path}")


def run_cli():
    """Entry point for CLI."""
    asyncio.run(cli_main())


if __name__ == "__main__":
    run_cli()
