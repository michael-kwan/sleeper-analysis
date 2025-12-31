"""Test script to verify roster construction analysis."""

import asyncio

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.services.roster_construction import RosterConstructionService


async def test_roster_construction():
    """Test roster construction analysis."""
    league_id = "1257152597513490432"  # 2025 league

    async with SleeperClient() as client:
        # Create league context
        print(f"Loading league context for {league_id}...")
        ctx = await LeagueContext.create(client, league_id)
        print(f"League: {ctx.league_name}\n")

        # Create service
        service = RosterConstructionService(client, ctx)

        # Test team analysis
        first_roster_id = ctx.rosters[0].roster_id
        team_name = ctx.get_team_name(first_roster_id)

        print(f"{'='*70}")
        print(f"Testing Roster Construction for {team_name}")
        print(f"{'='*70}\n")

        team_report = await service.analyze_team_roster_construction(
            first_roster_id, weeks=5
        )

        print(f"Team: {team_report.team_name}\n")

        breakdown = team_report.breakdown
        print(f"Point Breakdown:")
        print(f"  Draft:       {breakdown.draft_points:>8.2f} pts ({breakdown.draft_percentage:>5.1f}%) - {breakdown.draft_count} players")
        print(f"  Trades:      {breakdown.trade_points:>8.2f} pts ({breakdown.trade_percentage:>5.1f}%) - {breakdown.trade_count} players")
        print(f"  Waivers:     {breakdown.waiver_points:>8.2f} pts ({breakdown.waiver_percentage:>5.1f}%) - {breakdown.waiver_count} players")
        print(f"  Free Agents: {breakdown.free_agent_points:>8.2f} pts ({breakdown.free_agent_percentage:>5.1f}%) - {breakdown.free_agent_count} players")
        print(f"  {'─'*50}")
        print(f"  Total:       {breakdown.total_points:>8.2f} pts (100.0%)\n")

        print(f"Insights:")
        print(f"  Primary Source: {team_report.primary_source.value.title()}")
        print(f"  Draft Reliance: {team_report.draft_reliance}")
        print(f"  Waiver Activity: {team_report.waiver_activity}\n")

        # Show top 10 acquisitions by points
        sorted_acqs = sorted(
            team_report.acquisitions,
            key=lambda x: x.points_scored,
            reverse=True
        )[:10]

        print(f"Top 10 Acquisitions by Points:")
        print(f"{'Player':<25} {'Pos':<5} {'Method':<12} {'Week':<5} {'Points':<8} {'Status'}")
        print("─" * 75)

        for acq in sorted_acqs:
            status = "Active" if acq.is_currently_owned else f"Dropped"
            method_display = acq.acquisition_method.value.replace("_", " ").title()
            print(f"{acq.player_name:<25} {acq.position:<5} {method_display:<12} "
                  f"{acq.acquisition_week:<5} {acq.points_scored:>6.2f}   {status}")

        # Test league-wide report
        print(f"\n{'='*70}")
        print(f"Testing League-Wide Roster Construction Report")
        print(f"{'='*70}\n")

        league_report = await service.get_league_roster_construction_report(weeks=5)

        print(f"League: {league_report.league_name}")
        print(f"Weeks Analyzed: {league_report.weeks_analyzed}\n")

        print(f"League Averages:")
        print(f"  Draft:       {league_report.avg_draft_percentage:>5.1f}%")
        print(f"  Trades:      {league_report.avg_trade_percentage:>5.1f}%")
        print(f"  Waivers:     {league_report.avg_waiver_percentage:>5.1f}%")
        print(f"  Free Agents: {league_report.avg_free_agent_percentage:>5.1f}%\n")

        print(f"Champions:")
        print(f"  🏆 Best Drafter: {league_report.best_drafter} "
              f"({league_report.best_drafter_pct:.1f}% from draft)")
        print(f"  🔄 Most Active Trader: {league_report.most_active_trader} "
              f"({league_report.most_active_trader_count} trades)")
        print(f"  📊 Waiver Wire King: {league_report.waiver_wire_king} "
              f"({league_report.waiver_wire_king_points:.2f} pts from waivers)\n")

        # Show all teams sorted by draft percentage
        sorted_teams = sorted(
            league_report.all_teams,
            key=lambda t: t.breakdown.draft_percentage,
            reverse=True
        )

        print(f"All Teams (by Draft %):")
        print(f"{'Rank':<6} {'Team':<30} {'Draft%':<10} {'Trade%':<10} {'Waiver%':<10} {'FA%'}")
        print("─" * 80)

        for idx, team in enumerate(sorted_teams, 1):
            b = team.breakdown
            print(f"{idx:<6} {team.team_name:<30} {b.draft_percentage:>6.1f}%   "
                  f"{b.trade_percentage:>6.1f}%   {b.waiver_percentage:>6.1f}%   "
                  f"{b.free_agent_percentage:>6.1f}%")

        print(f"\n✅ Roster Construction Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_roster_construction())
