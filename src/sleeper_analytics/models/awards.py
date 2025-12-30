"""
Awards models for tracking weekly high/low scorers.

Used for payout tracking ($5 per week).
"""

from pydantic import BaseModel, Field


class WeeklyAward(BaseModel):
    """Award for a single week's high and low scorer."""

    week: int
    high_scorer_roster_id: int
    high_scorer: str
    high_score: float
    low_scorer_roster_id: int
    low_scorer: str
    low_score: float


class SeasonAwardsReport(BaseModel):
    """Summary of all weekly awards for the season."""

    league_id: str
    league_name: str
    weeks_analyzed: int
    weekly_awards: list[WeeklyAward]
    high_score_leaders: dict[str, int] = Field(
        description="Team name -> count of high scores"
    )
    low_score_leaders: dict[str, int] = Field(
        description="Team name -> count of low scores"
    )
    total_payout_high: float = Field(
        description="Total $ owed to high scorers (weekly_count * $5)"
    )
    total_payout_low: float = Field(
        description="Total $ owed by low scorers (weekly_count * $5)"
    )
    payout_by_team: dict[str, float] = Field(
        description="Net payout per team (positive = owed money, negative = owes money)"
    )
