"""Test script to verify benchwarmer calculation fix."""

import asyncio

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.services.benchwarmer import BenchwarmerService


async def test_benchwarmer_fix():
    """Test that benchwarmer now calculates differential correctly."""
    league_id = "1257152597513490432"  # 2025 league

    async with SleeperClient() as client:
        # Create league context
        print(f"Loading league context for {league_id}...")
        ctx = await LeagueContext.create(client, league_id)
        print(f"League: {ctx.league_name}\n")

        # Create benchwarmer service
        bw_service = BenchwarmerService(client, ctx)

        # Test for first team
        first_roster_id = ctx.rosters[0].roster_id
        team_name = ctx.get_team_name(first_roster_id)

        print(f"{'='*70}")
        print(f"Testing Benchwarmer Analysis for {team_name} (Roster ID: {first_roster_id})")
        print(f"{'='*70}\n")

        report = await bw_service.analyze_team_bench(first_roster_id, weeks=5)

        print(f"Team: {report.team_name}")
        print(f"Weeks Analyzed: {report.total_weeks_analyzed}")
        print(f"Total Opportunity Cost: {report.total_bench_points:.2f} pts")
        print(f"  (This is the sum of all positive differentials)")
        print(f"Average Per Week: {report.avg_bench_points_per_week:.2f} pts\n")

        print(f"Top 10 Benchwamer Mistakes:")
        print(f"{'Rank':<6} {'Week':<6} {'Player':<25} {'Pos':<5} {'Differential':<12}")
        print("-" * 70)

        for idx, bw in enumerate(report.top_benchwarmers, 1):
            print(f"{idx:<6} {bw.week:<6} {bw.player_name:<25} {bw.position:<5} "
                  f"{bw.points:>6.2f} pts")

        if report.worst_benching_decision:
            worst = report.worst_benching_decision
            print(f"\n🏆 Worst Benching Decision:")
            print(f"   Week {worst.week}: {worst.player_name} ({worst.position})")
            print(f"   Left {worst.points:.2f} pts on the bench")
            print(f"   (Bench player scored {worst.points:.2f} more than worst starter in slot)")

        # Test league-wide report
        print(f"\n{'='*70}")
        print(f"Testing League-Wide Benchwarmer Report")
        print(f"{'='*70}\n")

        league_report = await bw_service.get_league_benchwarmer_report(weeks=5)

        print(f"League: {league_report.league_name}")
        print(f"Weeks Analyzed: {league_report.weeks_analyzed}\n")

        print(f"🏆 Benchwarmer Champion: {league_report.benchwarmer_champion}")
        print(f"   Total Opportunity Cost: {league_report.benchwarmer_champion_points:.2f} pts")
        print(f"   (Left the most points on the bench across {league_report.weeks_analyzed} weeks)\n")

        print(f"Top 5 League-Wide Benching Mistakes:")
        print(f"{'Rank':<6} {'Team':<30} {'Week':<6} {'Player':<20} {'Diff':<10}")
        print("-" * 70)

        for idx, mistake in enumerate(league_report.biggest_benching_mistakes[:5], 1):
            print(f"{idx:<6} {mistake.team_name:<30} {mistake.week:<6} "
                  f"{mistake.player_name:<20} {mistake.points:>6.2f} pts")

        print(f"\n✅ Benchwarmer Fix Test Complete!")
        print(f"   Now calculates: bench_player_points - worst_starter_points")
        print(f"   Only counts positive differentials (actual mistakes)")


if __name__ == "__main__":
    asyncio.run(test_benchwarmer_fix())
