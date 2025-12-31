"""
FAAB Analysis Service

Tracks player lifecycle and FAAB spending efficiency.
"""

import asyncio
from collections import defaultdict
from typing import Any

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.faab import (
    LeagueFAABReport,
    OwnerFAABPerformance,
    PlayerLifecycle,
    PlayerOwnershipPeriod,
)


class FAABService:
    """
    Service for analyzing FAAB spending and player lifecycle.

    Tracks player movement through waivers and free agency.
    """

    def __init__(self, client: SleeperClient, context: LeagueContext):
        self.client = client
        self.ctx = context

    async def _get_player_points_by_week(
        self, player_id: str, weeks: int = 17
    ) -> dict[int, float]:
        """Get points scored by a player each week."""
        matchups_by_week = await self.client.get_matchups_range(
            self.ctx.league_id, 1, weeks
        )

        points_by_week: dict[int, float] = {}

        for week, matchups in matchups_by_week.items():
            for matchup in matchups:
                players_points = matchup.get("players_points", {})
                if player_id in players_points:
                    points_by_week[week] = float(players_points[player_id])
                    break

        return points_by_week

    async def get_player_lifecycle(
        self, player_id: str, weeks: int = 17
    ) -> PlayerLifecycle:
        """
        Track a player's complete journey through the league.

        Args:
            player_id: Player ID
            weeks: Number of weeks to analyze

        Returns:
            PlayerLifecycle with all ownership periods
        """
        # Get all transactions
        all_transactions = await self.client.get_all_transactions(
            self.ctx.league_id, weeks
        )

        # Get player points by week
        points_by_week = await self._get_player_points_by_week(player_id, weeks)

        # Track ownership changes
        ownership_periods: list[dict[str, Any]] = []
        current_owner: int | None = None
        current_period_start: int | None = None
        faab_spent: int = 0

        for txn in sorted(all_transactions, key=lambda x: x.week):
            # Check if this player was added
            if txn.adds and player_id in txn.adds:
                new_owner = txn.adds[player_id]

                # Close previous ownership period if exists
                if current_owner is not None and current_period_start is not None:
                    ownership_periods.append({
                        "owner_roster_id": current_owner,
                        "start_week": current_period_start,
                        "end_week": txn.week - 1,
                        "faab_spent": faab_spent,
                    })

                # Start new ownership period
                current_owner = new_owner
                current_period_start = txn.week

                # Extract FAAB spent (if waiver AND successful)
                faab_spent = 0
                if txn.is_waiver and txn.settings:
                    # Only count SUCCESSFUL waiver claims
                    # Failed claims have metadata indicating failure
                    is_successful = True
                    if txn.metadata and txn.metadata.get('notes'):
                        notes = txn.metadata['notes'].lower()
                        if 'claimed by another' in notes or 'failed' in notes or 'too many' in notes:
                            is_successful = False

                    if is_successful:
                        # FAAB bid is stored in settings, not waiver_budget
                        faab_spent = txn.settings.get('waiver_bid', 0)

            # Check if this player was dropped
            elif txn.drops and player_id in txn.drops:
                dropping_owner = txn.drops[player_id]

                # Close ownership period
                if current_owner == dropping_owner and current_period_start is not None:
                    ownership_periods.append({
                        "owner_roster_id": current_owner,
                        "start_week": current_period_start,
                        "end_week": txn.week,
                        "faab_spent": faab_spent,
                    })
                    current_owner = None
                    current_period_start = None

        # Close final ownership period if still owned
        if current_owner is not None and current_period_start is not None:
            ownership_periods.append({
                "owner_roster_id": current_owner,
                "start_week": current_period_start,
                "end_week": weeks,
                "faab_spent": faab_spent,
            })

        # Convert to PlayerOwnershipPeriod objects
        ownership_objects: list[PlayerOwnershipPeriod] = []
        player_name = self.ctx.get_player_name(player_id)
        player_position = self.ctx.get_player_position(player_id)

        for period in ownership_periods:
            # Calculate points during ownership
            period_points = sum(
                points_by_week.get(w, 0)
                for w in range(period["start_week"], period["end_week"] + 1)
            )

            weeks_owned = period["end_week"] - period["start_week"] + 1
            ppw = period_points / weeks_owned if weeks_owned > 0 else 0

            # Calculate ROI
            if period["faab_spent"] > 0:
                roi = period_points / period["faab_spent"]
            else:
                roi = float('inf') if period_points > 0 else 0

            ownership_objects.append(
                PlayerOwnershipPeriod(
                    player_id=player_id,
                    player_name=player_name,
                    position=player_position,
                    owner_roster_id=period["owner_roster_id"],
                    owner_name=self.ctx.get_team_name(period["owner_roster_id"]),
                    acquired_week=period["start_week"],
                    dropped_week=period["end_week"] if period["end_week"] < weeks else None,
                    faab_spent=period["faab_spent"],
                    weeks_owned=weeks_owned,
                    points_during_ownership=round(period_points, 2),
                    points_per_week=round(ppw, 2),
                    roi=round(roi, 2) if roi != float('inf') else 999.99,
                )
            )

        # Determine best/worst ROI owners
        finite_roi_periods = [p for p in ownership_objects if p.roi < 999]
        best_owner = max(finite_roi_periods, key=lambda x: x.roi).owner_name if finite_roi_periods else "N/A"
        worst_owner = min(finite_roi_periods, key=lambda x: x.roi).owner_name if finite_roi_periods else None

        return PlayerLifecycle(
            player_id=player_id,
            player_name=player_name,
            position=player_position,
            ownership_history=ownership_objects,
            total_faab_spent=sum(p.faab_spent for p in ownership_objects),
            times_picked_up=len(ownership_objects),
            times_dropped=sum(1 for p in ownership_objects if p.dropped_week is not None),
            current_owner=ownership_objects[-1].owner_name if ownership_objects and ownership_objects[-1].dropped_week is None else None,
            best_roi_owner=best_owner,
            worst_roi_owner=worst_owner,
        )

    async def get_owner_faab_performance(
        self, roster_id: int, weeks: int = 17
    ) -> OwnerFAABPerformance:
        """
        Analyze FAAB efficiency for a specific owner.

        Args:
            roster_id: Owner's roster ID
            weeks: Number of weeks to analyze

        Returns:
            OwnerFAABPerformance with all metrics
        """
        # Get all transactions
        all_transactions = await self.client.get_all_transactions(
            self.ctx.league_id, weeks
        )

        # Track this owner's FAAB acquisitions
        acquisitions: list[dict[str, Any]] = []
        total_faab_spent = 0

        for txn in all_transactions:
            if not txn.adds:
                continue

            # Check if this owner acquired any players
            for player_id, acquiring_roster in txn.adds.items():
                if acquiring_roster == roster_id:
                    # Determine FAAB spent (only for SUCCESSFUL waivers)
                    faab = 0
                    if txn.is_waiver and txn.settings:
                        # Only count SUCCESSFUL waiver claims
                        is_successful = True
                        if txn.metadata and txn.metadata.get('notes'):
                            notes = txn.metadata['notes'].lower()
                            if 'claimed by another' in notes or 'failed' in notes or 'too many' in notes:
                                is_successful = False

                        if is_successful:
                            # FAAB bid is stored in settings, not waiver_budget
                            faab = txn.settings.get('waiver_bid', 0)

                    if faab > 0:  # Only track FAAB pickups, not free agents
                        acquisitions.append({
                            "player_id": player_id,
                            "week": txn.week,
                            "faab": faab,
                        })
                        total_faab_spent += faab

        # Get details for each acquisition using lifecycle
        acquisition_periods: list[PlayerOwnershipPeriod] = []

        for acq in acquisitions:
            lifecycle = await self.get_player_lifecycle(acq["player_id"], weeks)
            # Find the period that matches this acquisition
            for period in lifecycle.ownership_history:
                if (period.owner_roster_id == roster_id and
                    period.acquired_week == acq["week"]):
                    acquisition_periods.append(period)
                    break

        # Calculate metrics
        total_points = sum(p.points_during_ownership for p in acquisition_periods)
        avg_roi = (
            sum(p.roi for p in acquisition_periods if p.roi < 999) / len([p for p in acquisition_periods if p.roi < 999])
            if acquisition_periods and any(p.roi < 999 for p in acquisition_periods)
            else 0
        )

        # Find best and worst pickups
        finite_acquisitions = [p for p in acquisition_periods if p.roi < 999]
        best_pickup = max(finite_acquisitions, key=lambda x: x.roi) if finite_acquisitions else None
        worst_pickup = min(finite_acquisitions, key=lambda x: x.roi) if finite_acquisitions else None

        # Get FAAB remaining (assume 100 budget)
        faab_remaining = 100 - total_faab_spent

        return OwnerFAABPerformance(
            roster_id=roster_id,
            owner_name=self.ctx.get_team_name(roster_id),
            total_faab_spent=total_faab_spent,
            faab_remaining=faab_remaining,
            acquisitions=acquisition_periods,
            total_points_from_faab=round(total_points, 2),
            avg_roi=round(avg_roi, 2),
            best_pickup=best_pickup,
            worst_pickup=worst_pickup,
        )

    async def get_league_faab_report(
        self, weeks: int = 17
    ) -> LeagueFAABReport:
        """
        Get league-wide FAAB analysis.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            LeagueFAABReport with all teams
        """
        # Get FAAB performance for all owners
        tasks = [
            self.get_owner_faab_performance(roster.roster_id, weeks)
            for roster in self.ctx.rosters
        ]
        owner_performances = await asyncio.gather(*tasks)

        # Rank by average ROI
        owner_performances_list = list(owner_performances)
        owner_performances_list.sort(key=lambda x: x.avg_roi, reverse=True)

        # Set ranks
        for idx, perf in enumerate(owner_performances_list):
            perf.faab_efficiency_rank = idx + 1

        # Collect all pickups for league-wide analysis
        all_pickups: list[PlayerOwnershipPeriod] = []
        for perf in owner_performances:
            all_pickups.extend(perf.acquisitions)

        # Filter out infinite ROI for ranking
        finite_pickups = [p for p in all_pickups if p.roi < 999]

        # Best value pickups
        best_pickups = sorted(finite_pickups, key=lambda x: x.roi, reverse=True)[:20]

        # Worst value pickups (overpays)
        worst_pickups = sorted(finite_pickups, key=lambda x: x.roi)[:10]

        # Most transacted players (get top 10 by transaction count)
        all_transactions = await self.client.get_all_transactions(
            self.ctx.league_id, weeks
        )

        player_transaction_counts: dict[str, int] = defaultdict(int)
        for txn in all_transactions:
            if txn.adds:
                for player_id in txn.adds.keys():
                    player_transaction_counts[player_id] += 1

        most_transacted_player_ids = sorted(
            player_transaction_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Get lifecycles for most transacted players
        lifecycle_tasks = [
            self.get_player_lifecycle(pid, weeks)
            for pid, _ in most_transacted_player_ids
        ]
        most_transacted = await asyncio.gather(*lifecycle_tasks)

        return LeagueFAABReport(
            league_id=self.ctx.league_id,
            league_name=self.ctx.league_name,
            weeks_analyzed=weeks,
            total_faab_spent=sum(p.total_faab_spent for p in owner_performances),
            owner_rankings=owner_performances_list,
            best_value_pickups=best_pickups,
            worst_value_pickups=worst_pickups,
            most_transacted_players=most_transacted,
        )
