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
        total_bench_points = 0.0

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

            # Identify bench players
            bench_players = [p for p in players if p not in starters]

            for player_id in bench_players:
                if not player_id:
                    continue

                points = float(players_points.get(player_id) or 0)
                if points <= 0:
                    continue

                position = self.ctx.get_player_position(player_id)
                could_start = self._can_player_start(position)

                if could_start:
                    total_bench_points += points

                    all_benchwarmers.append(
                        BenchwarmerWeek(
                            week=week,
                            player_id=player_id,
                            player_name=self.ctx.get_player_name(player_id),
                            position=position,
                            points=points,
                            roster_id=roster_id,
                            team_name=self.ctx.get_team_name(roster_id),
                            was_benched=True,
                            could_have_started=could_start,
                        )
                    )

        # Sort by points to get top benchwarmers
        all_benchwarmers.sort(key=lambda x: x.points, reverse=True)

        # Top 10 bench performances
        top_benchwarmers = all_benchwarmers[:10]

        # Worst benching decision = highest single game on bench
        worst_decision = all_benchwarmers[0] if all_benchwarmers else None

        return BenchwarmerReport(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            total_bench_points=round(total_bench_points, 2),
            total_weeks_analyzed=weeks,
            top_benchwarmers=top_benchwarmers,
            worst_benching_decision=worst_decision,
            avg_bench_points_per_week=round(total_bench_points / weeks, 2) if weeks > 0 else 0.0,
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
