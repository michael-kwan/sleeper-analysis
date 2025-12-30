"""
API Dependencies

Shared dependencies for FastAPI route handlers including
client management and league context creation.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query

from sleeper_analytics.clients.sleeper import LeagueContext, SleeperClient
from sleeper_analytics.config import Settings, get_settings
from sleeper_analytics.services.nfl_stats import NFLStatsService, get_nfl_stats_service


class ClientManager:
    """
    Manages SleeperClient lifecycle for the application.

    Creates a single client instance that can be reused across requests.
    """

    _client: SleeperClient | None = None

    @classmethod
    async def get_client(cls) -> SleeperClient:
        """Get or create the SleeperClient instance."""
        if cls._client is None:
            cls._client = SleeperClient()
            await cls._client.__aenter__()
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        """Close the SleeperClient instance."""
        if cls._client is not None:
            await cls._client.__aexit__(None, None, None)
            cls._client = None


async def get_sleeper_client() -> SleeperClient:
    """Dependency to get the SleeperClient."""
    return await ClientManager.get_client()


async def get_league_context(
    league_id: Annotated[str, Path(description="Sleeper league ID")],
    client: Annotated[SleeperClient, Depends(get_sleeper_client)],
) -> LeagueContext:
    """
    Dependency to create a LeagueContext for a given league.

    Raises HTTPException if league not found.
    """
    try:
        context = await LeagueContext.create(client, league_id)
        return context
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"League not found: {league_id}. Error: {str(e)}",
        )


def get_nfl_stats(
    season: Annotated[
        int,
        Query(description="NFL season year", ge=2020, le=2030),
    ] = 2024,
) -> NFLStatsService:
    """Dependency to get NFLStatsService for a season."""
    return get_nfl_stats_service(season)


# Type aliases for cleaner route signatures
SleeperClientDep = Annotated[SleeperClient, Depends(get_sleeper_client)]
LeagueContextDep = Annotated[LeagueContext, Depends(get_league_context)]
NFLStatsDep = Annotated[NFLStatsService, Depends(get_nfl_stats)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


# Common query parameters
WeeksQuery = Annotated[
    int,
    Query(description="Number of weeks to analyze", ge=1, le=18),
]

SeasonQuery = Annotated[
    int,
    Query(description="NFL season year", ge=2020, le=2030),
]
