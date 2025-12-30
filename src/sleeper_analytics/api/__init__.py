"""API package - FastAPI routes and dependencies."""

from sleeper_analytics.api.dependencies import (
    ClientManager,
    LeagueContextDep,
    NFLStatsDep,
    SettingsDep,
    SleeperClientDep,
    get_league_context,
    get_nfl_stats,
    get_sleeper_client,
)

__all__ = [
    "ClientManager",
    "get_sleeper_client",
    "get_league_context",
    "get_nfl_stats",
    "SleeperClientDep",
    "LeagueContextDep",
    "NFLStatsDep",
    "SettingsDep",
]
