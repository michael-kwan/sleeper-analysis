# TODO - Sleeper Analytics

## 🐛 Bugs to Fix

### FAAB Spending Shows Zero
- **Issue**: FAAB spending is showing as $0 in reports
- **Location**: `src/sleeper_analytics/services/faab.py`
- **Fix needed**: Debug waiver_budget parsing, check if field name is correct

### Benchwarmer Calculation Incorrect
- **Issue**: Should calculate actual point differential
- **Current**: Shows total bench points
- **Should be**: `bench_player_points - starter_points_in_that_slot`
- **Example**: If RB on bench scored 20 and starting RB scored 8, benchwamer cost = 12 points
- **Location**: `src/sleeper_analytics/services/benchwarmer.py`

## 🚀 New Features

### Trade Analysis - Player Ownership Timeline
- **Description**: Graphviz/timeline visualization showing how player ownership changed
- **Features**:
  - Visual tree/timeline of player movement
  - Show week-by-week ownership changes
  - Highlight trades vs waivers vs FA
  - Color-code by team
- **API Endpoint**: Already have `/api/transactions/{league_id}/player-tree/{player_id}`
- **Need**: Visualization layer (could use Plotly timeline or generate graphviz SVG)

### Trade Analysis - Most Lopsided Trades
- **Description**: Analyze trades by point differential before/after
- **Metrics**:
  - Pre-trade point balance between teams
  - Post-trade point production
  - Most imbalanced trades (who won/lost big)
  - Track points scored by traded players after the trade
- **New service needed**: `get_most_lopsided_trades()`
- **Models**: `LopsidedTradeAnalysis`

### Roster Construction Analysis
- **Description**: Where did each manager's points come from?
- **Breakdown by source**:
  - Draft picks: % of points from drafted players
  - Trades: % of points from acquired players
  - Waivers: % of points from waiver pickups
  - Free agents: % of points from FA pickups
- **New service needed**: `analyze_roster_construction()`
- **Visualization**: Stacked bar chart or pie chart per team

### Draft Analysis
- **Description**: Who drafted the best? Who drafted the worst?
- **Metrics**:
  - Total points from drafted players
  - Points per draft pick
  - Best pick by round
  - Worst pick by round
  - Hit rate (% of picks that produced)
- **Need**: Draft data from Sleeper API
- **New service**: `DraftAnalysisService`
- **Endpoint**: `/api/draft/{league_id}/analysis`

## 🔮 Future Enhancements

### Custom Scoring Recalculation
- **Description**: Recalculate entire season with different scoring formats
- **Formats**: 0.5 PPR, 1.0 PPR, 1.5 TE PPR
- **Need**: Integration with `nfl-data-py` for raw stats
- **Service**: `ScoringService`
- **Status**: Deferred

## 📋 Implementation Order (Recommended)

1. **Fix FAAB bug** - Critical, affects existing feature
2. **Fix benchwarmer calculation** - Critical, incorrect data
3. **Roster construction analysis** - Medium complexity, high value
4. **Draft analysis** - Requires draft data integration
5. **Lopsided trades analysis** - Builds on existing trade service
6. **Player ownership timeline visualization** - Complex, visual enhancement
7. **Custom scoring** - Most complex, lowest priority

## 🔍 Investigation Needed

### FAAB Bug Investigation
```python
# Check in FAABService.get_owner_faab_performance()
# Lines 214-218 in src/sleeper_analytics/services/faab.py
if txn.is_waiver and txn.waiver_budget:
    for wb in txn.waiver_budget:
        if wb.receiver == roster_id:
            faab = wb.amount
            break
```
- Is `waiver_budget` populated?
- Is `wb.amount` the correct field?
- Check actual transaction response from Sleeper API

### Benchwarmer Investigation
```python
# In BenchwarmerService.analyze_team_bench()
# Need to:
# 1. Get actual starter points for that position slot
# 2. Calculate differential = bench_points - starter_points
# 3. Only count positive differentials (cases where bench was better)
```

## 📝 Notes

- All new features should follow existing architectural patterns
- Use dependency injection for services
- Add models to `src/sleeper_analytics/models/`
- Test locally with `generate_reports.py` before deploying
- Update API docs in main.py root endpoint
