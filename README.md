# Sleeper Analytics API

A FastAPI-based analytics platform for Sleeper fantasy football leagues featuring transaction analysis, matchup breakdowns, roster efficiency metrics, and trade value calculations.

## Features

- 📊 **League Analysis** - Standings, rosters, and league settings
- 🔄 **Transaction Tracking** - Trades, waivers, and free agent moves
- 🏈 **Matchup Analysis** - Weekly scores, head-to-head records, close games
- ⚡ **Roster Efficiency** - Optimal lineup vs actual lineup comparisons
- 💰 **Trade Value** - Player and pick value calculations using NFL stats

## Tech Stack

- **Package Manager**: uv
- **API Framework**: FastAPI + Uvicorn
- **HTTP Client**: httpx (async)
- **Data Processing**: pandas, numpy
- **NFL Stats**: nfl-data-py
- **Visualization**: Plotly

## Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) as the package manager. Install it first:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Or with pip
pip install uv
```

## Installation

```bash
# Clone the repository
cd sleeper-analytics

# Install dependencies with uv
uv sync

# Or with dev dependencies
uv sync --dev

# Configure your leagues (optional)
cp leagues.json.example leagues.json
# Edit leagues.json with your league IDs
```

## Running the API

```bash
# Using the CLI entry point
uv run sleeper-api

# Or directly with uvicorn
uv run uvicorn sleeper_analytics.main:app --reload

# With custom host/port
uv run uvicorn sleeper_analytics.main:app --host 0.0.0.0 --port 8080 --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

All settings can be configured via environment variables with the `SLEEPER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SLEEPER_DEBUG` | `false` | Enable debug mode |
| `SLEEPER_DEFAULT_SEASON` | `2024` | Default NFL season |
| `SLEEPER_HOST` | `0.0.0.0` | Server host |
| `SLEEPER_PORT` | `8000` | Server port |
| `SLEEPER_PLAYERS_CACHE_TTL` | `3600` | Player cache TTL in seconds |

## Project Structure

```
src/sleeper_analytics/
├── main.py              # FastAPI application entry
├── config.py            # Settings and configuration
├── api/
│   └── routes/          # API route handlers
│       ├── leagues.py
│       ├── transactions.py
│       ├── matchups.py
│       ├── efficiency.py
│       └── trades.py
├── clients/
│   └── sleeper.py       # Async Sleeper API client
├── services/            # Business logic
│   ├── nfl_stats.py
│   ├── matchups.py
│   ├── efficiency.py
│   └── trades.py
├── models/              # Pydantic schemas
│   ├── league.py
│   ├── matchup.py
│   ├── player.py
│   └── transaction.py
└── visualization/       # Plotly chart generators
    └── charts.py
```

## Quick Start Example

```python
import asyncio
from sleeper_analytics.clients import SleeperClient, LeagueContext

async def main():
    async with SleeperClient() as client:
        # Get user info
        user = await client.get_user("your_username")
        print(f"User: {user.display_name}")

        # Get leagues
        leagues = await client.get_user_leagues(user.user_id, 2024)
        for league in leagues:
            print(f"League: {league.name}")

        # Create league context for detailed analysis
        if leagues:
            ctx = await LeagueContext.create(client, leagues[0].league_id)
            print(f"Teams: {len(ctx.rosters)}")

asyncio.run(main())
```

## License

MIT
