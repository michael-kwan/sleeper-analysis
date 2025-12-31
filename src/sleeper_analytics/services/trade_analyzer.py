"""
Comprehensive Trade Analysis Service

Analyzes trades from both value and roster needs perspectives.
"""

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.models.trade_analyzer import (
    ByeWeekImpact,
    ComprehensiveTradeAnalysis,
    PlayoffTiming,
    PositionNeed,
    RosterNeedsAnalysis,
    TradeImpactAnalysis,
)
from sleeper_analytics.services.nfl_stats import NFLStatsService, TradeValueCalculator
from sleeper_analytics.services.trades import TransactionService


class TradeAnalyzerService:
    """
    Service for comprehensive trade analysis.

    Analyzes trades from multiple angles:
    - Simple value comparison
    - Position depth and needs
    - Bye week impact
    - Playoff timing
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
        self.transaction_service = TransactionService(client, context, nfl_stats)

    async def analyze_roster_needs(
        self, roster_id: int
    ) -> RosterNeedsAnalysis:
        """
        Analyze a team's roster needs.

        Args:
            roster_id: Team to analyze

        Returns:
            Complete roster needs analysis
        """
        # Get roster
        roster = next(r for r in self.ctx.rosters if r.roster_id == roster_id)
        team_name = self.ctx.get_team_name(roster_id)

        # Analyze position depth
        position_needs = []
        positions = ["QB", "RB", "WR", "TE"]

        for pos in positions:
            # Count players at this position
            players = [
                p for p in roster.players
                if self.ctx.get_player_position(p) == pos
            ]

            # Determine starters needed (simplified)
            starters_needed = {
                "QB": 1,
                "RB": 2,
                "WR": 2,
                "TE": 1,
            }.get(pos, 0)

            current_starters = min(len(players), starters_needed)
            bench_depth = max(0, len(players) - starters_needed)

            # Determine need level
            if current_starters < starters_needed:
                need_level = "critical"
            elif bench_depth < 2:
                need_level = "moderate"
            else:
                need_level = "satisfied"

            position_needs.append(
                PositionNeed(
                    position=pos,
                    starters_needed=starters_needed,
                    current_starters=current_starters,
                    bench_depth=bench_depth,
                    need_level=need_level,
                )
            )

        # Find top need
        critical_needs = [p for p in position_needs if p.need_level == "critical"]
        if critical_needs:
            top_need = critical_needs[0].position
        else:
            moderate_needs = [p for p in position_needs if p.need_level == "moderate"]
            top_need = moderate_needs[0].position if moderate_needs else "None"

        # Simplified bye week and playoff analysis
        bye_week_issues = []  # Could be enhanced with actual bye week data
        playoff_outlook = PlayoffTiming(
            playoff_weeks=[15, 16, 17],
            key_players_available=[],
            injury_concerns=[],
            overall_strength="average",
        )

        # Determine trade priority
        if critical_needs:
            trade_priority = "win_now"
        elif len([p for p in position_needs if p.need_level == "satisfied"]) >= 3:
            trade_priority = "build_depth"
        else:
            trade_priority = "balanced"

        return RosterNeedsAnalysis(
            roster_id=roster_id,
            team_name=team_name,
            position_needs=position_needs,
            bye_week_issues=bye_week_issues,
            playoff_outlook=playoff_outlook,
            top_need=top_need,
            trade_priority=trade_priority,
        )

    async def analyze_comprehensive_trade(
        self,
        team_a_roster_id: int,
        team_a_gives: list[str],
        team_b_roster_id: int,
        team_b_gives: list[str],
    ) -> ComprehensiveTradeAnalysis:
        """
        Comprehensive trade analysis with value and roster fit.

        Args:
            team_a_roster_id: Team A's roster ID
            team_a_gives: Player IDs Team A gives away
            team_b_roster_id: Team B's roster ID
            team_b_gives: Player IDs Team B gives away

        Returns:
            Complete trade analysis
        """
        team_a_name = self.ctx.get_team_name(team_a_roster_id)
        team_b_name = self.ctx.get_team_name(team_b_roster_id)

        # Simple value analysis
        team_a_receives_value = sum(
            self._get_player_value(pid) for pid in team_b_gives
        )
        team_b_receives_value = sum(
            self._get_player_value(pid) for pid in team_a_gives
        )

        value_diff = abs(team_a_receives_value - team_b_receives_value)

        if value_diff < 10:
            value_fairness = "Fair"
        elif value_diff < 25:
            value_fairness = "Slightly Uneven"
        else:
            value_fairness = "Uneven"

        # Roster needs analysis
        team_a_needs = await self.analyze_roster_needs(team_a_roster_id)
        team_b_needs = await self.analyze_roster_needs(team_b_roster_id)

        # Analyze trade impact for Team A
        team_a_impact = self._analyze_trade_impact(
            team_a_needs, team_a_gives, team_b_gives
        )

        # Analyze trade impact for Team B
        team_b_impact = self._analyze_trade_impact(
            team_b_needs, team_b_gives, team_a_gives
        )

        # Determine overall winner
        if team_a_impact.overall_fit_score > team_b_impact.overall_fit_score + 10:
            overall_winner = "team_a"
            confidence = "high" if value_diff < 15 else "medium"
        elif team_b_impact.overall_fit_score > team_a_impact.overall_fit_score + 10:
            overall_winner = "team_b"
            confidence = "high" if value_diff < 15 else "medium"
        else:
            overall_winner = "fair"
            confidence = "medium"

        # Final recommendation
        if overall_winner == "team_a":
            final_recommendation = f"Trade favors {team_a_name} - better roster fit"
        elif overall_winner == "team_b":
            final_recommendation = f"Trade favors {team_b_name} - better roster fit"
        else:
            final_recommendation = "Fair trade - both teams address needs"

        return ComprehensiveTradeAnalysis(
            team_a_name=team_a_name,
            team_b_name=team_b_name,
            team_a_receives_value=round(team_a_receives_value, 1),
            team_b_receives_value=round(team_b_receives_value, 1),
            value_difference=round(value_diff, 1),
            value_fairness=value_fairness,
            team_a_impact=team_a_impact,
            team_b_impact=team_b_impact,
            overall_winner=overall_winner,
            confidence=confidence,
            final_recommendation=final_recommendation,
        )

    def _get_player_value(self, player_id: str) -> float:
        """Get estimated player value."""
        player_name = self.ctx.get_player_name(player_id)
        position = self.ctx.get_player_position(player_id)

        # Simplified value estimation
        # Could be enhanced with actual trade values or projections
        base_values = {
            "QB": 50,
            "RB": 60,
            "WR": 55,
            "TE": 45,
        }

        return base_values.get(position, 40)

    def _analyze_trade_impact(
        self,
        needs: RosterNeedsAnalysis,
        gives_away: list[str],
        receives: list[str],
    ) -> TradeImpactAnalysis:
        """Analyze how a trade impacts roster needs."""
        position_improvements = {}
        position_downgrades = {}

        # Analyze what they're giving away
        for player_id in gives_away:
            pos = self.ctx.get_player_position(player_id)
            player_name = self.ctx.get_player_name(player_id)

            # Find position need
            need = next((n for n in needs.position_needs if n.position == pos), None)
            if need and need.need_level in ["critical", "moderate"]:
                position_downgrades[pos] = f"Loses {player_name} at position of need"

        # Analyze what they're receiving
        for player_id in receives:
            pos = self.ctx.get_player_position(player_id)
            player_name = self.ctx.get_player_name(player_id)

            # Find position need
            need = next((n for n in needs.position_needs if n.position == pos), None)
            if need and need.need_level == "critical":
                position_improvements[pos] = f"Adds {player_name} to critical need"
            elif need and need.need_level == "moderate":
                position_improvements[pos] = f"Strengthens {player_name} at {pos}"

        # Calculate fit score
        fit_score = 50.0  # Base score

        # Bonus for addressing needs
        fit_score += len(position_improvements) * 15

        # Penalty for creating holes
        fit_score -= len(position_downgrades) * 10

        # Clamp between 0-100
        fit_score = max(0, min(100, fit_score))

        # Generate recommendation
        if fit_score >= 70:
            recommendation = "Strong fit - addresses key needs"
        elif fit_score >= 50:
            recommendation = "Reasonable fit - consider team context"
        else:
            recommendation = "Poor fit - creates more holes than it fills"

        return TradeImpactAnalysis(
            team_name=needs.team_name,
            position_improvements=position_improvements,
            position_downgrades=position_downgrades,
            bye_week_impact="neutral",  # Simplified
            playoff_impact="neutral",  # Simplified
            overall_fit_score=round(fit_score, 1),
            recommendation=recommendation,
        )
