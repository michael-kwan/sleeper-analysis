"""
Roster Construction Analysis Service

Analyzes where each team's points came from (draft, trades, waivers, FA).
"""

import asyncio
from collections import defaultdict

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.roster_construction import (
    AcquisitionMethod,
    LeagueRosterConstructionReport,
    PlayerAcquisition,
    RosterConstructionBreakdown,
    TeamRosterConstruction,
)


class RosterConstructionService:
    """
    Service for analyzing roster construction.

    Tracks player acquisition methods and calculates point contributions.
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

    async def analyze_team_roster_construction(
        self, roster_id: int, weeks: int = 17
    ) -> TeamRosterConstruction:
        """
        Analyze roster construction for a specific team.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            TeamRosterConstruction with acquisition breakdown
        """
        # Get all transactions
        all_transactions = await self.client.get_all_transactions(
            self.ctx.league_id, weeks
        )

        # Track player acquisitions and ownership periods
        player_acquisitions: dict[str, dict] = {}

        # First, identify all players ever owned by this team
        for txn in all_transactions:
            if not txn.adds:
                continue

            for player_id, acquiring_roster in txn.adds.items():
                if acquiring_roster == roster_id:
                    # Determine acquisition method
                    if txn.is_trade:
                        method = AcquisitionMethod.TRADE
                    elif txn.is_waiver:
                        method = AcquisitionMethod.WAIVER
                    else:
                        method = AcquisitionMethod.FREE_AGENT

                    player_acquisitions[player_id] = {
                        "method": method,
                        "week": txn.week,
                        "start_week": txn.week,
                        "end_week": weeks,  # Assume still owned until proven otherwise
                    }

            # Check if player was dropped
            if txn.drops:
                for player_id, dropping_roster in txn.drops.items():
                    if dropping_roster == roster_id and player_id in player_acquisitions:
                        player_acquisitions[player_id]["end_week"] = txn.week - 1

        # Get current roster to identify drafted players
        current_roster = next(
            (r for r in self.ctx.rosters if r.roster_id == roster_id), None
        )

        if current_roster:
            # Players currently on roster that we haven't seen in transactions are drafted
            for player_id in current_roster.players:
                if player_id not in player_acquisitions:
                    player_acquisitions[player_id] = {
                        "method": AcquisitionMethod.DRAFT,
                        "week": 0,
                        "start_week": 1,
                        "end_week": weeks,
                    }

        # Calculate points for each acquisition
        acquisitions: list[PlayerAcquisition] = []

        for player_id, acq_info in player_acquisitions.items():
            # Get player points by week
            points_by_week = await self._get_player_points_by_week(player_id, weeks)

            # Sum points during ownership period
            total_points = sum(
                points_by_week.get(w, 0)
                for w in range(acq_info["start_week"], acq_info["end_week"] + 1)
            )

            weeks_owned = acq_info["end_week"] - acq_info["start_week"] + 1
            is_currently_owned = acq_info["end_week"] == weeks

            acquisitions.append(
                PlayerAcquisition(
                    player_id=player_id,
                    player_name=self.ctx.get_player_name(player_id),
                    position=self.ctx.get_player_position(player_id),
                    acquisition_method=acq_info["method"],
                    acquisition_week=acq_info["week"],
                    points_scored=round(total_points, 2),
                    weeks_owned=weeks_owned,
                    is_currently_owned=is_currently_owned,
                )
            )

        # Calculate breakdown by method
        draft_points = sum(
            a.points_scored for a in acquisitions
            if a.acquisition_method == AcquisitionMethod.DRAFT
        )
        trade_points = sum(
            a.points_scored for a in acquisitions
            if a.acquisition_method == AcquisitionMethod.TRADE
        )
        waiver_points = sum(
            a.points_scored for a in acquisitions
            if a.acquisition_method == AcquisitionMethod.WAIVER
        )
        fa_points = sum(
            a.points_scored for a in acquisitions
            if a.acquisition_method == AcquisitionMethod.FREE_AGENT
        )

        total_points = draft_points + trade_points + waiver_points + fa_points

        # Calculate counts
        draft_count = len([a for a in acquisitions if a.acquisition_method == AcquisitionMethod.DRAFT])
        trade_count = len([a for a in acquisitions if a.acquisition_method == AcquisitionMethod.TRADE])
        waiver_count = len([a for a in acquisitions if a.acquisition_method == AcquisitionMethod.WAIVER])
        fa_count = len([a for a in acquisitions if a.acquisition_method == AcquisitionMethod.FREE_AGENT])

        breakdown = RosterConstructionBreakdown(
            draft_points=round(draft_points, 2),
            draft_percentage=round((draft_points / total_points * 100) if total_points > 0 else 0, 1),
            trade_points=round(trade_points, 2),
            trade_percentage=round((trade_points / total_points * 100) if total_points > 0 else 0, 1),
            waiver_points=round(waiver_points, 2),
            waiver_percentage=round((waiver_points / total_points * 100) if total_points > 0 else 0, 1),
            free_agent_points=round(fa_points, 2),
            free_agent_percentage=round((fa_points / total_points * 100) if total_points > 0 else 0, 1),
            total_points=round(total_points, 2),
            draft_count=draft_count,
            trade_count=trade_count,
            waiver_count=waiver_count,
            free_agent_count=fa_count,
        )

        # Determine primary source
        method_points = {
            AcquisitionMethod.DRAFT: draft_points,
            AcquisitionMethod.TRADE: trade_points,
            AcquisitionMethod.WAIVER: waiver_points,
            AcquisitionMethod.FREE_AGENT: fa_points,
        }
        primary_source = max(method_points, key=method_points.get)

        # Draft reliance
        if breakdown.draft_percentage >= 70:
            draft_reliance = "High (draft-dependent)"
        elif breakdown.draft_percentage >= 50:
            draft_reliance = "Moderate (balanced)"
        else:
            draft_reliance = "Low (active manager)"

        # Waiver activity
        if waiver_count >= 15:
            waiver_activity = "Very High"
        elif waiver_count >= 10:
            waiver_activity = "High"
        elif waiver_count >= 5:
            waiver_activity = "Moderate"
        else:
            waiver_activity = "Low"

        return TeamRosterConstruction(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            breakdown=breakdown,
            acquisitions=acquisitions,
            primary_source=primary_source,
            draft_reliance=draft_reliance,
            waiver_activity=waiver_activity,
        )

    async def get_league_roster_construction_report(
        self, weeks: int = 17
    ) -> LeagueRosterConstructionReport:
        """
        Get league-wide roster construction analysis.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            LeagueRosterConstructionReport with all teams
        """
        # Analyze all teams concurrently
        tasks = [
            self.analyze_team_roster_construction(roster.roster_id, weeks)
            for roster in self.ctx.rosters
        ]
        all_teams = await asyncio.gather(*tasks)

        # Calculate league averages
        avg_draft_pct = sum(t.breakdown.draft_percentage for t in all_teams) / len(all_teams)
        avg_trade_pct = sum(t.breakdown.trade_percentage for t in all_teams) / len(all_teams)
        avg_waiver_pct = sum(t.breakdown.waiver_percentage for t in all_teams) / len(all_teams)
        avg_fa_pct = sum(t.breakdown.free_agent_percentage for t in all_teams) / len(all_teams)

        # Find champions
        best_drafter = max(all_teams, key=lambda t: t.breakdown.draft_percentage)
        most_active_trader = max(all_teams, key=lambda t: t.breakdown.trade_count)
        waiver_wire_king = max(all_teams, key=lambda t: t.breakdown.waiver_points)

        return LeagueRosterConstructionReport(
            league_id=self.ctx.league_id,
            league_name=self.ctx.league_name,
            weeks_analyzed=weeks,
            all_teams=all_teams,
            avg_draft_percentage=round(avg_draft_pct, 1),
            avg_trade_percentage=round(avg_trade_pct, 1),
            avg_waiver_percentage=round(avg_waiver_pct, 1),
            avg_free_agent_percentage=round(avg_fa_pct, 1),
            best_drafter=best_drafter.team_name,
            best_drafter_pct=best_drafter.breakdown.draft_percentage,
            most_active_trader=most_active_trader.team_name,
            most_active_trader_count=most_active_trader.breakdown.trade_count,
            waiver_wire_king=waiver_wire_king.team_name,
            waiver_wire_king_points=waiver_wire_king.breakdown.waiver_points,
        )
