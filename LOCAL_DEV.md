# Local Development Guide

Test changes locally before deploying to Railway.

## Quick Start

### 1. Start the API Server

```bash
PYTHONPATH=/Users/michaelkwan/Documents/sleeper-analysis/src uv run uvicorn sleeper_analytics.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag means the server will auto-restart when you change Python code.

### 2. Open the Local Frontend

Open in your browser:
```
file:///Users/michaelkwan/Documents/sleeper-analysis/docs/app-local.html?id=1257152597513490432
```

Or use any league ID:
```
file:///Users/michaelkwan/Documents/sleeper-analysis/docs/app-local.html?id=YOUR_LEAGUE_ID
```

### 3. Make Changes & Test

**Frontend Changes:**
1. Edit `docs/app-local.html`
2. Refresh browser (Cmd+R)
3. See changes immediately

**Backend Changes:**
1. Edit Python files in `src/sleeper_analytics/`
2. Server auto-reloads
3. Refresh browser to see API changes

## API Endpoints

Once running locally, you can test API endpoints directly:

- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs
- Standings: http://localhost:8000/api/matchups/{league_id}/standings?weeks=14
- Awards: http://localhost:8000/api/awards/{league_id}/season?weeks=14
- Luck: http://localhost:8000/api/luck/{league_id}/league?weeks=14
- FAAB: http://localhost:8000/api/faab/{league_id}/report?weeks=14
- Benchwarmer: http://localhost:8000/api/benchwarmer/{league_id}/league?weeks=14

## Testing Workflow

1. Make backend changes
2. Test API endpoint in browser or with curl:
   ```bash
   curl http://localhost:8000/api/luck/1257152597513490432/league?weeks=14 | jq
   ```
3. Make frontend changes in `app-local.html`
4. Refresh browser to test
5. When everything works, copy changes to `app.html`
6. Commit and push to deploy to Railway

## Deploying Changes

**Frontend Only:**
```bash
# Copy local changes to production file
cp docs/app-local.html docs/app.html

# Update API_BASE back to Railway
# Edit docs/app.html and change:
# const API_BASE = 'http://localhost:8000';
# to:
# const API_BASE = 'https://sleeper-analysis-production.up.railway.app';

git add docs/app.html
git commit -m "Update frontend"
git push
```

**Backend Changes:**
```bash
# Just push - Railway auto-deploys
git add src/
git commit -m "Update backend"
git push
# Railway will automatically rebuild and deploy
```

## Tips

- Use browser DevTools (F12) to see console errors
- Check Network tab to see API requests/responses
- Use `--reload` flag so server restarts on code changes
- Test with multiple league IDs to catch edge cases
- `app-local.html` is gitignored so you won't accidentally deploy it

## Common Issues

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

**CORS errors:**
- Make sure API is running on port 8000
- Check browser console for actual error

**Module not found:**
- Make sure PYTHONPATH is set correctly
- Try: `uv sync` to reinstall dependencies
