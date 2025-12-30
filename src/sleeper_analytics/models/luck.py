"""
Matchup Luck Analysis Models

Analyzes strength of schedule and lucky/unlucky wins and losses.
"""

from pydantic import BaseModel, Field


class WeeklyLuckAnalysis(BaseModel):
    """Luck analysis for a single week."""

    week: int
    roster_id: int
    team_name: str
    actual_result: str = Field(description="W, L, or T")
    points_scored: float
    opponent_points: float
    opponent_name: str
    league_median: float = Field(description="Median score for the week")
    league_rank_this_week: int = Field(description="1 = highest scorer")
    wins_vs_all: int = Field(
        description="How many teams they would beat if they played everyone"
    )
    expected_win_pct: float = Field(
        description="wins_vs_all / total_teams (excluding self)"
    )
    luck_factor: str = Field(
        description="lucky_win, unlucky_loss, deserved_win, deserved_loss, or tie"
    )


class StrengthOfSchedule(BaseModel):
    """Strength of schedule analysis."""

    roster_id: int
    team_name: str
    avg_opponent_points: float = Field(description="Average opponent score")
    avg_opponent_rank: float = Field(
        description="Average opponent rank (1 = toughest schedule)"
    )
    toughest_schedule_rank: int = Field(
        description="Rank compared to league (1 = toughest)"
    )
    easiest_weeks: list[int] = Field(description="Weeks with easiest matchups")
    hardest_weeks: list[int] = Field(description="Weeks with hardest matchups")
    total_weeks: int


class LuckReport(BaseModel):
    """Complete luck analysis for a team."""

    roster_id: int
    team_name: str
    actual_wins: int
    actual_losses: int
    actual_ties: int
    actual_record: str = Field(description="e.g., '8-5-0'")
    expected_wins: float = Field(
        description="Based on scoring against league median each week"
    )
    expected_record: str = Field(description="e.g., '6.5-6.5-0'")
    luck_score: float = Field(
        description="Positive = lucky (more wins than expected), negative = unlucky"
    )
    lucky_wins: list[WeeklyLuckAnalysis] = Field(
        description="Weeks where they won despite scoring below median"
    )
    unlucky_losses: list[WeeklyLuckAnalysis] = Field(
        description="Weeks where they lost despite scoring above median"
    )
    strength_of_schedule: StrengthOfSchedule


class LeagueLuckReport(BaseModel):
    """League-wide luck analysis."""

    league_id: str
    league_name: str
    weeks_analyzed: int
    team_reports: list[LuckReport]
    luckiest_team: str = Field(description="Team with highest luck score")
    unluckiest_team: str = Field(description="Team with lowest luck score")
    luckiest_score: float
    unluckiest_score: float
