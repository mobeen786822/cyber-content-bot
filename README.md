# Cyber Content Bot

A weekly cybersecurity content automation tool that aggregates CVEs, CISA advisories, and AI security research — then uses Claude to draft LinkedIn posts for review.

![Cyber Content Bot Dashboard](Screenshot.png)

## Features

- **Automated Data Collection** — Pulls high-severity CVEs, actively exploited vulnerabilities, and cutting-edge AI security research from three authoritative sources
- **AI-Powered Drafting** — Claude Haiku generates concise, professional LinkedIn posts from raw findings
- **Tone Control** — Regenerate drafts in professional, conversational, or technical tones
- **Weekly Scheduling** — APScheduler triggers a full fetch-and-draft cycle every Monday at 8 AM
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
├── scheduler.py                  # APScheduler — weekly cron + startup run
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

The backend runs on **http://localhost:5058**. On first startup, it automatically fetches data and generates an initial draft.

### Frontend

```bash
cd client
npm install
npm run dev
```

The Vite dev server starts on **http://localhost:5173** and proxies all `/api` requests to the Flask backend.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Last run time, finding count, scheduler state, cycle status |
| `POST` | `/api/run` | Manually trigger a fetch + generate cycle (409 if already running) |
| `GET` | `/api/draft` | Current draft text and raw findings from all sources |
| `POST` | `/api/draft/regenerate` | Re-generate the draft — accepts `{ "tone": "professional" \| "conversational" \| "technical" }` |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key for Claude Haiku |

Copy `.env.example` to `.env` and add your key. The app uses `python-dotenv` with `override=True` so the `.env` file always takes precedence over shell environment variables.

## How It Works

1. **APScheduler** runs a full fetch + generate cycle every Monday at 8:00 AM
2. On startup, if no draft exists, an immediate cycle runs in a background thread
3. The bot fetches from all three data sources concurrently
4. Findings are passed to Claude Haiku, which drafts a 150–250 word LinkedIn post highlighting the 2–3 most notable items
5. The dashboard polls `/api/status` while a cycle is running, then loads the draft when complete
6. Review the draft, regenerate with a different tone, or copy to clipboard

## CI/CD

The GitHub Actions workflow (`.github/workflows/security.yml`) runs on every push and PR to `main`:

- **Bandit** — Static analysis for Python security issues (HIGH severity)
- **pip-audit** — Checks dependencies against known vulnerability databases
- **Gitleaks** — Scans for accidentally committed secrets and API keys

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask, Flask-CORS |
| Data Fetching | Requests, Feedparser |
| AI Generation | Anthropic SDK (Claude Haiku) |
| Scheduling | APScheduler |
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS v4 |
| CI/CD | GitHub Actions |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
