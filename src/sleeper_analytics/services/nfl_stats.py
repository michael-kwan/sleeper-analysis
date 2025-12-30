"""
NFL Stats Service

Uses nfl_data_py (nflreadpy) to fetch real NFL player statistics
for enhanced analysis and trade value calculations.
"""

from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from sleeper_analytics.models.player import PlayerValue


class NFLStatsService:
    """
    Service for fetching and analyzing NFL player statistics using nfl_data_py.

    Provides methods to:
    - Fetch weekly/seasonal player stats
    - Calculate player trade values
    - Get position rankings
    - Analyze player efficiency
    """

    def __init__(self, season: int = 2024):
        self.season = season
        self._weekly_stats: pd.DataFrame | None = None
        self._seasonal_stats: pd.DataFrame | None = None
        self._rosters: pd.DataFrame | None = None

    def _import_nfl_data(self):
        """Lazy import of nfl_data_py to avoid startup overhead."""
        import nfl_data_py as nfl
        return nfl

    @property
    def weekly_stats(self) -> pd.DataFrame:
        """Get weekly player stats (cached)."""
        if self._weekly_stats is None:
            try:
                nfl = self._import_nfl_data()
                self._weekly_stats = nfl.import_weekly_data([self.season])
            except Exception as e:
                print(f"Error fetching weekly stats: {e}")
                self._weekly_stats = pd.DataFrame()
        return self._weekly_stats

    @property
    def seasonal_stats(self) -> pd.DataFrame:
        """Get aggregated seasonal stats (cached)."""
        if self._seasonal_stats is None:
            try:
                nfl = self._import_nfl_data()
                self._seasonal_stats = nfl.import_seasonal_data([self.season])
            except Exception as e:
                print(f"Error fetching seasonal stats: {e}")
                self._seasonal_stats = pd.DataFrame()
        return self._seasonal_stats

    def get_weekly_stats(self, weeks: list[int] | None = None) -> pd.DataFrame:
        """
        Get weekly player stats for the season.

        Args:
            weeks: Optional list of specific weeks to filter

        Returns:
            DataFrame with weekly stats
        """
        df = self.weekly_stats
        if df.empty:
            return df

        if weeks:
            return df[df["week"].isin(weeks)].copy()
        return df.copy()

    def get_player_weekly_points(
        self, player_name: str, scoring: str = "ppr"
    ) -> pd.DataFrame:
        """
        Get weekly fantasy points for a specific player.

        Args:
            player_name: Player's full name
            scoring: 'ppr', 'half_ppr', or 'standard'

        Returns:
            DataFrame with weekly points
        """
        df = self.weekly_stats
        if df.empty:
            return pd.DataFrame()

        # Try exact match first
        player_data = df[
            df["player_display_name"].str.lower() == player_name.lower()
        ].copy()

        # Fall back to contains match
        if player_data.empty:
            player_data = df[
                df["player_display_name"].str.contains(
                    player_name, case=False, na=False
                )
            ].copy()

        if player_data.empty:
            return pd.DataFrame()

        points_col = self._get_points_column(scoring)
        if points_col in player_data.columns:
            return player_data[
                ["week", "player_display_name", "position", points_col]
            ].rename(columns={points_col: "fantasy_points"})

        return player_data

    def _get_points_column(self, scoring: str) -> str:
        """Get the appropriate fantasy points column based on scoring type."""
        scoring_map = {
            "ppr": "fantasy_points_ppr",
            "half_ppr": "fantasy_points",
            "standard": "fantasy_points",
        }
        return scoring_map.get(scoring, "fantasy_points_ppr")

    def get_position_rankings(
        self,
        position: str,
        week: int | None = None,
        top_n: int = 30,
        scoring: str = "ppr",
    ) -> pd.DataFrame:
        """
        Get position rankings based on fantasy points.

        Args:
            position: QB, RB, WR, TE, K, DEF
            week: Specific week or None for season total
            top_n: Number of players to return
            scoring: Scoring type

        Returns:
            DataFrame with position rankings
        """
        df = self.weekly_stats
        if df.empty:
            return pd.DataFrame()

        points_col = self._get_points_column(scoring)
        pos_data = df[df["position"] == position.upper()].copy()

        if week:
            pos_data = pos_data[pos_data["week"] == week]
            pos_data = pos_data.sort_values(points_col, ascending=False)
            result = pos_data.head(top_n)[
                ["player_display_name", "recent_team", points_col, "week"]
            ].copy()
            result["rank"] = range(1, len(result) + 1)
            return result
        else:
            # Season totals
            season_totals = (
                pos_data.groupby(["player_display_name", "recent_team"])
                .agg({points_col: "sum", "week": "count"})
                .reset_index()
            )
            season_totals = season_totals.rename(columns={"week": "games_played"})
            season_totals["ppg"] = (
                season_totals[points_col] / season_totals["games_played"]
            )
            season_totals = season_totals.sort_values(points_col, ascending=False)
            result = season_totals.head(top_n).copy()
            result["rank"] = range(1, len(result) + 1)
            return result

    def calculate_player_value(
        self, player_name: str, position: str | None = None
    ) -> PlayerValue | dict[str, Any]:
        """
        Calculate a player's trade value based on their production.

        Args:
            player_name: Player's display name
            position: Player's position (optional, will be detected)

        Returns:
            PlayerValue model with value metrics
        """
        df = self.weekly_stats
        if df.empty:
            return {"error": "No stats available"}

        # Find player data
        player_data = df[
            df["player_display_name"].str.lower() == player_name.lower()
        ]

        if player_data.empty:
            player_data = df[
                df["player_display_name"].str.contains(
                    player_name, case=False, na=False
                )
            ]

        if player_data.empty:
            return {"error": f"Player {player_name} not found"}

        # Get position from data if not provided
        if position is None:
            position = player_data["position"].iloc[0]

        # Calculate metrics
        points = player_data["fantasy_points_ppr"]
        total_points = float(points.sum())
        games = len(points)
        ppg = total_points / games if games > 0 else 0
        consistency = float(points.std()) if games > 1 else 0

        # Get position rank
        pos_rankings = self.get_position_rankings(position, top_n=100)
        position_rank = 50  # Default

        if not pos_rankings.empty:
            rank_match = pos_rankings[
                pos_rankings["player_display_name"].str.lower() == player_name.lower()
            ]
            if not rank_match.empty:
                position_rank = int(rank_match["rank"].iloc[0])

        # Calculate value score
        position_weights = {
            "QB": 1.0,
            "RB": 1.2,
            "WR": 1.15,
            "TE": 0.9,
            "K": 0.5,
            "DEF": 0.5,
        }
        pos_weight = position_weights.get(position.upper(), 1.0)

        raw_value = (
            (ppg * 3) + (total_points / 10) - (position_rank * 0.5) - (consistency * 0.3)
        )
        value_score = max(0, min(100, (raw_value * pos_weight) + 30))

        return PlayerValue(
            player_id=player_data["player_id"].iloc[0] if "player_id" in player_data.columns else player_name,
            player_name=player_name,
            position=position,
            total_points=round(total_points, 2),
            games_played=games,
            ppg=round(ppg, 2),
            position_rank=position_rank,
            consistency=round(consistency, 2),
            value_score=round(value_score, 1),
        )

    def get_player_efficiency(self, player_name: str) -> dict[str, Any]:
        """
        Calculate player efficiency metrics.

        Returns:
        - points_per_opportunity
        - target_share (for WR/TE)
        - rush_share (for RB)
        """
        df = self.weekly_stats
        if df.empty:
            return {"error": "No stats available"}

        player_data = df[
            df["player_display_name"].str.contains(player_name, case=False, na=False)
        ]

        if player_data.empty:
            return {"error": f"Player {player_name} not found"}

        position = player_data["position"].iloc[0]
        total_points = float(player_data["fantasy_points_ppr"].sum())

        # Calculate opportunities
        total_targets = (
            int(player_data["targets"].sum())
            if "targets" in player_data.columns
            else 0
        )
        total_carries = (
            int(player_data["carries"].sum())
            if "carries" in player_data.columns
            else 0
        )
        total_opportunities = total_targets + total_carries

        efficiency: dict[str, Any] = {
            "player_name": player_name,
            "position": position,
            "total_points": round(total_points, 2),
            "total_opportunities": total_opportunities,
            "points_per_opportunity": (
                round(total_points / total_opportunities, 3)
                if total_opportunities > 0
                else 0
            ),
        }

        if position in ["WR", "TE"]:
            if "target_share" in player_data.columns:
                efficiency["avg_target_share"] = round(
                    float(player_data["target_share"].mean()) * 100, 1
                )
            efficiency["total_targets"] = total_targets

        if position == "RB":
            efficiency["total_carries"] = total_carries
            if "rushing_yards" in player_data.columns and total_carries > 0:
                rushing_yards = float(player_data["rushing_yards"].sum())
                efficiency["yards_per_carry"] = round(rushing_yards / total_carries, 2)

        return efficiency

    def compare_players(self, player1: str, player2: str) -> pd.DataFrame:
        """Compare two players' stats side by side."""
        df = self.weekly_stats
        if df.empty:
            return pd.DataFrame()

        p1_data = df[
            df["player_display_name"].str.contains(player1, case=False, na=False)
        ]
        p2_data = df[
            df["player_display_name"].str.contains(player2, case=False, na=False)
        ]

        if p1_data.empty or p2_data.empty:
            return pd.DataFrame()

        stats_cols = [
            "fantasy_points_ppr",
            "targets",
            "receptions",
            "receiving_yards",
            "receiving_tds",
            "carries",
            "rushing_yards",
            "rushing_tds",
        ]

        comparison = []
        for name, data in [(player1, p1_data), (player2, p2_data)]:
            row: dict[str, Any] = {"player": name}
            for col in stats_cols:
                if col in data.columns:
                    row[col] = float(data[col].sum())
            row["games"] = len(data)
            comparison.append(row)

        return pd.DataFrame(comparison)


