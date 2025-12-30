"""
Roster Efficiency Service

Analyzes how well teams utilize their rosters - comparing actual lineups
to optimal lineups and identifying missed opportunities.
"""

from collections import defaultdict
from typing import Any

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.matchup import EfficiencyReport, SeasonEfficiency


class EfficiencyService:
    """
    Service for analyzing roster efficiency.

    Provides methods to:
    - Calculate optimal vs actual lineup efficiency
    - Identify missed start/sit decisions
    - Rank teams by efficiency
    - Track bench points over time
    """

    def __init__(self, client: SleeperClient, context: LeagueContext):
        self.client = client
        self.ctx = context

    async def analyze_weekly_efficiency(
        self, roster_id: int, week: int
    ) -> EfficiencyReport:
        """
        Analyze roster efficiency for a specific week.

        Compares points scored vs potential points (optimal lineup).

        Args:
            roster_id: Team's roster ID
            week: Week number

        Returns:
            EfficiencyReport with detailed analysis
        """
        matchups = await self.client.get_matchups(self.ctx.league_id, week)

        # Find this team's matchup data
        roster_matchup = None
        for m in matchups:
            if m.get("roster_id") == roster_id:
                roster_matchup = m
                break

        if not roster_matchup:
            return EfficiencyReport(
                week=week,
                roster_id=roster_id,
                team_name=self.ctx.get_team_name(roster_id),
                points_scored=0,
                potential_points=0,
                efficiency_pct=0,
                bench_points=0,
                missed_opportunities=[],
            )

        starters = roster_matchup.get("starters") or []
        players = roster_matchup.get("players") or []
        players_points = roster_matchup.get("players_points") or {}
        points_scored = roster_matchup.get("points") or 0

        # Calculate bench points
        bench_players = [p for p in players if p not in starters]
        bench_points = sum(
            float(players_points.get(p) or 0) for p in bench_players
        )

        # Group players by position
        positions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for player_id in players:
            if player_id:
                pos = self.ctx.get_player_position(player_id)
                pts = float(players_points.get(player_id) or 0)
                positions[pos].append({
                    "player_id": player_id,
                    "name": self.ctx.get_player_name(player_id),
                    "points": pts,
                })

        # Sort each position by points
        for pos in positions:
            positions[pos].sort(key=lambda x: x["points"], reverse=True)

        # Calculate optimal lineup
        potential_points = self._calculate_optimal_lineup(positions)

        # Calculate efficiency
        efficiency_pct = (
            (points_scored / potential_points * 100) if potential_points > 0 else 0
        )

        # Find missed opportunities
        missed_opportunities = self._find_missed_opportunities(
            positions, starters
        )

        return EfficiencyReport(
            week=week,
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            points_scored=round(points_scored, 2),
            potential_points=round(potential_points, 2),
            efficiency_pct=round(efficiency_pct, 1),
            bench_points=round(bench_points, 2),
            missed_opportunities=missed_opportunities,
        )

    def _calculate_optimal_lineup(
        self, positions: dict[str, list[dict[str, Any]]]
    ) -> float:
        """Calculate optimal lineup points based on league roster positions."""
        roster_positions = self.ctx.league.roster_positions
        if not roster_positions:
            roster_positions = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF"]

        optimal_points = 0.0
        used_players: set[str] = set()

        for pos in roster_positions:
            if pos in ("BN", "IR"):
                continue

            if pos == "FLEX":
                # FLEX can be RB, WR, or TE
                flex_candidates = []
                for flex_pos in ["RB", "WR", "TE"]:
                    for p in positions.get(flex_pos, []):
                        if p["player_id"] not in used_players:
                            flex_candidates.append(p)
                flex_candidates.sort(key=lambda x: x["points"], reverse=True)
                if flex_candidates:
                    optimal_points += flex_candidates[0]["points"]
                    used_players.add(flex_candidates[0]["player_id"])

            elif pos == "SUPER_FLEX":
                # SUPER_FLEX can be QB, RB, WR, or TE
                sf_candidates = []
                for sf_pos in ["QB", "RB", "WR", "TE"]:
                    for p in positions.get(sf_pos, []):
                        if p["player_id"] not in used_players:
                            sf_candidates.append(p)
                sf_candidates.sort(key=lambda x: x["points"], reverse=True)
                if sf_candidates:
                    optimal_points += sf_candidates[0]["points"]
                    used_players.add(sf_candidates[0]["player_id"])

            elif pos == "REC_FLEX":
                # REC_FLEX can be WR or TE
                rf_candidates = []
                for rf_pos in ["WR", "TE"]:
                    for p in positions.get(rf_pos, []):
                        if p["player_id"] not in used_players:
                            rf_candidates.append(p)
                rf_candidates.sort(key=lambda x: x["points"], reverse=True)
                if rf_candidates:
                    optimal_points += rf_candidates[0]["points"]
                    used_players.add(rf_candidates[0]["player_id"])

            else:
                # Standard position
                pos_players = positions.get(pos, [])
                for p in pos_players:
                    if p["player_id"] not in used_players:
                        optimal_points += p["points"]
                        used_players.add(p["player_id"])
                        break

        return optimal_points

    def _find_missed_opportunities(
        self,
        positions: dict[str, list[dict[str, Any]]],
        starters: list[str],
    ) -> list[dict[str, Any]]:
        """Find players who should have been started over actual starters."""
        missed = []

        for pos, players_list in positions.items():
            if len(players_list) > 1:
                # Check if the highest scorer was benched
                best = players_list[0]
                if best["player_id"] not in starters:
                    # Find who was started at this position
                    started_player = next(
                        (p for p in players_list if p["player_id"] in starters),
                        None,
                    )
                    if started_player and started_player["points"] < best["points"]:
                        missed.append({
                            "position": pos,
                            "benched_player": best["name"],
                            "benched_points": round(best["points"], 2),
                            "started_player": started_player["name"],
                            "started_points": round(started_player["points"], 2),
                            "points_lost": round(
                                best["points"] - started_player["points"], 2
                            ),
                        })

        # Sort by points lost
        missed.sort(key=lambda x: x["points_lost"], reverse=True)
        return missed

    async def get_season_efficiency(
        self, roster_id: int, weeks: int = 17
    ) -> SeasonEfficiency:
        """
        Get efficiency metrics for the entire season.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to analyze

        Returns:
            SeasonEfficiency with aggregated metrics
        """
        weekly_efficiency: list[EfficiencyReport] = []
        total_scored = 0.0
        total_potential = 0.0
        total_missed = 0

        for week in range(1, weeks + 1):
            eff = await self.analyze_weekly_efficiency(roster_id, week)
            if eff.points_scored > 0:  # Only include weeks with data
                weekly_efficiency.append(eff)
                total_scored += eff.points_scored
                total_potential += eff.potential_points
                total_missed += len(eff.missed_opportunities)

        season_efficiency_pct = (
            (total_scored / total_potential * 100) if total_potential > 0 else 0
        )

        return SeasonEfficiency(
            roster_id=roster_id,
            team_name=self.ctx.get_team_name(roster_id),
            total_points_scored=round(total_scored, 2),
            total_potential_points=round(total_potential, 2),
            season_efficiency_pct=round(season_efficiency_pct, 1),
            points_left_on_bench=round(total_potential - total_scored, 2),
            weekly_efficiency=weekly_efficiency,
            total_missed_opportunities=total_missed,
        )

    async def get_league_efficiency_rankings(
        self, weeks: int = 17
    ) -> list[dict[str, Any]]:
        """
        Rank all teams by roster efficiency.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            List of teams ranked by efficiency percentage
        """
        rankings = []

        for roster in self.ctx.rosters:
            eff = await self.get_season_efficiency(roster.roster_id, weeks)
            rankings.append({
                "rank": 0,  # Will be set after sorting
                "roster_id": eff.roster_id,
                "team_name": eff.team_name,
                "efficiency_pct": eff.season_efficiency_pct,
                "points_scored": eff.total_points_scored,
                "potential_points": eff.total_potential_points,
                "points_left_on_bench": eff.points_left_on_bench,
                "missed_opportunities": eff.total_missed_opportunities,
            })

        # Sort by efficiency percentage descending
        rankings.sort(key=lambda x: x["efficiency_pct"], reverse=True)

        # Set ranks
        for i, team in enumerate(rankings):
            team["rank"] = i + 1

        return rankings

    async def get_biggest_missed_starts(
        self, weeks: int = 17, top_n: int = 10
    ) -> list[dict[str, Any]]:
        """
        Find the biggest missed start/sit decisions across the league.

        Args:
            weeks: Number of weeks to analyze
            top_n: Number of results to return

        Returns:
            List of the biggest missed opportunities
        """
        all_missed = []

        for roster in self.ctx.rosters:
            for week in range(1, weeks + 1):
                eff = await self.analyze_weekly_efficiency(roster.roster_id, week)
                for opp in eff.missed_opportunities:
                    all_missed.append({
                        "week": week,
                        "team": eff.team_name,
                        **opp,
                    })

        # Sort by points lost
        all_missed.sort(key=lambda x: x["points_lost"], reverse=True)

        return all_missed[:top_n]
