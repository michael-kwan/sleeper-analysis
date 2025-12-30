#!/usr/bin/env python3
"""Quick test script to fetch user and leagues from Sleeper."""

import asyncio
import httpx


async def main():
    username = "michaelburps"

    async with httpx.AsyncClient() as client:
        # Fetch user
        print(f"🔍 Looking up user: {username}")
        user_resp = await client.get(f"https://api.sleeper.app/v1/user/{username}")

        if user_resp.status_code != 200:
            print(f"❌ User not found: {user_resp.status_code}")
            return

        user = user_resp.json()
        print(f"✅ Found user: {user.get('display_name', username)}")
        print(f"   User ID: {user.get('user_id')}")
        print(f"   Avatar: {user.get('avatar')}")

        user_id = user.get("user_id")

        # Fetch leagues for 2024
        print(f"\n📋 Fetching 2024 leagues...")
        leagues_resp = await client.get(
            f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/2024"
        )

        if leagues_resp.status_code != 200:
            print(f"❌ Could not fetch leagues: {leagues_resp.status_code}")
            return

        leagues = leagues_resp.json()

        if not leagues:
            print("No leagues found for 2024. Trying 2023...")
            leagues_resp = await client.get(
                f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/2023"
            )
            leagues = leagues_resp.json() or []

        print(f"✅ Found {len(leagues)} league(s):\n")

        for i, league in enumerate(leagues, 1):
            print(f"  {i}. {league.get('name')}")
            print(f"     League ID: {league.get('league_id')}")
            print(f"     Season: {league.get('season')}")
            print(f"     Teams: {league.get('total_rosters')}")
            print(f"     Status: {league.get('status')}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
