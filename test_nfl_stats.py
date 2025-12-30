#!/usr/bin/env python3
"""Test NFL stats integration with nfl-data-py."""

import nfl_data_py as nfl


def main():
    print("🏈 Testing NFL Data Integration\n")

    # Test 1: Fetch weekly data for 2024
    print("📊 Test 1: Fetching weekly data for 2024...")
    try:
        weekly_2024 = nfl.import_weekly_data([2024])
        print(f"   ✅ Loaded {len(weekly_2024)} rows of weekly data")
        print(f"   Columns: {list(weekly_2024.columns[:10])}...")
        print(f"   Sample player: {weekly_2024.iloc[0]['player_display_name']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Fetch seasonal data
    print("\n📊 Test 2: Fetching seasonal data for 2024...")
    try:
        seasonal_2024 = nfl.import_seasonal_data([2024])
        print(f"   ✅ Loaded {len(seasonal_2024)} rows of seasonal data")
        print(f"   Sample: {seasonal_2024.iloc[0]['player_display_name']} - "
              f"{seasonal_2024.iloc[0]['completions']} completions")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Calculate fantasy points with custom scoring
    print("\n📊 Test 3: Testing custom scoring calculation...")
    try:
        # Get a QB's stats
        qb_data = weekly_2024[
            (weekly_2024['position'] == 'QB') &
            (weekly_2024['week'] == 1)
        ].head(1)

        if not qb_data.empty:
            qb = qb_data.iloc[0]

            # Standard scoring
            std_points = (
                qb['passing_yards'] * 0.04 +
                qb['passing_tds'] * 4 +
                qb['interceptions'] * -1 +
                qb['rushing_yards'] * 0.1 +
                qb['rushing_tds'] * 6
            )

            # Custom scoring (e.g., 6pt passing TDs)
            custom_points = (
                qb['passing_yards'] * 0.04 +
                qb['passing_tds'] * 6 +  # Changed from 4 to 6
                qb['interceptions'] * -1 +
                qb['rushing_yards'] * 0.1 +
                qb['rushing_tds'] * 6
            )

            print(f"   ✅ {qb['player_display_name']} Week 1:")
            print(f"      Standard scoring: {std_points:.2f} pts")
            print(f"      Custom scoring (6pt pass TD): {custom_points:.2f} pts")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Check roster data (for positional eligibility)
    print("\n📊 Test 4: Fetching roster/player info...")
    try:
        rosters = nfl.import_rosters([2024])
        print(f"   ✅ Loaded {len(rosters)} players from rosters")

        # Show position distribution
        position_counts = rosters['position'].value_counts().head(10)
        print(f"   Top positions: {dict(position_counts)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n✅ NFL Data Integration Test Complete!")


if __name__ == "__main__":
    main()
