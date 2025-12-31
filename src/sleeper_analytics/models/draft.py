"""
Draft Analysis Models

Tracks draft performance and identifies best/worst picks.
"""

from pydantic import BaseModel, Field


class DraftPick(BaseModel):
    """A single draft pick with performance metrics."""

    pick_number: int = Field(description="Overall pick number")
    round: int
    pick_in_round: int
    roster_id: int
    team_name: str
    player_id: str
    player_name: str
    position: str
    points_scored: float = Field(description="Total points scored")
    games_played: int = Field(description="Weeks with points > 0")
    points_per_game: float = Field(description="Average points per game played")
    is_on_roster: bool = Field(description="Still on drafting team's roster")
    value_rating: str = Field(description="Hit/Solid/Bust rating")


class RoundSummary(BaseModel):
    """Summary of a draft round."""

    round_number: int
    total_picks: int
    avg_points: float
    best_pick: DraftPick | None
    worst_pick: DraftPick | None
    hit_rate: float = Field(description="% of picks that were productive")


class TeamDraftGrade(BaseModel):
    """Draft performance for a single team."""

    roster_id: int
    team_name: str
    total_picks: int
    total_points: float = Field(description="Total points from draft picks")
    avg_points_per_pick: float
    best_pick: DraftPick | None
    worst_pick: DraftPick | None
    hit_rate: float = Field(description="% of picks still on roster or productive")
    draft_grade: str = Field(description="A+/A/B+/B/C+/C/D/F grade")
    picks: list[DraftPick]


class DraftAnalysisReport(BaseModel):
    """Complete draft analysis for a league."""

    league_id: str
    league_name: str
    draft_id: str
    total_rounds: int
    total_picks: int
    weeks_analyzed: int

    team_grades: list[TeamDraftGrade]
    round_summaries: list[RoundSummary]

    # Overall stats
    best_drafter: str = Field(description="Team with best draft grade")
    best_drafter_avg_ppick: float
    worst_drafter: str
    worst_drafter_avg_ppick: float

    best_overall_pick: DraftPick | None
    biggest_bust: DraftPick | None

    league_avg_points_per_pick: float
    league_hit_rate: float
