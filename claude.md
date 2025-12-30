# Sleeper Analytics API - Claude Code Context

## Project Overview

This is a **FastAPI-based analytics platform** for Sleeper fantasy football leagues. It provides comprehensive analytics including transaction analysis, matchup breakdowns, roster efficiency metrics, and trade value calculations using NFL stats.

**Primary Goal**: Enable deep insights into fantasy football league data through a RESTful API with interactive visualizations.

## Tech Stack & Dependencies

### Core Framework
- **Package Manager**: `uv` (modern Python package manager)
- **Python Version**: 3.12+
- **API Framework**: FastAPI 0.115+ with Uvicorn (ASGI server)
- **HTTP Client**: httpx (async, with connection pooling)

### Data & Analytics
- **Data Processing**: pandas 2.2+, numpy 2.0+
- **NFL Stats**: nfl-data-py 0.3+ (real NFL stats integration)
- **Validation**: Pydantic 2.10+ (runtime type checking and settings)
- **Visualization**: Plotly 5.24+ (interactive charts)

### Code Quality
- **Linter/Formatter**: Ruff (line length: 100, target: py312)
- **Testing**: pytest with pytest-asyncio

## Architecture Overview

### Layered Architecture

```
API Layer (FastAPI routes)
    ↓
Service Layer (business logic)
    ↓
Client Layer (Sleeper API integration)
    ↓
Models (Pydantic schemas)
```

### Key Design Patterns

1. **Async-First**: All I/O operations are async (httpx, concurrent API calls)
2. **Dependency Injection**: FastAPI's DI system for clients, contexts, and services
3. **Factory Pattern**: Application factory in `create_app()` for testability
4. **Context Object Pattern**: `LeagueContext` caches league data and provides lookup methods
5. **Singleton Client**: `ClientManager` maintains a single SleeperClient instance across requests
6. **Class-Level Caching**: Player data cached at class level with TTL

## Directory Structure

```
src/sleeper_analytics/
├── main.py                    # FastAPI app factory & entry point
├── config.py                  # Pydantic settings (env vars with SLEEPER_ prefix)
├── cli.py                     # CLI entry point (sleeper-cli command)
│
├── api/
│   ├── dependencies.py        # FastAPI dependencies (client, context, NFL stats)
│   └── routes/                # API route handlers (one file per domain)
│       ├── leagues.py         # League info, rosters, standings
│       ├── transactions.py    # Trades, waivers, free agent moves
│       ├── matchups.py        # Weekly matchups, head-to-head records
│       ├── efficiency.py      # Optimal vs actual lineup analysis
│       ├── trades.py          # Trade value calculations
│       └── viz.py             # Plotly visualization endpoints
│
├── clients/
│   └── sleeper.py             # Async Sleeper API client + LeagueContext helper
│
├── services/                  # Business logic layer
│   ├── nfl_stats.py           # NFL stats service (nfl-data-py wrapper)
│   ├── matchups.py            # Matchup analysis logic
│   ├── efficiency.py          # Roster efficiency calculations
│   └── trades.py              # Trade value calculations
│
├── models/                    # Pydantic models (API contracts & validation)
│   ├── league.py              # League, User, Roster, NFLState
│   ├── matchup.py             # Matchup, Standing, HeadToHead
│   ├── player.py              # Player model
│   └── transaction.py         # Transaction, TransactionType, TransactionStatus
│
└── visualization/
    └── charts.py              # Plotly chart generators
```

## Coding Patterns & Conventions

### 1. Async Patterns

**Always use async for I/O operations**:
```python
async def get_data(client: SleeperClient):
    # Use async client
    user = await client.get_user("username")

    # Concurrent requests with asyncio.gather
    leagues, rosters, players = await asyncio.gather(
        client.get_user_leagues(user_id, 2024),
        client.get_league_rosters(league_id),
        client.get_all_players()
    )
```

### 2. Client Management

