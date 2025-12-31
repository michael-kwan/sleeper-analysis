"""
Lopsided Trades Analysis Models

Identifies the most one-sided trades based on post-trade performance.
"""

from pydantic import BaseModel, Field


class TradePlayer(BaseModel):
    """A player involved in a trade."""

    player_id: str
    player_name: str
    position: str
    from_team: str
    to_team: str
    points_after_trade: float = Field(
        description="Points scored after the trade"
    )
    weeks_after_trade: int = Field(
        description="Number of weeks since trade"
    )
    ppw_after_trade: float = Field(
        description="Points per week after trade"
    )


class LopsidedTrade(BaseModel):
    """Analysis of a single potentially lopsided trade."""

    transaction_id: str
    week: int
    team_a: str
    team_b: str

    team_a_players: list[TradePlayer] = Field(
        description="Players Team A received"
    )
    team_b_players: list[TradePlayer] = Field(
        description="Players Team B received"
    )

    team_a_points_received: float = Field(
        description="Total points scored by players Team A received"
    )
    team_b_points_received: float = Field(
        description="Total points scored by players Team B received"
    )

    point_differential: float = Field(
        description="Absolute difference in points received"
    )

    winner: str = Field(description="Team that won the trade")
    loser: str = Field(description="Team that lost the trade")

    lopsidedness_rating: str = Field(
        description="Slightly Lopsided / Lopsided / Extremely Lopsided"
    )


class LopsidedTradesReport(BaseModel):
    """Complete lopsided trades analysis for a league."""

    league_id: str
    league_name: str
    weeks_analyzed: int
    total_trades: int

    most_lopsided_trades: list[LopsidedTrade] = Field(
        description="Top 10 most lopsided trades"
    )

    biggest_trade_winner: str = Field(
        description="Team that benefited most from a single trade"
    )
    biggest_trade_winner_differential: float

    biggest_trade_loser: str = Field(
        description="Team that lost most from a single trade"
    )
    biggest_trade_loser_differential: float

    best_overall_trader: str = Field(
        description="Team with best cumulative trade performance"
    )
    best_overall_trader_net_points: float

    worst_overall_trader: str
    worst_overall_trader_net_points: float
