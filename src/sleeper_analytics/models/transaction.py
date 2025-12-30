"""
Transaction-related Pydantic models.
"""

from enum import Enum

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Types of transactions in Sleeper."""

    TRADE = "trade"
    WAIVER = "waiver"
    FREE_AGENT = "free_agent"
    COMMISSIONER = "commissioner"


class TransactionStatus(str, Enum):
    """Transaction status."""

    COMPLETE = "complete"
    PENDING = "pending"
    FAILED = "failed"


class DraftPick(BaseModel):
    """Draft pick involved in a transaction."""

    season: str
    round: int
    roster_id: int
    previous_owner_id: int | None = None
    owner_id: int


class WaiverBudget(BaseModel):
    """Waiver budget transfer in a transaction."""

    sender: int
    receiver: int
    amount: int


class Transaction(BaseModel):
    """Sleeper transaction."""

    transaction_id: str
    type: TransactionType
    status: TransactionStatus
    week: int = Field(default=0, description="Week the transaction occurred")
    roster_ids: list[int] = Field(default_factory=list)
    adds: dict[str, int] | None = Field(
        default=None, description="Player ID -> Roster ID receiving"
    )
    drops: dict[str, int] | None = Field(
        default=None, description="Player ID -> Roster ID dropping"
    )
    draft_picks: list[DraftPick] = Field(default_factory=list)
    waiver_budget: list[WaiverBudget] = Field(default_factory=list)
    settings: dict | None = None
    metadata: dict | None = None
    created: int | None = Field(default=None, description="Unix timestamp")
    consenter_ids: list[int] = Field(default_factory=list)
    status_updated: int | None = None
    creator: str | None = None

    @property
    def is_trade(self) -> bool:
        return self.type == TransactionType.TRADE

    @property
    def is_waiver(self) -> bool:
        return self.type == TransactionType.WAIVER

    @property
    def teams_count(self) -> int:
        return len(self.roster_ids)


class TradeAsset(BaseModel):
    """An asset (player or pick) in a trade."""

    asset_type: str = Field(description="'player' or 'pick'")
    player_id: str | None = None
    player_name: str | None = None
    position: str | None = None
    pick_round: int | None = None
    pick_season: str | None = None
    value: float = Field(default=0.0, description="Estimated trade value")


class TradeSide(BaseModel):
    """One side of a trade."""

    roster_id: int
    team_name: str
    assets_received: list[TradeAsset] = Field(default_factory=list)
    total_value: float = Field(default=0.0)


class TradeFairness(str, Enum):
    """Trade fairness classification."""

    FAIR = "Fair"
    SLIGHTLY_UNEVEN = "Slightly Uneven"
    UNEVEN = "Uneven"
    LOPSIDED = "Lopsided"


class TradeAnalysis(BaseModel):
    """Analysis of a trade."""

    transaction_id: str
    week: int
    sides: list[TradeSide]
    value_difference: float
    fairness: TradeFairness
    winner: str | None = Field(default=None, description="Team name of trade winner")


class TransactionSummary(BaseModel):
    """Summary of transactions in a league."""

    total: int
    by_type: dict[str, int] = Field(default_factory=dict)
    by_week: dict[int, int] = Field(default_factory=dict)
    by_team: dict[str, dict[str, int]] = Field(default_factory=dict)