**SleeperClient MUST be used as async context manager**:
```python
# In standalone scripts
async with SleeperClient() as client:
    user = await client.get_user("username")

# In FastAPI routes - use dependency injection
async def my_route(client: SleeperClientDep):
    # Client is managed by ClientManager singleton
    user = await client.get_user("username")
```

### 3. FastAPI Route Patterns

**Standard route structure**:
```python
@router.get(
    "/{league_id}/endpoint",
    response_model=ResponseModel,
    summary="Short description",
    description="Detailed description"
)
async def route_handler(
    ctx: LeagueContextDep,  # Auto-creates LeagueContext from league_id
    client: SleeperClientDep,  # Singleton client
    param: Annotated[int, Query(description="Param desc", ge=1)] = 10,
) -> ResponseModel:
    """Docstring for route."""
    # Implementation
```

### 4. Dependency Injection Types

**Use these type aliases** (defined in `api/dependencies.py`):
- `SleeperClientDep` - Singleton Sleeper API client
- `LeagueContextDep` - Auto-fetches league data, raises 404 if not found
- `NFLStatsDep` - NFL stats service for a season
- `SettingsDep` - App settings
- `WeeksQuery` - Validated weeks query param (1-18)
- `SeasonQuery` - Validated season query param (2020-2030)

### 5. LeagueContext Usage

**LeagueContext provides convenient lookups**:
```python
async def analyze_league(ctx: LeagueContextDep):
    # Access league data
    league_name = ctx.league_name

    # Get team/user info
    team_name = ctx.get_team_name(roster_id)
    display_name = ctx.get_user_display_name(roster_id)

    # Get player info
    player = ctx.get_player(player_id)
    player_name = ctx.get_player_name(player_id)
    position = ctx.get_player_position(player_id)
    nfl_team = ctx.get_player_team(player_id)

    # Iterate rosters
    for roster_id in ctx.roster_ids():
        roster = ctx.get_roster(roster_id)
```

### 6. Pydantic Models

**All models use Pydantic BaseModel**:
- Use `Field()` for aliases, defaults, and descriptions
- Add `@property` methods for computed fields
- Use `model_config` for model-level configuration
- Default to `dict` for flexible nested structures from API

Example:
```python
class MyModel(BaseModel):
    field_name: str = Field(alias="api_field_name", description="Help text")
    optional_field: int | None = None
    nested_dict: dict = Field(default_factory=dict)

    @property
    def computed_value(self) -> float:
        return self.field_name.upper()
```

### 7. Configuration

**All settings use environment variables**:
- Prefix: `SLEEPER_` (e.g., `SLEEPER_DEBUG=true`)
- Can use `.env` file (loaded automatically)
- Access via `get_settings()` (cached with `@lru_cache`)

### 8. Error Handling

**SleeperAPIError for API failures**:
```python
# In SleeperClient
if response.status_code != 200:
    raise SleeperAPIError(
        f"API request failed: {endpoint}",
        status_code=response.status_code
    )

# In routes - FastAPI converts to HTTPException
```

**Graceful degradation in batch operations**:
```python
# gather with return_exceptions=True to avoid failing all requests
results = await asyncio.gather(*tasks, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        # Handle error gracefully
        continue
```

### 9. Caching Strategy

**Player cache** (class-level with TTL):
- Players cached at `SleeperClient._players_cache` (shared across instances)
- TTL controlled by `SLEEPER_PLAYERS_CACHE_TTL` (default: 3600s)
- Use `force_refresh=True` to invalidate

**No caching** for:
- League data (changes frequently during season)
- Matchups/transactions (real-time data)
- User rosters (roster changes common)

## Development Workflow

### Running the API
```bash
# Preferred method (uses CLI entry point)
uv run sleeper-api

# Direct uvicorn (for custom host/port)
uv run uvicorn sleeper_analytics.main:app --reload --host 0.0.0.0 --port 8080
```

### Running Tests
```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_client.py
```

### Code Quality
```bash
# Format and lint
uv run ruff check .
uv run ruff format .
```

