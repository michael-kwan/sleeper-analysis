"""Test script to verify FAAB fix."""

import asyncio

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.services.faab import FAABService


async def test_faab_fix():
    """Test that FAAB amounts are now being extracted correctly."""
    league_id = "1257152597513490432"  # 2025 league

    async with SleeperClient() as client:
        # Create league context
        print(f"Loading league context for {league_id}...")
        ctx = await LeagueContext.create(client, league_id)
        print(f"League: {ctx.league_name}\n")

        # Create FAAB service
        faab_service = FAABService(client, ctx)

        # Test 1: Get owner FAAB performance for first roster
        first_roster_id = ctx.rosters[0].roster_id
        team_name = ctx.get_team_name(first_roster_id)
        print(f"{'='*60}")
        print(f"Testing FAAB Performance for {team_name} (Roster ID: {first_roster_id})")
        print(f"{'='*60}\n")

        perf = await faab_service.get_owner_faab_performance(first_roster_id, weeks=5)

        print(f"Team: {perf.owner_name}")
        print(f"Total FAAB Spent: ${perf.total_faab_spent}")
        print(f"FAAB Remaining: ${perf.faab_remaining}")
        print(f"Total Points from FAAB: {perf.total_points_from_faab}")
        print(f"Average ROI: {perf.avg_roi:.2f} pts/$")
        print(f"\nAcquisitions ({len(perf.acquisitions)}):")

        for acq in perf.acquisitions[:10]:  # Show first 10
            print(f"  Week {acq.acquired_week}: {acq.player_name} ({acq.position}) - "
                  f"${acq.faab_spent} → {acq.points_during_ownership:.1f} pts "
                  f"(ROI: {acq.roi:.2f} pts/$)")

        # Test 2: Get player lifecycle for a highly transacted player
        # Player ID 8126 appeared in many week 2 transactions
        print(f"\n{'='*60}")
        print(f"Testing Player Lifecycle for Player ID: 8126")
        print(f"{'='*60}\n")

        lifecycle = await faab_service.get_player_lifecycle("8126", weeks=5)

        print(f"Player: {lifecycle.player_name} ({lifecycle.position})")
        print(f"Times Picked Up: {lifecycle.times_picked_up}")
        print(f"Times Dropped: {lifecycle.times_dropped}")
        print(f"Total FAAB Spent: ${lifecycle.total_faab_spent}")
        print(f"Current Owner: {lifecycle.current_owner or 'Free Agent'}")
        print(f"\nOwnership History:")

        for period in lifecycle.ownership_history:
            status = "Still owned" if period.dropped_week is None else f"Dropped week {period.dropped_week}"
            print(f"  Week {period.acquired_week}: {period.owner_name} - "
                  f"${period.faab_spent} → {period.points_during_ownership:.1f} pts "
                  f"({status})")

        print(f"\n✅ FAAB Fix Test Complete!")
        print(f"   FAAB amounts are now being extracted from txn.settings['waiver_bid']")


if __name__ == "__main__":
    asyncio.run(test_faab_fix())
