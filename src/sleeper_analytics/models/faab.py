"""
FAAB Analysis Models

Tracks player lifecycle through the league and FAAB spending efficiency.
"""

from pydantic import BaseModel, Field


class PlayerOwnershipPeriod(BaseModel):
    """A single ownership period for a player."""

    player_id: str
    player_name: str
    position: str
    owner_roster_id: int
    owner_name: str
    acquired_week: int
    dropped_week: int | None = Field(
        description="None if still owned"
    )
    faab_spent: int = Field(
        description="FAAB spent to acquire (0 for free agent)"
    )
    weeks_owned: int
    points_during_ownership: float = Field(
        description="Total points scored while owned"
    )
    points_per_week: float
    roi: float = Field(
        description="Points gained per dollar spent (points / faab_spent). Infinity if free agent."
    )


class PlayerLifecycle(BaseModel):
    """Complete journey of a player through the league."""

    player_id: str
    player_name: str
    position: str
    ownership_history: list[PlayerOwnershipPeriod]
    total_faab_spent: int = Field(
        description="Total FAAB spent on this player league-wide"
    )
    times_picked_up: int
    times_dropped: int
    current_owner: str | None
    best_roi_owner: str = Field(
        description="Owner who got best value from this player"
    )
    worst_roi_owner: str | None = Field(
        description="Owner who got worst value from this player"
    )


class OwnerFAABPerformance(BaseModel):
    """FAAB efficiency for a single owner."""

    roster_id: int
    owner_name: str
    total_faab_spent: int
    faab_remaining: int
    total_faab_budget: int = 100
    acquisitions: list[PlayerOwnershipPeriod] = Field(
        description="All FAAB pickups by this owner"
    )
    total_points_from_faab: float = Field(
        description="Total points from all FAAB acquisitions"
    )
    avg_roi: float = Field(
        description="Average ROI across all acquisitions"
    )
    best_pickup: PlayerOwnershipPeriod | None
    worst_pickup: PlayerOwnershipPeriod | None
    faab_efficiency_rank: int = 0  # Will be set by league comparison


class LeagueFAABReport(BaseModel):
    """League-wide FAAB analysis."""

    league_id: str
    league_name: str
    weeks_analyzed: int
    total_faab_spent: int
    owner_rankings: list[OwnerFAABPerformance] = Field(
        description="Owners ranked by FAAB efficiency (ROI)"
    )
    best_value_pickups: list[PlayerOwnershipPeriod] = Field(
        description="Top 20 FAAB pickups by ROI"
    )
    worst_value_pickups: list[PlayerOwnershipPeriod] = Field(
        description="Bottom 10 FAAB pickups by ROI (overpays)"
    )
    most_transacted_players: list[PlayerLifecycle] = Field(
        description="Players with most ownership changes"
    )
