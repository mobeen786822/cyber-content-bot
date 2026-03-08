# Cyber Content Bot

A cybersecurity content automation tool that aggregates CVEs, CISA advisories, and AI security research — then uses Claude to draft LinkedIn posts for review.

![Cyber Content Bot Dashboard](Screenshot.png)

## Features

- **Automated Data Collection** — Pulls high-severity CVEs, actively exploited vulnerabilities, and cutting-edge AI security research from three authoritative sources
- **AI-Powered Drafting** — Claude Haiku generates concise, professional LinkedIn posts from raw findings
- **Tone Control** — Regenerate drafts in professional, conversational, or technical tones
- **One-Click Manual Runs** — Trigger the pipeline on demand from the dashboard
- **Dark-Themed Dashboard** — React + Tailwind UI for reviewing drafts, browsing raw findings, and copying posts to clipboard
- **CI/CD Security Pipeline** — GitHub Actions runs Bandit SAST, pip-audit, and Gitleaks on every push

## Data Sources

| Source | What It Fetches | Filter |
|--------|----------------|--------|
| [NVD API](https://nvd.nist.gov/) | CVEs from the past 7 days | CVSS ≥ 7.0 (HIGH / CRITICAL), top 10 by score |
| [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | Known Exploited Vulnerabilities | Added in the past 7 days |
| [arXiv](https://arxiv.org/) | AI security research papers | Keywords: LLM, prompt injection, AI security |

## Project Structure

```
cyber-content-bot/
├── app.py                        # Flask API server (port 5058)
├── render.yaml                   # Render deployment blueprint
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
│
├── fetchers/
│   ├── nvd.py                    # NVD CVE fetcher
│   ├── cisa.py                   # CISA KEV fetcher
│   └── arxiv.py                  # arXiv paper fetcher
│
├── generator/
│   └── post_generator.py         # Claude Haiku post generation
│
├── client/                       # React + Vite frontend
│   ├── index.html
│   ├── vite.config.ts            # Vite config with Tailwind + API proxy
│   ├── src/
│   │   ├── App.tsx               # Dashboard UI
│   │   ├── api.ts                # Typed API client
│   │   ├── index.css             # Tailwind base styles
│   │   └── main.tsx              # React entry point
│   └── public/
│       └── favicon.svg           # Custom shield-and-lock icon
│
└── .github/
    └── workflows/
        └── security.yml          # Bandit, pip-audit, Gitleaks CI
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Backend

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and paste your Anthropic API key

# Start the Flask server
python app.py
```

The backend runs on **http://localhost:5058**. Click **Run Now** in the dashboard to fetch data and generate your first draft.

### Frontend

```bash
cd client
npm install
npm run dev
```

The Vite dev server starts on **http://localhost:5173** and proxies API requests to the Flask backend.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Last run time, finding count, cycle status |
| `POST` | `/run` | Manually trigger a fetch + generate cycle (409 if already running) |
| `GET` | `/draft` | Current draft text and raw findings from all sources |
| `POST` | `/draft/regenerate` | Re-generate the draft — accepts `{ "tone": "professional" \| "conversational" \| "technical" }` |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude Haiku |
| `FLASK_DEBUG` | No | Set to `1` to enable Flask debug mode (defaults to off) |
| `VITE_API_BASE` | No | Full backend URL for production builds (e.g. `https://cyber-content-bot-api.onrender.com`). In local dev, the Vite proxy handles routing automatically |

Copy `.env.example` to `.env` and add your key. The app uses `python-dotenv` with `override=True` so the `.env` file always takes precedence over shell environment variables.

## How It Works

1. Click **Run Now** from the dashboard to trigger a fetch + generate cycle
2. The bot fetches from all three data sources (NVD, CISA, arXiv)
3. Findings are passed to Claude Haiku, which drafts a 150–250 word LinkedIn post highlighting the 2–3 most notable items
4. The dashboard polls `/api/status` while a cycle is running, then loads the draft when complete
5. Review the draft, regenerate with a different tone, or copy to clipboard

## CI/CD

The GitHub Actions workflow (`.github/workflows/security.yml`) runs on every push and PR to `main`:

- **Bandit** — Static analysis for Python security issues (HIGH severity)
- **pip-audit** — Checks dependencies against known vulnerability databases
- **Gitleaks** — Scans for accidentally committed secrets and API keys

## Deployment (Render)

The project includes a `render.yaml` blueprint for one-click deployment to [Render](https://render.com):

| Service | Type | What It Does |
|---------|------|--------------|
| **cyber-content-bot-api** | Python Web Service | Flask backend on port 5058 |
| **cyber-content-bot-ui** | Static Site | React frontend built from `client/dist` |

To deploy:

1. Push the repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. Connect your repo — Render reads `render.yaml` automatically
4. Set `ANTHROPIC_API_KEY` when prompted for the backend
5. Set `VITE_API_BASE` to the backend's public URL (e.g. `https://cyber-content-bot-api.onrender.com`) for the frontend
6. Redeploy the frontend after setting `VITE_API_BASE` — it's a build-time variable

## Issues & Fixes

A log of problems encountered during development and deployment, and how each was resolved.

### `.env` file encoded as UTF-16 LE

**Problem:** Python's `load_dotenv` threw `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff` because the `.env` file was saved with UTF-16 LE encoding (BOM `ff fe`).

**Fix:** Converted the file to UTF-8 with `iconv` and stripped the BOM.

### API key returning 401 despite being set in `.env`

**Problem:** The Anthropic API returned `authentication_error: invalid x-api-key` even though the key was in `.env`. The root cause was that `ANTHROPIC_API_KEY` already existed as an empty string in the shell environment, and `load_dotenv()` doesn't override existing env vars by default.

**Fix:** Added `override=True` to the `load_dotenv()` call so the `.env` file always takes precedence.

### Bandit B201 — Flask debug mode hardcoded

**Problem:** Bandit flagged `debug=True` in `app.run()` as a high-severity issue ([B201](https://bandit.readthedocs.io/en/latest/plugins/b201_flask_debug_true.html)). Running Flask with debug mode exposes the Werkzeug debugger, which allows arbitrary code execution.

**Fix:** The debug flag now reads from the `FLASK_DEBUG` environment variable and defaults to **off**.

### pip-audit — 6 vulnerable dependencies

**Problem:** pip-audit flagged known CVEs in three packages.

**Fix:** Bumped all to patched versions:

| Package | Old | New | CVEs |
|---------|-----|-----|------|
| flask | 3.1.0 | 3.1.3 | CVE-2025-47278, CVE-2026-27205 |
| flask-cors | 5.0.1 | 6.0.0 | CVE-2024-6866, CVE-2024-6844, CVE-2024-6839 |
| requests | 2.32.3 | 2.32.4 | CVE-2024-47081 |

### APScheduler removed

**Problem:** The weekly cron scheduler added complexity and a dependency that wasn't needed for an on-demand tool.

**Fix:** Deleted `scheduler.py`, removed `apscheduler` from `requirements.txt`, and moved `run_cycle` into `app.py`. The pipeline now runs only when triggered via **Run Now**.

### Render blueprint — `PYTHON_VERSION` format

**Problem:** Render rejected `PYTHON_VERSION: "3.12"` with the error: *"must provide a major, minor, and patch version, e.g. 3.8.1"*.

**Fix:** Changed to the full semver format `"3.12.0"`.

### Render blueprint — static site definition

**Problem:** The initial `render.yaml` defined the frontend under a `staticSites` top-level key, which Render didn't recognise. A second attempt used `plan: static` under `services`, which also failed.

**Fix:** Static sites in Render blueprints use `type: web` with `runtime: static` under the `services` key.

### Frontend 404s on Render — `/api` prefix mismatch

**Problem:** The deployed static site called `/api/run`, `/api/status`, etc. In production there's no Vite proxy to rewrite these paths, so they returned 404. The `/api` prefix only worked in local dev where the proxy forwarded them to Flask.

**Fix:** Removed the `/api` prefix from all Flask routes (`/status`, `/run`, `/draft`, `/draft/regenerate`). Updated the frontend API client to use `VITE_API_BASE` (the full backend URL) in production, with an empty string fallback for local dev. Updated the Vite proxy to forward the bare paths individually.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask, Flask-CORS |
| Data Fetching | Requests, Feedparser |
| AI Generation | Anthropic SDK (Claude Haiku) |
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS v4 |
| CI/CD | GitHub Actions |
| Hosting | Render |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