### Package Management
```bash
# Add dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update all dependencies
uv sync --upgrade
```

## Key Concepts

### 1. Sleeper API Integration

The Sleeper API (https://docs.sleeper.com/) provides:
- User/league/roster data
- Matchup scores by week
- Transaction history
- Draft data
- All NFL players (~15MB payload)

**Important**:
- No authentication required for public league data
- Rate limits exist (be respectful with concurrent requests)
- Player data is large - use caching
- Matchup data only available for completed weeks

### 2. LeagueContext Helper

**Why LeagueContext exists**:
- Fetches all required league data in parallel (league, users, rosters, players)
- Caches data for the request lifetime
- Provides convenient lookup methods (roster_id → team_name)
- Reduces boilerplate in route handlers

**When to use**:
- Use `LeagueContextDep` in routes that need league data
- Creates context automatically from `league_id` path param
- Raises 404 if league not found

### 3. NFL Stats Integration

**nfl-data-py provides**:
- Weekly player stats
- Play-by-play data
- Team stats
- Historical data back to 1999

**Usage**:
```python
async def calculate_trade_value(stats: NFLStatsDep):
    # NFLStatsService wraps nfl-data-py
    weekly_stats = stats.get_weekly_data()
    player_value = stats.calculate_player_value(player_id)
```

### 4. Concurrency Patterns

**Always fetch multiple weeks/resources in parallel**:
```python
# Good - parallel fetching
matchups_by_week = await client.get_matchups_range(league_id, 1, 17)

# Bad - sequential fetching
for week in range(1, 18):
    matchups = await client.get_matchups(league_id, week)  # Slow!
```

## API Endpoint Structure

All endpoints under `/api` prefix:
- `/api/leagues` - League info, rosters, standings
- `/api/transactions` - Trade, waiver, and free agent analysis
- `/api/matchups` - Weekly scores, records, close games
- `/api/efficiency` - Optimal vs actual lineup comparisons
- `/api/trades` - Player/pick value calculations
- `/api/viz` - Plotly chart HTML endpoints

**Interactive docs**: http://localhost:8000/docs

## Important Notes for AI Assistance

1. **Always use async/await** for I/O operations
2. **Use dependency injection** in routes instead of creating clients manually
3. **LeagueContextDep** automatically validates league_id and creates context
4. **Type hints are required** - this is a Pydantic-heavy codebase
5. **Don't cache league data** - it changes during the season
6. **Do cache player data** - it's large and mostly static
7. **Use asyncio.gather()** for concurrent API calls
8. **Follow FastAPI patterns** - response_model, Path/Query annotations, etc.
9. **Environment variables** must have `SLEEPER_` prefix
10. **Line length limit**: 100 characters (enforced by Ruff)

## Common Tasks

### Adding a new API endpoint
1. Create route in appropriate file under `api/routes/`
2. Define response model in `models/`
3. Implement business logic in `services/` if complex
4. Use dependency injection for client/context
5. Register router in `main.py` if new route file

### Adding a new Sleeper API method
1. Add method to `SleeperClient` class
2. Follow naming pattern: `get_*`, `get_all_*`, `get_*_range`
3. Return Pydantic models (not raw dicts) when possible
4. Handle 404s gracefully (return None or empty list)
5. Use async/await

### Adding a new model
1. Create in appropriate file under `models/`
2. Inherit from `BaseModel`
3. Use `Field()` for API aliases and defaults
4. Add `@property` methods for computed fields
5. Keep models flat - use `dict` for deeply nested API responses

### Working with NFL stats
1. Get service via `NFLStatsDep` dependency
2. Service is season-aware (from query param)
3. Data cached per season
4. Returns pandas DataFrames for analysis

## Entry Points

Defined in `pyproject.toml`:
- `sleeper-api` → `sleeper_analytics.main:run` (starts API server)
- `sleeper-cli` → `sleeper_analytics.cli:run_cli` (CLI tool)

Run with: `uv run sleeper-api` or `uv run sleeper-cli`
