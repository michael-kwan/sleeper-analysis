"""
Transaction and Trade Analysis Service

Analyzes trades, waivers, and free agent moves with value calculations
to determine trade fairness and identify transaction patterns.
"""

from collections import defaultdict
from typing import Any

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.transaction import (
    TradeAnalysis,
    TradeAsset,
    TradeFairness,
    TradeSide,
    Transaction,
    TransactionSummary,
    TransactionType,
)
from sleeper_analytics.services.nfl_stats import NFLStatsService, TradeValueCalculator


class TransactionService:
    """
    Service for analyzing transactions including trades, waivers, and FA moves.

    Provides methods to:
    - Get and filter transactions
    - Analyze trade values and fairness
    - Track transaction activity by team
    - Identify best waiver pickups
    """

    def __init__(
        self,
        client: SleeperClient,
        context: LeagueContext,
        nfl_stats: NFLStatsService,
    ):
        self.client = client
        self.ctx = context
        self.nfl_stats = nfl_stats
        self.trade_calc = TradeValueCalculator(nfl_stats)

    async def get_all_transactions(self, weeks: int = 18) -> list[Transaction]:
        """
        Get all transactions for the season.

        Args:
            weeks: Number of weeks to fetch

        Returns:
            List of Transaction objects
        """
        return await self.client.get_all_transactions(self.ctx.league_id, weeks)

    async def get_transactions_by_type(
        self, txn_type: TransactionType, weeks: int = 18
    ) -> list[Transaction]:
        """
        Get transactions filtered by type.

        Args:
            txn_type: Type of transaction to filter
            weeks: Number of weeks to fetch

        Returns:
            List of filtered Transaction objects
        """
        all_txns = await self.get_all_transactions(weeks)
        return [t for t in all_txns if t.type == txn_type]

    async def get_team_transactions(
        self, roster_id: int, weeks: int = 18
    ) -> list[Transaction]:
        """
        Get transactions for a specific team.

        Args:
            roster_id: Team's roster ID
            weeks: Number of weeks to fetch

        Returns:
            List of Transaction objects involving this team
        """
        all_txns = await self.get_all_transactions(weeks)
        return [t for t in all_txns if roster_id in t.roster_ids]

    async def get_transaction_summary(self, weeks: int = 18) -> TransactionSummary:
        """
        Get summary statistics for all transactions.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            TransactionSummary with aggregated stats
        """
        all_txns = await self.get_all_transactions(weeks)

        by_type: dict[str, int] = defaultdict(int)
        by_week: dict[int, int] = defaultdict(int)
        by_team: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for txn in all_txns:
            by_type[txn.type.value] += 1
            by_week[txn.week] += 1

            for roster_id in txn.roster_ids:
                team_name = self.ctx.get_team_name(roster_id)
                by_team[team_name][txn.type.value] += 1

        return TransactionSummary(
            total=len(all_txns),
            by_type=dict(by_type),
            by_week=dict(by_week),
            by_team={k: dict(v) for k, v in by_team.items()},
        )

    async def analyze_trades(self, weeks: int = 18) -> list[TradeAnalysis]:
        """
        Analyze all trades in the league with value calculations.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            List of TradeAnalysis objects
        """
        trades = await self.get_transactions_by_type(TransactionType.TRADE, weeks)

        analyses = []
        for trade in trades:
            analysis = await self._analyze_single_trade(trade)
            if analysis:
                analyses.append(analysis)

        return analyses

    async def _analyze_single_trade(
        self, trade: Transaction
    ) -> TradeAnalysis | None:
        """
        Analyze a single trade for value balance.

        Args:
            trade: Transaction object to analyze

        Returns:
            TradeAnalysis or None if invalid
        """
        if len(trade.roster_ids) < 2:
            return None

        adds = trade.adds or {}
        draft_picks = trade.draft_picks

        # Group assets by receiving roster
        team_assets: dict[int, dict[str, list]] = defaultdict(
            lambda: {"players": [], "picks": []}
        )

        # Players added to each roster
        for player_id, roster_id in adds.items():
            player_name = self.ctx.get_player_name(player_id)
            position = self.ctx.get_player_position(player_id)
            team_assets[roster_id]["players"].append({
                "player_id": player_id,
                "name": player_name,
                "position": position,
            })

        # Draft picks transferred
        for pick in draft_picks:
            team_assets[pick.owner_id]["picks"].append({
                "round": pick.round,
                "season": pick.season,
            })

        # Build trade sides
        sides: list[TradeSide] = []
        for roster_id in trade.roster_ids:
            assets = team_assets[roster_id]
            total_value = 0.0

            trade_assets: list[TradeAsset] = []

            # Value players
            for player in assets["players"]:
                value = self._estimate_player_value(
                    player["name"], player["position"]
                )
                total_value += value
                trade_assets.append(
                    TradeAsset(
                        asset_type="player",
                        player_id=player["player_id"],
                        player_name=player["name"],
                        position=player["position"],
                        value=round(value, 1),
                    )
                )

            # Value picks
            for pick in assets["picks"]:
                value = self.trade_calc.get_pick_value(pick["round"], 6)
                total_value += value
                trade_assets.append(
                    TradeAsset(
                        asset_type="pick",
                        pick_round=pick["round"],
                        pick_season=pick["season"],
                        value=value,
                    )
                )

            sides.append(
                TradeSide(
                    roster_id=roster_id,
                    team_name=self.ctx.get_team_name(roster_id),
                    assets_received=trade_assets,
                    total_value=round(total_value, 1),
                )
            )

        # Calculate fairness
        if len(sides) >= 2:
            diff = abs(sides[0].total_value - sides[1].total_value)

            if diff < 10:
                fairness = TradeFairness.FAIR
            elif diff < 25:
                fairness = TradeFairness.SLIGHTLY_UNEVEN
            elif diff < 50:
                fairness = TradeFairness.UNEVEN
            else:
                fairness = TradeFairness.LOPSIDED

            # Determine winner
            if sides[0].total_value > sides[1].total_value + 5:
                winner = sides[0].team_name
            elif sides[1].total_value > sides[0].total_value + 5:
                winner = sides[1].team_name
            else:
                winner = None
        else:
            diff = 0
            fairness = TradeFairness.FAIR
            winner = None

        return TradeAnalysis(
            transaction_id=trade.transaction_id,
            week=trade.week,
            sides=sides,
            value_difference=round(diff, 1),
            fairness=fairness,
            winner=winner,
        )

    def _estimate_player_value(
        self, player_name: str, position: str | None = None
    ) -> float:
        """
        Estimate a player's trade value using NFL stats.

        Args:
            player_name: Player's display name
            position: Player's position

        Returns:
            Trade value score
        """
        value_data = self.nfl_stats.calculate_player_value(player_name, position)

        if isinstance(value_data, dict):
            if "error" in value_data:
                return 20.0  # Default value for unknown players
            return value_data.get("value_score", 20.0)

        # It's a PlayerValue object
        return value_data.value_score

    async def get_trade_winners_losers(
        self, weeks: int = 18
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Identify teams that have won and lost the most in trades.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Dict with 'winners' and 'losers' lists
        """
        analyses = await self.analyze_trades(weeks)

        team_balance: dict[str, float] = defaultdict(float)

        for analysis in analyses:
            if len(analysis.sides) == 2:
                diff = analysis.sides[0].total_value - analysis.sides[1].total_value
                team_balance[analysis.sides[0].team_name] += diff
                team_balance[analysis.sides[1].team_name] -= diff

        # Sort and categorize
        sorted_teams = sorted(
            team_balance.items(), key=lambda x: x[1], reverse=True
        )

        winners = [
            {"team": t, "net_value": round(v, 1)}
            for t, v in sorted_teams
            if v > 0
        ]

        losers = [
            {"team": t, "net_value": round(v, 1)}
            for t, v in sorted_teams
            if v < 0
        ]

        return {"winners": winners, "losers": losers}

    async def get_waiver_analysis(
        self, weeks: int = 18, top_n: int = 20
    ) -> list[dict[str, Any]]:
        """
        Analyze waiver wire pickups and rank by value.

        Args:
            weeks: Number of weeks to analyze
            top_n: Number of top pickups to return

        Returns:
            List of best waiver pickups sorted by value
        """
        waivers = await self.get_transactions_by_type(TransactionType.WAIVER, weeks)

        pickups = []
        for w in waivers:
            adds = w.adds or {}
            for player_id, roster_id in adds.items():
                player_name = self.ctx.get_player_name(player_id)
                position = self.ctx.get_player_position(player_id)
                value = self._estimate_player_value(player_name, position)

                pickups.append({
                    "week": w.week,
                    "team": self.ctx.get_team_name(roster_id),
                    "player": player_name,
                    "position": position,
                    "value": round(value, 1),
                })

        # Sort by value
        pickups.sort(key=lambda x: x["value"], reverse=True)

        return pickups[:top_n]

    async def get_most_active_teams(self, weeks: int = 18) -> list[dict[str, Any]]:
        """
        Rank teams by transaction activity.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            List of teams sorted by total transactions
        """
        summary = await self.get_transaction_summary(weeks)

        activity = []
        for team, counts in summary.by_team.items():
            total = sum(counts.values())
            activity.append({
                "team": team,
                "total_transactions": total,
                "trades": counts.get("trade", 0),
                "waivers": counts.get("waiver", 0),
                "free_agent": counts.get("free_agent", 0),
            })

        activity.sort(key=lambda x: x["total_transactions"], reverse=True)
        return activity

    async def evaluate_hypothetical_trade(
        self,
        team_a_roster_id: int,
        team_a_player_ids: list[str],
        team_a_picks: list[tuple[int, int]],
        team_b_roster_id: int,
        team_b_player_ids: list[str],
        team_b_picks: list[tuple[int, int]],
    ) -> dict[str, Any]:
        """
        Evaluate a hypothetical trade between two teams.

        Args:
            team_a_roster_id: Team A's roster ID
            team_a_player_ids: Player IDs Team A would receive
            team_a_picks: (round, pick) tuples Team A would receive
            team_b_roster_id: Team B's roster ID
            team_b_player_ids: Player IDs Team B would receive
            team_b_picks: (round, pick) tuples Team B would receive

        Returns:
            Trade evaluation with values and recommendation
        """
        team_a_name = self.ctx.get_team_name(team_a_roster_id)
        team_b_name = self.ctx.get_team_name(team_b_roster_id)

        # Calculate Team A's received value
        team_a_value = 0.0
        team_a_assets = []

        for player_id in team_a_player_ids:
            player_name = self.ctx.get_player_name(player_id)
            position = self.ctx.get_player_position(player_id)
            value = self._estimate_player_value(player_name, position)
            team_a_value += value
            team_a_assets.append({
                "player": player_name,
                "position": position,
                "value": round(value, 1),
            })

        for round_num, pick_num in team_a_picks:
            value = self.trade_calc.get_pick_value(round_num, pick_num)
            team_a_value += value
            team_a_assets.append({
                "pick": f"Round {round_num}, Pick {pick_num}",
                "value": value,
            })

        # Calculate Team B's received value
        team_b_value = 0.0
        team_b_assets = []

        for player_id in team_b_player_ids:
            player_name = self.ctx.get_player_name(player_id)
            position = self.ctx.get_player_position(player_id)
            value = self._estimate_player_value(player_name, position)
            team_b_value += value
            team_b_assets.append({
                "player": player_name,
                "position": position,
                "value": round(value, 1),
            })

        for round_num, pick_num in team_b_picks:
            value = self.trade_calc.get_pick_value(round_num, pick_num)
            team_b_value += value
            team_b_assets.append({
                "pick": f"Round {round_num}, Pick {pick_num}",
                "value": value,
            })

        # Determine fairness
        diff = abs(team_a_value - team_b_value)
        if diff < 10:
            fairness = "Fair"
        elif diff < 25:
            fairness = "Slightly Uneven"
        elif diff < 50:
            fairness = "Uneven"
        else:
            fairness = "Lopsided"

        # Recommendation
        if team_a_value > team_b_value + 10:
            recommendation = f"Favors {team_a_name}"
        elif team_b_value > team_a_value + 10:
            recommendation = f"Favors {team_b_name}"
        else:
            recommendation = "Fair trade - consider team needs"

        return {
            team_a_name: {
                "receives": team_a_assets,
                "total_value": round(team_a_value, 1),
            },
            team_b_name: {
                "receives": team_b_assets,
                "total_value": round(team_b_value, 1),
            },
            "value_difference": round(diff, 1),
            "fairness": fairness,
            "recommendation": recommendation,
        }