class TradeValueCalculator:
    """Calculates trade values for players and draft picks."""

    # Dynasty/keeper draft pick values (1-12 picks per round)
    PICK_VALUES: dict[int, dict[int, float]] = {
        1: {1: 100, 2: 95, 3: 90, 4: 85, 5: 80, 6: 75, 7: 70, 8: 65, 9: 60, 10: 55, 11: 50, 12: 45},
        2: {1: 40, 2: 38, 3: 36, 4: 34, 5: 32, 6: 30, 7: 28, 8: 26, 9: 24, 10: 22, 11: 20, 12: 18},
        3: {1: 15, 2: 14, 3: 13, 4: 12, 5: 11, 6: 10, 7: 9, 8: 8, 9: 7, 10: 6, 11: 5, 12: 4},
        4: {1: 3, 2: 3, 3: 2, 4: 2, 5: 2, 6: 2, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1},
    }

    def __init__(self, nfl_stats: NFLStatsService):
        self.nfl_stats = nfl_stats

    def get_player_trade_value(self, player_name: str, position: str | None = None) -> float:
        """Get a player's trade value score."""
        value_data = self.nfl_stats.calculate_player_value(player_name, position)

        if isinstance(value_data, dict) and "error" in value_data:
            return 0.0

        if isinstance(value_data, PlayerValue):
            return value_data.value_score

        return 0.0

    def get_pick_value(self, round_num: int, pick_num: int = 6) -> float:
        """
        Get draft pick trade value.

        Args:
            round_num: Draft round (1-4)
            pick_num: Pick number within round (1-12)

        Returns:
            Trade value for the pick
        """
        if round_num in self.PICK_VALUES:
            pick_num = min(max(pick_num, 1), 12)
            return self.PICK_VALUES[round_num].get(pick_num, 1.0)
        return 0.5

    def evaluate_trade(
        self,
        team_a_players: list[tuple[str, str]],
        team_a_picks: list[tuple[int, int]],
        team_b_players: list[tuple[str, str]],
        team_b_picks: list[tuple[int, int]],
    ) -> dict[str, Any]:
        """
        Evaluate a trade between two teams.

        Args:
            team_a_players: List of (player_name, position) tuples Team A receives
            team_a_picks: List of (round, pick) tuples Team A receives
            team_b_players: List of (player_name, position) tuples Team B receives
            team_b_picks: List of (round, pick) tuples Team B receives

        Returns:
            Trade evaluation with values and winner
        """
        # Calculate Team A's received value
        team_a_value = 0.0
        team_a_breakdown = []

        for player, pos in team_a_players:
            value = self.get_player_trade_value(player, pos)
            team_a_value += value
            team_a_breakdown.append({"player": player, "position": pos, "value": round(value, 1)})

        for round_num, pick_num in team_a_picks:
            value = self.get_pick_value(round_num, pick_num)
            team_a_value += value
            team_a_breakdown.append(
                {"pick": f"Round {round_num}, Pick {pick_num}", "value": value}
            )

        # Calculate Team B's received value
        team_b_value = 0.0
        team_b_breakdown = []

        for player, pos in team_b_players:
            value = self.get_player_trade_value(player, pos)
            team_b_value += value
            team_b_breakdown.append({"player": player, "position": pos, "value": round(value, 1)})

        for round_num, pick_num in team_b_picks:
            value = self.get_pick_value(round_num, pick_num)
            team_b_value += value
            team_b_breakdown.append(
                {"pick": f"Round {round_num}, Pick {pick_num}", "value": value}
            )

        # Determine fairness
        difference = abs(team_a_value - team_b_value)
        if difference < 5:
            fairness = "Fair"
        elif difference < 15:
            fairness = "Slightly Uneven"
        elif difference < 30:
            fairness = "Uneven"
        else:
            fairness = "Lopsided"

        # Determine winner
        winner = None
        if team_a_value > team_b_value + 5:
            winner = "Team A"
        elif team_b_value > team_a_value + 5:
            winner = "Team B"

        return {
            "team_a_value": round(team_a_value, 1),
            "team_a_breakdown": team_a_breakdown,
            "team_b_value": round(team_b_value, 1),
            "team_b_breakdown": team_b_breakdown,
            "difference": round(difference, 1),
            "fairness": fairness,
            "winner": winner,
        }


@lru_cache(maxsize=4)
def get_nfl_stats_service(season: int = 2024) -> NFLStatsService:
    """Get a cached NFLStatsService instance for the given season."""
    return NFLStatsService(season=season)
