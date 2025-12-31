"""
Trade Analysis Models

Models for comprehensive trade evaluation including roster needs.
"""

from pydantic import BaseModel, Field


class PositionNeed(BaseModel):
    """Position depth analysis for a team."""

    position: str
    starters_needed: int
    current_starters: int
    bench_depth: int
    need_level: str = Field(
        description="critical, moderate, or satisfied"
    )


class ByeWeekImpact(BaseModel):
    """Bye week coverage analysis."""

    week: int
    affected_starters: list[str] = Field(description="Player names")
    backup_available: bool
    severity: str = Field(description="high, medium, or low")


class PlayoffTiming(BaseModel):
    """Playoff roster strength analysis."""

    playoff_weeks: list[int]
    key_players_available: list[str]
    injury_concerns: list[str]
    overall_strength: str = Field(description="strong, average, or weak")


class RosterNeedsAnalysis(BaseModel):
    """Complete roster needs assessment."""

    roster_id: int
    team_name: str
    position_needs: list[PositionNeed]
    bye_week_issues: list[ByeWeekImpact]
    playoff_outlook: PlayoffTiming
    top_need: str = Field(description="Most critical position need")
    trade_priority: str = Field(description="win_now, build_depth, or balanced")


class TradeImpactAnalysis(BaseModel):
    """Analysis of how a trade affects roster needs."""

    team_name: str
    position_improvements: dict[str, str] = Field(
        description="Position -> improvement description"
    )
    position_downgrades: dict[str, str] = Field(
        description="Position -> downgrade description"
    )
    bye_week_impact: str = Field(description="better, worse, or neutral")
    playoff_impact: str = Field(description="stronger, weaker, or neutral")
    overall_fit_score: float = Field(description="0-100 score")
    recommendation: str


class ComprehensiveTradeAnalysis(BaseModel):
    """Complete trade analysis with both value and roster fit."""

    # Simple value analysis
    team_a_name: str
    team_b_name: str
    team_a_receives_value: float
    team_b_receives_value: float
    value_difference: float
    value_fairness: str

    # Roster needs analysis
    team_a_impact: TradeImpactAnalysis
    team_b_impact: TradeImpactAnalysis

    # Overall recommendation
    overall_winner: str = Field(description="team_a, team_b, or fair")
    confidence: str = Field(description="high, medium, or low")
    final_recommendation: str
