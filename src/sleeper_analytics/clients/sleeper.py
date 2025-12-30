"""
Async Sleeper API Client

Handles all API interactions with the Sleeper Fantasy Football platform.
Uses httpx for async HTTP requests with connection pooling.

API Documentation: https://docs.sleeper.com/
"""

import asyncio
import time
from typing import Any

import httpx

from sleeper_analytics.config import Settings, get_settings
from sleeper_analytics.models import (
    League,
    NFLState,
    Player,
    Roster,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)


class SleeperAPIError(Exception):
    """Exception raised for Sleeper API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SleeperClient:
    """
    Async client for the Sleeper Fantasy Football API.

    Usage:
        async with SleeperClient() as client:
            user = await client.get_user("username")
            leagues = await client.get_user_leagues(user.user_id, 2024)
    """

    _players_cache: dict[str, Player] | None = None
    _players_cache_raw: dict[str, dict] | None = None
    _cache_timestamp: float = 0

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SleeperClient":
        """Create HTTP client on context entry."""
        self._client = httpx.AsyncClient(
            base_url=self.settings.sleeper_base_url,
            timeout=httpx.Timeout(self.settings.sleeper_timeout),
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close HTTP client on context exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "SleeperClient must be used as async context manager: "
                "async with SleeperClient() as client: ..."
            )
        return self._client

    async def _get(self, endpoint: str) -> Any:
        """Make a GET request to the Sleeper API."""
        response = await self.client.get(endpoint)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise SleeperAPIError(
                f"API request failed: {endpoint}",
                status_code=response.status_code,
            )

        return response.json()

    # ==================== User Endpoints ====================

    async def get_user(self, username: str) -> User | None:
        """
        Get user information by username or user_id.

        Args:
            username: Sleeper username or user ID

        Returns:
            User object or None if not found
        """
        data = await self._get(f"/user/{username}")
        if data is None:
            return None
        return User(**data)

    async def get_user_leagues(
        self, user_id: str, season: int, sport: str = "nfl"
    ) -> list[League]:
        """
        Get all leagues for a user in a given season.

        Args:
            user_id: Sleeper user ID
            season: Season year (e.g., 2024)
            sport: Sport type (default: nfl)

        Returns:
            List of League objects
        """
        data = await self._get(f"/user/{user_id}/leagues/{sport}/{season}")
        if data is None:
            return []
        return [League(**league) for league in data]

    # ==================== League Endpoints ====================

    async def get_league(self, league_id: str) -> League | None:
        """
        Get league information.

        Args:
            league_id: Sleeper league ID

        Returns:
            League object or None if not found
        """
        data = await self._get(f"/league/{league_id}")
        if data is None:
            return None
        return League(**data)

    async def get_league_rosters(self, league_id: str) -> list[Roster]:
        """
        Get all rosters in a league.

        Args:
            league_id: Sleeper league ID

        Returns:
            List of Roster objects
        """
        data = await self._get(f"/league/{league_id}/rosters")
        if data is None:
            return []
        return [Roster(**roster) for roster in data]

    async def get_league_users(self, league_id: str) -> list[User]:
        """
        Get all users in a league.

        Args:
            league_id: Sleeper league ID

        Returns:
            List of User objects
        """
        data = await self._get(f"/league/{league_id}/users")
        if data is None:
            return []
        return [User(**user) for user in data]

    # ==================== Matchup Endpoints ====================

    async def get_matchups(self, league_id: str, week: int) -> list[dict]:
        """
        Get matchups for a specific week.

        Args:
            league_id: Sleeper league ID
            week: Week number

        Returns:
            List of raw matchup dictionaries
        """
        data = await self._get(f"/league/{league_id}/matchups/{week}")
        return data if data else []

    async def get_matchups_range(
        self, league_id: str, start_week: int = 1, end_week: int = 17
    ) -> dict[int, list[dict]]:
        """
        Get matchups for a range of weeks concurrently.

        Args:
            league_id: Sleeper league ID
            start_week: Starting week
            end_week: Ending week

        Returns:
            Dict mapping week number to matchups
        """
        tasks = [
            self.get_matchups(league_id, week)
            for week in range(start_week, end_week + 1)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        matchups_by_week = {}
        for week, result in enumerate(results, start=start_week):
            if isinstance(result, Exception):
                matchups_by_week[week] = []
            else:
                matchups_by_week[week] = result

        return matchups_by_week

    # ==================== Transaction Endpoints ====================

    async def get_transactions(self, league_id: str, week: int) -> list[Transaction]:
        """
        Get transactions for a specific week (round).

        Args:
            league_id: Sleeper league ID
            week: Week/round number

        Returns:
            List of Transaction objects
        """
        data = await self._get(f"/league/{league_id}/transactions/{week}")
        if data is None:
            return []

        transactions = []
        for txn in data:
            try:
                txn_type = txn.get("type", "")
                status = txn.get("status", "")

                if txn_type not in [t.value for t in TransactionType]:
                    continue
                if status not in [s.value for s in TransactionStatus]:
                    continue

                transactions.append(Transaction(**txn, week=week))
            except Exception:
                continue

        return transactions

    async def get_all_transactions(
        self, league_id: str, weeks: int = 18
    ) -> list[Transaction]:
        """
        Get all transactions for the entire season concurrently.

        Args:
            league_id: Sleeper league ID
            weeks: Number of weeks to fetch

        Returns:
            List of all Transaction objects
        """
        tasks = [self.get_transactions(league_id, week) for week in range(1, weeks + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_transactions = []
        for result in results:
            if isinstance(result, list):
                all_transactions.extend(result)

        return all_transactions

    async def get_traded_picks(self, league_id: str) -> list[dict]:
        """
        Get all traded draft picks in a league.

        Args:
            league_id: Sleeper league ID

        Returns:
            List of traded pick dictionaries
        """
        data = await self._get(f"/league/{league_id}/traded_picks")
        return data if data else []

    # ==================== Draft Endpoints ====================

    async def get_drafts(self, league_id: str) -> list[dict]:
        """
        Get all drafts for a league.

        Args:
            league_id: Sleeper league ID

        Returns:
            List of draft dictionaries
        """
        data = await self._get(f"/league/{league_id}/drafts")
        return data if data else []

    async def get_draft(self, draft_id: str) -> dict | None:
        """
        Get specific draft information.

        Args:
            draft_id: Sleeper draft ID

        Returns:
            Draft dictionary or None
        """
        return await self._get(f"/draft/{draft_id}")

    async def get_draft_picks(self, draft_id: str) -> list[dict]:
        """
        Get all picks in a draft.

        Args:
            draft_id: Sleeper draft ID

        Returns:
            List of draft pick dictionaries
        """
        data = await self._get(f"/draft/{draft_id}/picks")
        return data if data else []

    # ==================== Player Endpoints ====================

    async def get_all_players(self, force_refresh: bool = False) -> dict[str, Player]:
        """
        Get all NFL players with caching.

        This endpoint returns a large payload (~15MB) so we cache it.

        Args:
            force_refresh: Force refresh of cache

        Returns:
            Dict mapping player_id to Player object
        """
        current_time = time.time()
        cache_valid = (
            SleeperClient._players_cache is not None
            and (current_time - SleeperClient._cache_timestamp)
            < self.settings.players_cache_ttl
        )

        if not force_refresh and cache_valid:
            return SleeperClient._players_cache  # type: ignore

        data = await self._get("/players/nfl")
        if data is None:
            return {}

        SleeperClient._players_cache_raw = data
        SleeperClient._players_cache = {}
        for player_id, player_data in data.items():
            try:
                player_data_copy = {**player_data}
                if "player_id" in player_data_copy:
                    del player_data_copy["player_id"]
                SleeperClient._players_cache[player_id] = Player(
                    player_id=player_id, **player_data_copy
                )
            except Exception:
                continue
        SleeperClient._cache_timestamp = current_time

        return SleeperClient._players_cache

    async def get_all_players_raw(self, force_refresh: bool = False) -> dict[str, dict]:
        """
        Get all NFL players as raw dictionaries (cached).

        More efficient when you don't need full Player objects.

        Args:
            force_refresh: Force refresh of cache

        Returns:
            Dict mapping player_id to raw player data
        """
        if SleeperClient._players_cache_raw is None or force_refresh:
            await self.get_all_players(force_refresh)

        return SleeperClient._players_cache_raw or {}

    # ==================== NFL State Endpoint ====================

    async def get_nfl_state(self) -> NFLState | None:
        """
        Get current NFL state (week, season, etc.).

        Returns:
            NFLState object or None
        """
        data = await self._get("/state/nfl")
        if data is None:
            return None
        return NFLState(**data)


class LeagueContext:
    """
    Helper class to hold league context and provide convenient lookups.

    Caches league data and provides methods to resolve roster IDs to team names,
    player IDs to player info, etc.
    """

    def __init__(
        self,
        league: League,
        users: list[User],
        rosters: list[Roster],
        players: dict[str, Player],
    ):
        self.league = league
        self.users = users
        self.rosters = rosters
        self.players = players

        self._user_map: dict[str, User] = {u.user_id: u for u in users}
        self._roster_map: dict[int, Roster] = {r.roster_id: r for r in rosters}
        self._roster_to_user: dict[int, str] = {}

        for roster in rosters:
            if roster.owner_id:
                self._roster_to_user[roster.roster_id] = roster.owner_id

    @classmethod
    async def create(cls, client: SleeperClient, league_id: str) -> "LeagueContext":
        """
        Factory method to create a LeagueContext by fetching all required data.

        Args:
            client: SleeperClient instance
            league_id: Sleeper league ID

        Returns:
            Initialized LeagueContext
        """
        league, users, rosters, players = await asyncio.gather(
            client.get_league(league_id),
            client.get_league_users(league_id),
            client.get_league_rosters(league_id),
            client.get_all_players(),
        )

        if league is None:
            raise SleeperAPIError(f"League not found: {league_id}")

        return cls(league=league, users=users, rosters=rosters, players=players)

    @property
    def league_id(self) -> str:
        return self.league.league_id

    @property
    def league_name(self) -> str:
        return self.league.name

    def get_team_name(self, roster_id: int) -> str:
        """Get team name from roster ID."""
        user_id = self._roster_to_user.get(roster_id)
        if user_id and user_id in self._user_map:
            return self._user_map[user_id].team_name
        return f"Team {roster_id}"

    def get_user_display_name(self, roster_id: int) -> str:
        """Get user display name from roster ID."""
        user_id = self._roster_to_user.get(roster_id)
        if user_id and user_id in self._user_map:
            return self._user_map[user_id].display_name
        return f"User {roster_id}"

    def get_roster(self, roster_id: int) -> Roster | None:
        """Get roster by ID."""
        return self._roster_map.get(roster_id)

    def get_player(self, player_id: str) -> Player | None:
        """Get player by ID."""
        return self.players.get(player_id)

    def get_player_name(self, player_id: str) -> str:
        """Get player name from player ID."""
        player = self.players.get(player_id)
        if player:
            return player.display_name
        return player_id

    def get_player_position(self, player_id: str) -> str:
        """Get player position from player ID."""
        player = self.players.get(player_id)
        if player and player.position:
            return player.position
        return "Unknown"

    def get_player_team(self, player_id: str) -> str:
        """Get player's NFL team from player ID."""
        player = self.players.get(player_id)
        if player and player.team:
            return player.team
        return "FA"

    def roster_ids(self) -> list[int]:
        """Get all roster IDs in the league."""
        return list(self._roster_map.keys())
