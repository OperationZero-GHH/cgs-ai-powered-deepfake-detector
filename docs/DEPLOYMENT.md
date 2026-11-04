# Deployment Guide — CGS DeepFake Shield

## Architecture Overview

CGS DeepFake Shield is a monorepo with two services:

| Service | Directory | Runtime | Deployment Target |
|---------|-----------|---------|-------------------|
| Frontend (Next.js) | `apps/web/` | Node.js 20+ | **Vercel** |
| Backend API (FastAPI) | `apps/api/` | Python 3.11+ | Railway, Render, Fly.io, or any container host |

> [!IMPORTANT]
> The Python API backend **cannot** run on Vercel. It requires a persistent process for model inference workers and a SQLite/PostgreSQL database.

## Frontend — Vercel Deployment

### 1. Connect Repository

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Vercel will auto-detect the `vercel.json` configuration

### 2. Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_API_ORIGIN` | **Yes** | Full HTTPS origin of your API backend (e.g., `https://api.yourdomain.com`). Must not include a path or trailing slash. |

### 3. How It Works

- The `vercel.json` sets `rootDirectory` to `apps/web/`, so Vercel builds only the Next.js frontend.
- API requests to `/api/*` are rewritten (proxied) to `NEXT_API_ORIGIN` via Next.js rewrites in `next.config.ts`.
- The CSP `connect-src` allows `'self'`, so API calls through the rewrite proxy are permitted.

### 4. Build Settings (Auto-Configured)

- **Framework:** Next.js (auto-detected)
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Install Command:** `npm install`

## Backend API — Deployment

The FastAPI backend needs:
- Python 3.11+
- Persistent filesystem (for SQLite) or PostgreSQL
- Optional: Redis for scaling beyond a single worker
- ffmpeg installed (for audio/video processing)

### Recommended Platforms

- **Railway** — `railway up` from `apps/api/`
- **Render** — Docker or native Python runtime
- **Fly.io** — `fly launch` with Dockerfile
- **Any VPS/container host** — Docker or systemd

### Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Prod | `sqlite:///./cgs.db` | PostgreSQL connection string for production |
| `SESSION_SECRET` | **Yes** | — | Random 64+ char secret for session signing |
| `ADMIN_EMAILS` | No | — | Comma-separated admin email addresses |
| `STORAGE_DIR` | No | `./storage` | Path for temporary upload storage |
| `HF_HUB_OFFLINE` | Prod | `1` | Must be `1` in production (models pre-downloaded) |
| `TRANSFORMERS_OFFLINE` | Prod | `1` | Must be `1` in production |
| `UPLOAD_RETENTION_HOURS` | No | `1` | Hours before uploaded media is auto-purged |
| `MAX_UPLOAD_SIZE_BYTES` | No | `10485760` | Maximum upload size (10 MB default) |
| `ENABLE_HARSHASNADE_MODEL` | No | `false` | Enable the Harshasnade hybrid model (license unspecified) |

### CORS Configuration

Set `CORS_ORIGINS` to your Vercel frontend URL (e.g., `https://your-app.vercel.app`).

## Security Notes

- The API enforces HTTPS for `NEXT_API_ORIGIN` on Vercel deployments.
- All session cookies use `Secure`, `HttpOnly`, and `SameSite=Lax` attributes.
- Rate limiting is applied at the application level; consider adding edge rate limits (e.g., Cloudflare, Vercel WAF) for additional protection.
- Model inference runs offline — no outbound network access from workers.
