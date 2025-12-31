# Local Development Guide

Test changes locally by generating static HTML reports before deploying.

## Quick Start

### 1. Make Your Changes

Edit Python files in `src/sleeper_analytics/` (models, services, routes, etc.)

### 2. Generate Reports Locally

```bash
PYTHONPATH=/Users/michaelkwan/Documents/sleeper-analysis/src $HOME/.local/bin/uv run python generate_reports.py
```

This will:
- Read leagues from `leagues.json`
- Fetch all analytics data
- Generate static HTML reports in `docs/` folder
- Create reports for each league + index page

### 3. Test in Browser

Open the generated HTML files:

```bash
open docs/tip-your-runningbacks.html
open docs/supa-flexas.html
open docs/index.html
```

Or just double-click them in Finder.

### 4. Verify Everything Works

Check:
- ✅ All tables render correctly
- ✅ No "undefined" values
- ✅ Charts display properly
- ✅ Data looks accurate

### 5. Deploy When Ready

```bash
git add .
git commit -m "Your changes"
git push
```

Railway will auto-deploy the backend, GitHub Pages will update the frontend.

## Testing Workflow

```bash
# 1. Edit Python code
vim src/sleeper_analytics/services/luck_analysis.py

# 2. Generate reports
PYTHONPATH=src uv run python generate_reports.py

# 3. Open in browser
open docs/tip-your-runningbacks.html

# 4. See the changes, fix bugs

# 5. Repeat 2-4 until perfect

# 6. Commit and push
git add . && git commit -m "Fix luck analysis" && git push
```

## Adding New Analytics

1. Create models in `src/sleeper_analytics/models/`
2. Create service in `src/sleeper_analytics/services/`
3. Create API route in `src/sleeper_analytics/api/routes/`
4. Update `generate_reports.py` to fetch new data
5. Update HTML template in `generate_reports.py` to display it
6. Test locally: `PYTHONPATH=src uv run python generate_reports.py`
7. Open HTML, verify it works
8. Commit and push

## Advantages

- ✅ No server to run
- ✅ No CORS issues
- ✅ Fast iteration
- ✅ See exactly what users will see
- ✅ Test with real data from your leagues
- ✅ Catch bugs before deployment

## Testing With Different Leagues

Edit `leagues.json` to add test leagues:

```json
{
  "leagues": [
    {"id": "1257152597513490432", "name": "tip your runningbacks", "season": 2025},
    {"id": "1261570852047040512", "name": "supa flexas", "season": 2025},
    {"id": "ANY_OTHER_LEAGUE_ID", "name": "test league", "season": 2025}
  ]
}
```

Then run generate_reports.py to create reports for all of them.

## Common Issues

**ModuleNotFoundError:**
```bash
# Make sure PYTHONPATH is set
PYTHONPATH=/Users/michaelkwan/Documents/sleeper-analysis/src uv run python generate_reports.py
```

**Old data showing:**
- Delete `docs/*.html` files and regenerate

**Styling broken:**
- Check that CSS is embedded in the HTML template
- Look at `generate_reports.py` template strings

## Pro Tips

- Use `grep` to find field names in models: `grep -r "class.*BaseModel" src/sleeper_analytics/models/`
- Check API responses: Look at the service code to see what data structure is returned
- Test edge cases: Use leagues with different sizes, settings, weeks played
- Keep `leagues.json` gitignored so you can add test leagues freely
