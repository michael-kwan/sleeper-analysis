"""
Player-related Pydantic models.
"""

from pydantic import BaseModel, Field


class Player(BaseModel):
    """NFL Player information from Sleeper."""

    player_id: str
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    position: str | None = None
    team: str | None = None
    age: int | None = None
    years_exp: int | None = None
    status: str | None = None
    injury_status: str | None = None
    number: int | None = None
    depth_chart_order: int | None = None
    fantasy_positions: list[str] | None = None

    @property
    def display_name(self) -> str:
        """Get display name for the player."""
        if self.full_name:
            return self.full_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.player_id


class PlayerPoints(BaseModel):
    """Player fantasy points for a matchup."""

    player_id: str
    player_name: str
    position: str
    points: float = 0.0
    is_starter: bool = False


class PlayerValue(BaseModel):
    """Player trade value calculation."""

    player_id: str
    player_name: str
    position: str
    total_points: float = Field(description="Total fantasy points scored")
    games_played: int = Field(description="Number of games played")
    ppg: float = Field(description="Points per game")
    position_rank: int = Field(description="Rank at position")
    consistency: float = Field(description="Standard deviation of weekly scores")
    value_score: float = Field(ge=0, le=100, description="Composite value score 0-100")
