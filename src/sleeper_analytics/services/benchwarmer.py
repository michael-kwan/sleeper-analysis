"""
Benchwarmer Analysis Service

Identifies players who scored high points while sitting on the bench.
"""

import asyncio
from typing import Any

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.benchwarmer import (
    BenchwarmerReport,
    BenchwarmerWeek,
    LeagueBenchwarmerReport,
)


class BenchwarmerService:
    """
    Service for analyzing bench performance.

    Identifies high-scoring players left on the bench and worst start/sit decisions.
    """

    # Position eligibility for starting slots
    POSITION_ELIGIBILITY = {
        "QB": ["QB", "SUPER_FLEX"],
        "RB": ["RB", "FLEX", "SUPER_FLEX", "REC_FLEX"],
        "WR": ["WR", "FLEX", "SUPER_FLEX", "REC_FLEX"],
        "TE": ["TE", "FLEX", "SUPER_FLEX", "REC_FLEX"],
        "K": ["K"],
        "DEF": ["DEF"],
    }

    def __init__(self, client: SleeperClient, context: LeagueContext):
        self.client = client
        self.ctx = context

    def _can_player_start(self, position: str) -> bool:
        """Check if a player in this position could potentially start."""
        roster_positions = self.ctx.league.roster_positions
        if not roster_positions:
            return False

        eligible_slots = self.POSITION_ELIGIBILITY.get(position, [])
        return any(slot in roster_positions for slot in eligible_slots)

    async def analyze_team_bench(
        self, roster_id: int, weeks: int = 17
    ) -> BenchwarmerReport:
        """
        Analyze bench performance for a specific team.

        Calculates the point differential between benched players and the starters
        they could have replaced. Only counts cases where benching was a mistake.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            BenchwarmerReport with top bench performances
        """
        # Fetch matchups for all weeks concurrently
        matchups_by_week = await self.client.get_matchups_range(
            self.ctx.league_id, 1, weeks
        )

        all_benchwarmers: list[BenchwarmerWeek] = []
        total_opportunity_cost = 0.0  # Total points left on bench

        for week, matchups in matchups_by_week.items():
            # Find this team's matchup
            roster_matchup = None
            for m in matchups:
                if m.get("roster_id") == roster_id:
                    roster_matchup = m
                    break

            if not roster_matchup:
                continue

            starters = roster_matchup.get("starters") or []
            players = roster_matchup.get("players") or []
            players_points = roster_matchup.get("players_points") or {}
            roster_positions = self.ctx.league.roster_positions or []

            # Identify bench players
            bench_players = [p for p in players if p not in starters]

            # For each bench player, find the worst starter they could have replaced
            for player_id in bench_players:
                if not player_id:
                    continue

                bench_points = float(players_points.get(player_id) or 0)
                if bench_points <= 0:
                    continue

                position = self.ctx.get_player_position(player_id)
                eligible_slots = self.POSITION_ELIGIBILITY.get(position, [])

                # Find the worst-performing starter in an eligible slot
                worst_starter_points = float('inf')
                for idx, starter_id in enumerate(starters):
                    if idx >= len(roster_positions):
                        break

                    slot = roster_positions[idx]
                    if slot in eligible_slots and starter_id:
                        starter_points = float(players_points.get(starter_id) or 0)
                        worst_starter_points = min(worst_starter_points, starter_points)

                # Calculate differential (opportunity cost)
                if worst_starter_points != float('inf'):
                    differential = bench_points - worst_starter_points

                    # Only count if benching was a mistake (positive differential)
                    if differential > 0:
                        total_opportunity_cost += differential

                        all_benchwarmers.append(
                            BenchwarmerWeek(
                                week=week,
                                player_id=player_id,
                                player_name=self.ctx.get_player_name(player_id),
                                position=position,
                                points=differential,  # Store differential, not raw points
                                roster_id=roster_id,
                                team_name=self.ctx.get_team_name(roster_id),
                                was_benched=True,
                                could_have_started=True,
                            )
                        )

        # Sort by differential to get worst decisions
        all_benchwarmers.sort(key=lambda x: x.points, reverse=True)

        # Top 10 bench performances
        top_benchwarmers = all_benchwarmers[:10]

        # Worst benching decision = highest differential
        worst_decision = all_benchwarmers[0] if all_benchwarmers else None

        return BenchwarmerReport(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            total_bench_points=round(total_opportunity_cost, 2),
            total_weeks_analyzed=weeks,
            top_benchwarmers=top_benchwarmers,
            worst_benching_decision=worst_decision,
            avg_bench_points_per_week=round(total_opportunity_cost / weeks, 2) if weeks > 0 else 0.0,
        )

    async def get_league_benchwarmer_report(
        self, weeks: int = 17
    ) -> LeagueBenchwarmerReport:
        """
        Get league-wide benchwarmer analysis.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            LeagueBenchwarmerReport with all teams
        """
        # Analyze all teams concurrently
        tasks = [
            self.analyze_team_bench(roster.roster_id, weeks)
            for roster in self.ctx.rosters
        ]
        all_team_reports = await asyncio.gather(*tasks)

        # Find benchwarmer champion (most points on bench)
        benchwarmer_champ = max(all_team_reports, key=lambda x: x.total_bench_points)

        # Collect all benchwarmers across league
        all_benchwarmers: list[BenchwarmerWeek] = []
        for report in all_team_reports:
            all_benchwarmers.extend(report.top_benchwarmers)

        # Sort to get biggest mistakes
        all_benchwarmers.sort(key=lambda x: x.points, reverse=True)
        biggest_mistakes = all_benchwarmers[:20]  # Top 20 league-wide

        return LeagueBenchwarmerReport(
            league_id=self.ctx.league_id,
            league_name=self.ctx.league_name,
            weeks_analyzed=weeks,
            all_teams=all_team_reports,
            biggest_benching_mistakes=biggest_mistakes,
            benchwarmer_champion=benchwarmer_champ.team_name,
            benchwarmer_champion_points=benchwarmer_champ.total_bench_points,
        )
