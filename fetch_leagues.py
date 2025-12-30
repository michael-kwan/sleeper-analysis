#!/usr/bin/env python3
"""Fetch league names and test 2025 league access."""

import asyncio
import json
import httpx


async def main():
    username = "michaelburps"
    league_ids = ["1257152597513490432", "1261570852047040512"]

    async with httpx.AsyncClient() as client:
        # Test 1: Can we fetch user's 2025 leagues?
        print(f"🔍 Testing user league fetch for 2025...")
        user_resp = await client.get(f"https://api.sleeper.app/v1/user/{username}")

        if user_resp.status_code != 200:
            print(f"❌ User not found: {user_resp.status_code}")
            return

        user = user_resp.json()
        user_id = user.get("user_id")
        print(f"✅ User ID: {user_id}")

        # Try to fetch 2025 leagues
        leagues_2025_resp = await client.get(
            f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/2025"
        )

        print(f"\n📋 Fetching 2025 leagues for user...")
        print(f"   Status code: {leagues_2025_resp.status_code}")

        if leagues_2025_resp.status_code == 200:
            leagues_2025 = leagues_2025_resp.json() or []
            print(f"   Found {len(leagues_2025)} leagues for 2025")
            for league in leagues_2025:
                print(f"   - {league.get('name')} ({league.get('league_id')})")
        else:
            print(f"   ❌ Could not fetch 2025 leagues")

        # Test 2: Fetch the specific league names
        print(f"\n📋 Fetching specific league details...")
        leagues_data = {"leagues": []}

        for league_id in league_ids:
            league_resp = await client.get(
                f"https://api.sleeper.app/v1/league/{league_id}"
            )

            if league_resp.status_code == 200:
                league = league_resp.json()
                league_name = league.get("name", "Unknown")
                print(f"✅ {league_id}: {league_name}")

                leagues_data["leagues"].append({
                    "id": league_id,
                    "name": league_name,
                    "season": 2025,
                    "notes": ""
                })
            else:
                print(f"❌ {league_id}: Not found (status {league_resp.status_code})")
                leagues_data["leagues"].append({
                    "id": league_id,
                    "name": "Unknown",
                    "season": 2025,
                    "notes": "Could not fetch league name"
                })

        # Save to leagues.json
        with open("leagues.json", "w") as f:
            json.dump(leagues_data, f, indent=2)

        print(f"\n✅ Updated leagues.json")


if __name__ == "__main__":
    asyncio.run(main())
