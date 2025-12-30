"""
Benchwarmer models for tracking bench performance.

Identifies players who scored high points while on the bench.
"""

from pydantic import BaseModel, Field


class BenchwarmerWeek(BaseModel):
    """A single instance of a high-scoring benched player."""

    week: int
    player_id: str
    player_name: str
    position: str
    points: float
    roster_id: int
    team_name: str
    was_benched: bool = True
    could_have_started: bool = Field(
        description="True if player was eligible for a starting slot"
    )


class BenchwarmerReport(BaseModel):
    """Benchwarmer analysis for a single team."""

    roster_id: int
    team_name: str
    total_bench_points: float = Field(
        description="Total points scored by benched players who could have started"
    )
    total_weeks_analyzed: int
    top_benchwarmers: list[BenchwarmerWeek] = Field(
        description="Highest scoring bench performances"
    )
    worst_benching_decision: BenchwarmerWeek | None = Field(
        description="Single worst start/sit decision"
    )
    avg_bench_points_per_week: float


class LeagueBenchwarmerReport(BaseModel):
    """League-wide benchwarmer analysis."""

    league_id: str
    league_name: str
    weeks_analyzed: int
    all_teams: list[BenchwarmerReport]
    biggest_benching_mistakes: list[BenchwarmerWeek] = Field(
        description="Top benching mistakes across the league"
    )
    benchwarmer_champion: str = Field(
        description="Team with most points left on bench"
    )
    benchwarmer_champion_points: float
