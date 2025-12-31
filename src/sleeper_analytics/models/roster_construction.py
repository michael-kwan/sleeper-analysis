"""
Roster Construction Analysis Models

Tracks where each team's points came from (draft, trades, waivers, FA).
"""

from enum import Enum

from pydantic import BaseModel, Field


class AcquisitionMethod(str, Enum):
    """How a player was acquired."""

    DRAFT = "draft"
    TRADE = "trade"
    WAIVER = "waiver"
    FREE_AGENT = "free_agent"
    UNKNOWN = "unknown"


class PlayerAcquisition(BaseModel):
    """Details of how a player was acquired."""

    player_id: str
    player_name: str
    position: str
    acquisition_method: AcquisitionMethod
    acquisition_week: int = Field(description="Week player was acquired (0 for draft)")
    points_scored: float = Field(description="Total points scored while owned")
    weeks_owned: int = Field(description="Number of weeks owned")
    is_currently_owned: bool = Field(default=True)


class RosterConstructionBreakdown(BaseModel):
    """Point breakdown by acquisition method."""

    draft_points: float = Field(description="Points from drafted players")
    draft_percentage: float = Field(description="% of total from draft")

    trade_points: float = Field(description="Points from traded players")
    trade_percentage: float = Field(description="% of total from trades")

    waiver_points: float = Field(description="Points from waiver pickups")
    waiver_percentage: float = Field(description="% of total from waivers")

    free_agent_points: float = Field(description="Points from FA pickups")
    free_agent_percentage: float = Field(description="% of total from FA")

    total_points: float = Field(description="Total points scored")

    draft_count: int = Field(default=0, description="Number of drafted players")
    trade_count: int = Field(default=0, description="Number of traded players")
    waiver_count: int = Field(default=0, description="Number of waiver pickups")
    free_agent_count: int = Field(default=0, description="Number of FA pickups")


class TeamRosterConstruction(BaseModel):
    """Roster construction analysis for a single team."""

    roster_id: int
    team_name: str
    breakdown: RosterConstructionBreakdown
    acquisitions: list[PlayerAcquisition] = Field(default_factory=list)

    # Insights
    primary_source: AcquisitionMethod = Field(
        description="Acquisition method that contributed most points"
    )
    draft_reliance: str = Field(
        description="How reliant team is on drafted players"
    )
    waiver_activity: str = Field(
        description="Waiver wire activity level"
    )


class LeagueRosterConstructionReport(BaseModel):
    """League-wide roster construction analysis."""

    league_id: str
    league_name: str
    weeks_analyzed: int

    all_teams: list[TeamRosterConstruction]

    # League-wide stats
    avg_draft_percentage: float = Field(
        description="Average % of points from draft across league"
    )
    avg_trade_percentage: float
    avg_waiver_percentage: float
    avg_free_agent_percentage: float

    # Champions
    best_drafter: str = Field(description="Team with highest draft %")
    best_drafter_pct: float

    most_active_trader: str = Field(description="Team with most trade acquisitions")
    most_active_trader_count: int

    waiver_wire_king: str = Field(description="Team with most waiver points")
    waiver_wire_king_points: float
