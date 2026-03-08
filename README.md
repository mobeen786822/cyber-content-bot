# Cyber Content Bot

Weekly cybersecurity content bot that pulls CVEs, CISA advisories, and AI security research, then uses Claude to draft LinkedIn posts for review.

## Data Sources

- **NVD API** — CVEs from the past 7 days with CVSS >= 7.0 (HIGH/CRITICAL)
- **CISA KEV** — Known Exploited Vulnerabilities added in the past 7 days
- **arXiv** — Recent AI security papers (LLM, prompt injection, AI security)

## Setup

### Backend

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Anthropic API key
python app.py
```

The Flask server runs on port **5058**.

### Frontend

```bash
cd client
npm install
npm run dev
```

The Vite dev server proxies API calls to the Flask backend.

## How It Works

1. **APScheduler** runs a fetch + generate cycle every Monday at 8am
2. On startup, if no draft exists, an immediate run is triggered
3. The bot fetches from all three sources, then calls Claude Haiku to draft a LinkedIn post
4. Review and regenerate drafts from the web dashboard

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Last run time, finding count, scheduler status |
| POST | `/api/run` | Manually trigger a full fetch + generate cycle |
| GET | `/api/draft` | Current draft and raw findings |
| POST | `/api/draft/regenerate` | Re-generate draft with optional tone parameter |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude |
