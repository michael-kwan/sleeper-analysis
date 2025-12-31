# Deployment Guide

## Railway Deployment (Recommended)

Railway provides free hosting for the FastAPI backend with automatic deployments from GitHub.

### Steps:

1. **Sign up for Railway**
   - Go to [railway.app](https://railway.app)
   - Sign in with your GitHub account

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `michael-kwan/sleeper-analysis`

3. **Configure the Service**
   - Railway will auto-detect Python and use `railway.json` config
   - No additional configuration needed!

4. **Get Your API URL**
   - Once deployed, Railway will give you a URL like: `sleeper-analysis-production.up.railway.app`
   - Click "Generate Domain" if it doesn't auto-generate

5. **Update GitHub Pages**
   - Copy your Railway URL
   - Update `docs/app.html` to use your Railway API URL instead of PyScript

### Environment Variables (Optional)

No environment variables are required for basic functionality. All settings have sensible defaults.

If you want to customize:
- `SLEEPER_DEBUG`: Set to `true` for debug mode
- `SLEEPER_DEFAULT_SEASON`: Override default season (defaults to 2024)

### Cost

**Free Tier:**
- 500 hours/month (enough for hobby projects)
- Auto-sleeps after inactivity
- Perfect for this use case

## Alternative: Render

1. Go to [render.com](https://render.com)
2. New > Web Service
3. Connect GitHub repo
4. Build command: `pip install -e .`
5. Start command: `uvicorn sleeper_analytics.main:app --host 0.0.0.0 --port $PORT`

## Alternative: Fly.io

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Run: `fly launch`
3. Follow prompts (it will auto-detect Python)
4. Deploy: `fly deploy`

## Verify Deployment

Once deployed, test your API:
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status": "healthy", "version": "0.1.0"}
```

## Updating GitHub Pages

After deploying to Railway, update your frontend in `docs/app.html` to call your Railway API instead of using PyScript.
