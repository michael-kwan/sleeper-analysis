"""
League-related Pydantic models.
"""

from pydantic import BaseModel, Field


class LeagueScoringSettings(BaseModel):
    """League scoring settings."""

    rec: float = Field(default=1.0, description="Points per reception (PPR)")
    pass_yd: float = Field(default=0.04, description="Points per passing yard")
    pass_td: float = Field(default=4.0, description="Points per passing TD")
    pass_int: float = Field(default=-1.0, description="Points per interception")
    rush_yd: float = Field(default=0.1, description="Points per rushing yard")
    rush_td: float = Field(default=6.0, description="Points per rushing TD")
    rec_yd: float = Field(default=0.1, description="Points per receiving yard")
    rec_td: float = Field(default=6.0, description="Points per receiving TD")
    fum_lost: float = Field(default=-2.0, description="Points per fumble lost")


class LeagueSettings(BaseModel):
    """Full league settings."""

    num_teams: int = Field(alias="total_rosters")
    playoff_week_start: int | None = None
    leg: int = Field(default=1, description="Current week/leg")
    waiver_type: int | None = None
    waiver_budget: int = Field(default=100)
    trade_deadline: int | None = None
    reserve_slots: int = Field(default=0)
    playoff_teams: int = Field(default=6)

    class Config:
        populate_by_name = True


class League(BaseModel):
    """Sleeper league information."""

    league_id: str
    name: str
    status: str
    sport: str = "nfl"
    season: str
    season_type: str
    total_rosters: int
    roster_positions: list[str] = Field(default_factory=list)
    scoring_settings: dict = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)
    avatar: str | None = None
    draft_id: str | None = None
    previous_league_id: str | None = None

    @property
    def is_ppr(self) -> bool:
        """Check if league uses PPR scoring."""
        return self.scoring_settings.get("rec", 0) >= 1.0

    @property
    def is_superflex(self) -> bool:
        """Check if league has superflex position."""
        return "SUPER_FLEX" in self.roster_positions


class User(BaseModel):
    """Sleeper user information."""

    user_id: str
    username: str | None = None
    display_name: str
    avatar: str | None = None
    metadata: dict = Field(default_factory=dict)
    is_owner: bool | None = False

    @property
    def team_name(self) -> str:
        """Get team name from metadata or display name."""
        if self.metadata and "team_name" in self.metadata:
            return self.metadata["team_name"]
        return self.display_name


class Roster(BaseModel):
    """League roster information."""

    roster_id: int
    owner_id: str | None = None
    league_id: str
    players: list[str] = Field(default_factory=list)
    starters: list[str] = Field(default_factory=list)
    reserve: list[str] | None = None
    taxi: list[str] | None = None
    settings: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    @property
    def wins(self) -> int:
        return self.settings.get("wins", 0)

    @property
    def losses(self) -> int:
        return self.settings.get("losses", 0)

    @property
    def ties(self) -> int:
        return self.settings.get("ties", 0)

    @property
    def fpts(self) -> float:
        """Total fantasy points scored."""
        pts = self.settings.get("fpts", 0)
        decimal = self.settings.get("fpts_decimal", 0)
        return pts + (decimal / 100)

    @property
    def fpts_against(self) -> float:
        """Total fantasy points against."""
        pts = self.settings.get("fpts_against", 0)
        decimal = self.settings.get("fpts_against_decimal", 0)
        return pts + (decimal / 100)


class NFLState(BaseModel):
    """Current NFL state from Sleeper."""

    week: int
    season: str
    season_type: str
    display_week: int
    leg: int
    season_start_date: str | None = None
    previous_season: str | None = None
