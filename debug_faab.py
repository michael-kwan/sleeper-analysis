"""Debug script to inspect FAAB transaction data."""

import asyncio
import json

from sleeper_analytics.clients.sleeper import SleeperClient


async def debug_faab_transactions():
    """Fetch and inspect raw transaction data."""
    async with SleeperClient() as client:
        # Use actual league ID from fetch_leagues.py
        league_id = "1257152597513490432"  # 2025 league

        print("Fetching transactions for league:", league_id)

        # Fetch transactions for several weeks
        for week in range(1, 6):
            print(f"\n{'='*60}")
            print(f"Week {week} Transactions")
            print('='*60)

            transactions = await client.get_transactions(league_id, week)

            # Filter for waiver transactions
            waivers = [t for t in transactions if t.is_waiver]

            if not waivers:
                print(f"No waiver transactions in week {week}")
                continue

            for txn in waivers:
                print(f"\nTransaction ID: {txn.transaction_id}")
                print(f"Type: {txn.type}")
                print(f"Adds: {txn.adds}")
                print(f"Waiver Budget: {txn.waiver_budget}")
                print(f"Settings: {txn.settings}")
                print(f"Metadata: {txn.metadata}")

                # Check if settings has waiver_bid
                if txn.settings:
                    print(f"Settings keys: {txn.settings.keys()}")
                    if "waiver_bid" in txn.settings:
                        print(f"⚠️  FAAB bid found in settings: {txn.settings['waiver_bid']}")

                # Check waiver_budget list
                if txn.waiver_budget:
                    for wb in txn.waiver_budget:
                        print(f"  Waiver budget entry: sender={wb.sender}, receiver={wb.receiver}, amount={wb.amount}")
                else:
                    print("  ⚠️  waiver_budget is empty!")


if __name__ == "__main__":
    asyncio.run(debug_faab_transactions())
