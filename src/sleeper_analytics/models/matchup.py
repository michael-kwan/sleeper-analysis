"""
Matchup-related Pydantic models.
"""

from pydantic import BaseModel, Field


class MatchupTeam(BaseModel):
    """A team's performance in a matchup."""

    roster_id: int
    team_name: str
    points: float = 0.0
    starters: list[str] = Field(default_factory=list)
    players: list[str] = Field(default_factory=list)
    players_points: dict[str, float] = Field(default_factory=dict)


class Matchup(BaseModel):
    """A weekly matchup between two teams."""

    week: int
    matchup_id: int
    team1: MatchupTeam
    team2: MatchupTeam

    @property
    def winner(self) -> MatchupTeam | None:
        """Get the winning team."""
        if self.team1.points > self.team2.points:
            return self.team1
        elif self.team2.points > self.team1.points:
            return self.team2
        return None

    @property
    def margin(self) -> float:
        """Point differential."""
        return abs(self.team1.points - self.team2.points)

    @property
    def is_close(self, threshold: float = 10.0) -> bool:
        """Check if game was close."""
        return self.margin <= threshold


class WeeklyResult(BaseModel):
    """A team's result for a single week."""

    week: int
    points: float
    opponent: str
    opponent_points: float
    result: str = Field(description="W, L, or T")

    @property
    def won(self) -> bool:
        return self.result == "W"


class TeamPerformance(BaseModel):
    """Season performance for a team."""

    roster_id: int
    team_name: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    avg_points: float = 0.0
    consistency: float = Field(default=0.0, description="Std dev of weekly scores")
    weekly_results: list[WeeklyResult] = Field(default_factory=list)

    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def win_pct(self) -> float:
        if self.games_played == 0:
            return 0.0
        return round(self.wins / self.games_played * 100, 1)


class Standing(BaseModel):
    """League standing entry."""

    rank: int
    roster_id: int
    team_name: str
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    win_pct: float
    avg_points: float


class EfficiencyReport(BaseModel):
    """Roster efficiency report."""

    week: int | None = None
    roster_id: int
    team_name: str
    points_scored: float
    potential_points: float
    efficiency_pct: float
    bench_points: float
    missed_opportunities: list[dict] = Field(default_factory=list)


class SeasonEfficiency(BaseModel):
    """Season-long efficiency metrics."""

    roster_id: int
    team_name: str
    total_points_scored: float
    total_potential_points: float
    season_efficiency_pct: float
    points_left_on_bench: float
    weekly_efficiency: list[EfficiencyReport] = Field(default_factory=list)
    total_missed_opportunities: int = 0
