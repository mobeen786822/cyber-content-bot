# Cyber Content Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack cybersecurity content bot that fetches CVEs, CISA advisories, and arXiv papers weekly, uses Claude to draft LinkedIn posts, and provides a React dashboard for review.

**Architecture:** Flask backend with 3 fetcher modules (NVD, CISA KEV, arXiv), a Claude-powered post generator, and APScheduler for weekly runs. React/Vite/Tailwind frontend proxies API calls through Vite dev server. All state in memory.

**Tech Stack:** Python/Flask, APScheduler, Anthropic SDK, React 18, Vite, Tailwind CSS, GitHub Actions

---

### Task 1: Backend Scaffolding & Config

**Files:**
- Create: `app.py`
- Create: `fetchers/__init__.py`
- Create: `generator/__init__.py`
- Create: `requirements.txt`
- Create: `.env.example`

**Step 1: Create requirements.txt**

```
flask==3.1.0
flask-cors==5.0.1
requests==2.32.3
anthropic==0.43.0
python-dotenv==1.0.1
apscheduler==3.10.4
feedparser==6.0.11
```

**Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Step 3: Create fetchers/__init__.py**

```python
```

(Empty init file)

**Step 4: Create generator/__init__.py**

```python
```

(Empty init file)

**Step 5: Create app.py with Flask skeleton and in-memory store**

```python
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / '.env')

app = Flask(__name__)
CORS(app)

# In-memory store
store = {
    "last_run": None,
    "findings": {
        "nvd": [],
        "cisa": [],
        "arxiv": [],
    },
    "draft": None,
    "scheduler_running": False,
    "next_run": None,
}
store_lock = threading.Lock()


@app.route("/api/status")
def status():
    with store_lock:
        return jsonify({
            "last_run": store["last_run"],
            "num_findings": (
                len(store["findings"]["nvd"])
                + len(store["findings"]["cisa"])
                + len(store["findings"]["arxiv"])
            ),
            "has_draft": store["draft"] is not None,
            "scheduler_running": store["scheduler_running"],
            "next_run": store["next_run"],
        })


@app.route("/api/run", methods=["POST"])
def run():
    from scheduler import run_cycle
    thread = threading.Thread(target=run_cycle, args=(store, store_lock))
    thread.start()
    return jsonify({"message": "Cycle started"}), 202


@app.route("/api/draft")
def get_draft():
    with store_lock:
        return jsonify({
            "draft": store["draft"],
            "findings": store["findings"],
        })


@app.route("/api/draft/regenerate", methods=["POST"])
def regenerate_draft():
    tone = request.json.get("tone", "professional") if request.is_json else "professional"
    from generator.post_generator import generate_post
    with store_lock:
        findings = store["findings"]
    draft = generate_post(findings, tone=tone)
    with store_lock:
        store["draft"] = draft
    return jsonify({"draft": draft})


if __name__ == "__main__":
    from scheduler import init_scheduler
    init_scheduler(app, store, store_lock)
    app.run(host="0.0.0.0", port=5058, debug=True, use_reloader=False)
```

**Step 6: Commit**

```bash
git add requirements.txt .env.example app.py fetchers/__init__.py generator/__init__.py
git commit -m "feat: backend scaffolding with Flask app, config, and in-memory store"
```

---

### Task 2: NVD CVE Fetcher

**Files:**
- Create: `fetchers/nvd.py`

**Step 1: Implement NVD fetcher**

```python
import requests
from datetime import datetime, timedelta, timezone


def fetch_nvd_cves():
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    params = {
        "pubStartDate": week_ago.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
    }

    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"NVD fetch error: {e}")
        return []

    cves = []
    for item in data.get("vulnerabilities", []):
        cve_data = item.get("cve", {})
        cve_id = cve_data.get("id", "")

        # Extract CVSS score — try v3.1 first, then v3.0, then v2
        metrics = cve_data.get("metrics", {})
        cvss_score = None
        severity = None

        for version_key in ["cvssMetricV31", "cvssMetricV30"]:
            if version_key in metrics and metrics[version_key]:
                cvss_data = metrics[version_key][0].get("cvssData", {})
                cvss_score = cvss_data.get("baseScore")
                severity = cvss_data.get("baseSeverity")
                break

        if cvss_score is None or cvss_score < 7.0:
            continue

        # Extract description
        descriptions = cve_data.get("descriptions", [])
        description = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break

        # Extract affected products from CPE configurations
        affected_products = []
        configurations = cve_data.get("configurations", [])
        for config in configurations:
            for node in config.get("nodes", []):
                for cpe_match in node.get("cpeMatch", []):
                    criteria = cpe_match.get("criteria", "")
                    parts = criteria.split(":")
                    if len(parts) >= 5:
                        vendor = parts[3]
                        product = parts[4]
                        affected_products.append(f"{vendor}/{product}")

        cves.append({
            "cve_id": cve_id,
            "description": description,
            "cvss_score": cvss_score,
            "severity": severity,
            "affected_products": list(set(affected_products))[:5],
        })

    # Sort by CVSS score descending, limit to top 10
    cves.sort(key=lambda x: x["cvss_score"], reverse=True)
    return cves[:10]
```

**Step 2: Commit**

```bash
git add fetchers/nvd.py
git commit -m "feat: add NVD CVE fetcher with CVSS >= 7.0 filtering"
```

---

### Task 3: CISA KEV Fetcher

**Files:**
- Create: `fetchers/cisa.py`

**Step 1: Implement CISA KEV fetcher**

```python
import requests
from datetime import datetime, timedelta, timezone


def fetch_cisa_kev():
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"CISA KEV fetch error: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    advisories = []

    for vuln in data.get("vulnerabilities", []):
        date_added = vuln.get("dateAdded", "")
        try:
            added_dt = datetime.strptime(date_added, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue

        if added_dt < cutoff:
            continue

        advisories.append({
            "cve_id": vuln.get("cveID", ""),
            "vulnerability_name": vuln.get("vulnerabilityName", ""),
            "vendor_project": vuln.get("vendorProject", ""),
            "product": vuln.get("product", ""),
            "required_action": vuln.get("requiredAction", ""),
            "due_date": vuln.get("dueDate", ""),
        })

    return advisories
```

**Step 2: Commit**

```bash
git add fetchers/cisa.py
git commit -m "feat: add CISA KEV fetcher with 7-day recency filter"
```

---

### Task 4: arXiv Paper Fetcher

**Files:**
- Create: `fetchers/arxiv.py`

**Step 1: Implement arXiv fetcher**

```python
import feedparser


def fetch_arxiv_papers():
    query = "cat:cs.CR+AND+(LLM+OR+prompt+injection+OR+AI+security)"
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results=5"
    )

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"arXiv fetch error: {e}")
        return []

    papers = []
    for entry in feed.entries:
        authors = [a.get("name", "") for a in entry.get("authors", [])]
        papers.append({
            "title": entry.get("title", "").replace("\n", " ").strip(),
            "summary": entry.get("summary", "").replace("\n", " ").strip()[:500],
            "authors": authors[:5],
            "link": entry.get("link", ""),
        })

    return papers
```

**Step 2: Commit**

```bash
git add fetchers/arxiv.py
git commit -m "feat: add arXiv AI security paper fetcher"
```

---

### Task 5: Claude Post Generator

**Files:**
- Create: `generator/post_generator.py`

**Step 1: Implement post generator**

```python
import os
import json
from anthropic import Anthropic


SYSTEM_PROMPT = (
    "You are a cybersecurity content writer helping a graduate security engineer "
    "build their LinkedIn presence. Write in a direct, technical but accessible tone. "
    "No fluff, no hype. Focus on what's genuinely interesting or important."
)


def generate_post(findings, tone="professional"):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    client = Anthropic(api_key=api_key)

    tone_instruction = {
        "professional": "Use a professional, polished tone suitable for LinkedIn.",
        "conversational": "Use a conversational, approachable tone — like talking to a peer over coffee.",
        "technical": "Use a deeply technical tone with specific details, for a security-savvy audience.",
    }.get(tone, "Use a professional, polished tone suitable for LinkedIn.")

    findings_text = json.dumps(findings, indent=2)

    user_prompt = f"""Here are this week's cybersecurity findings from three sources:

{findings_text}

Based on these findings, identify the 2-3 most interesting or important items across all three sources. Then draft a LinkedIn post of 150-250 words.

{tone_instruction}

Include relevant hashtags at the end. Do not use emojis. Focus on providing genuine insight or awareness, not just listing CVEs."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text
```

**Step 2: Commit**

```bash
git add generator/post_generator.py
git commit -m "feat: add Claude-powered LinkedIn post generator"
```

---

### Task 6: Scheduler

**Files:**
- Create: `scheduler.py`

**Step 1: Implement scheduler with APScheduler**

```python
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from fetchers.nvd import fetch_nvd_cves
from fetchers.cisa import fetch_cisa_kev
from fetchers.arxiv import fetch_arxiv_papers
from generator.post_generator import generate_post


def run_cycle(store, store_lock):
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting fetch cycle...")

    nvd_data = fetch_nvd_cves()
    cisa_data = fetch_cisa_kev()
    arxiv_data = fetch_arxiv_papers()

    findings = {
        "nvd": nvd_data,
        "cisa": cisa_data,
        "arxiv": arxiv_data,
    }

    print(f"Fetched: {len(nvd_data)} CVEs, {len(cisa_data)} CISA advisories, {len(arxiv_data)} arXiv papers")

    draft = generate_post(findings)

    with store_lock:
        store["findings"] = findings
        store["draft"] = draft
        store["last_run"] = datetime.now(timezone.utc).isoformat()

    print("Cycle complete.")


def init_scheduler(app, store, store_lock):
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_cycle,
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        args=[store, store_lock],
        id="weekly_cyber_content",
    )

    scheduler.start()

    with store_lock:
        store["scheduler_running"] = True
        next_job = scheduler.get_job("weekly_cyber_content")
        if next_job and next_job.next_run_time:
            store["next_run"] = next_job.next_run_time.isoformat()

    # If no draft exists, trigger immediate run
    with store_lock:
        has_draft = store["draft"] is not None

    if not has_draft:
        import threading
        thread = threading.Thread(target=run_cycle, args=(store, store_lock))
        thread.start()
```

**Step 2: Commit**

```bash
git add scheduler.py
git commit -m "feat: add APScheduler for weekly Monday 8am fetch cycle"
```

---

### Task 7: Update .gitignore & Push Backend

**Files:**
- Modify: `.gitignore`

**Step 1: Add node_modules to .gitignore if not present**

Verify `.gitignore` has `.env`, `node_modules/`, `__pycache__/`. Add `node_modules/` if missing.

**Step 2: Commit and push**

```bash
git add .gitignore
git commit -m "chore: update gitignore for node_modules"
git push origin main
```

---

### Task 8: Frontend Scaffolding

**Files:**
- Create: `client/` (via Vite)
- Modify: `client/vite.config.ts`
- Modify: `client/tailwind.config.js`
- Modify: `client/src/index.css`

**Step 1: Scaffold React app with Vite**

```bash
cd C:/Users/mobee/Desktop/cyber-content-bot
npm create vite@latest client -- --template react-typescript
cd client
npm install
npm install -D tailwindcss @tailwindcss/vite
```

**Step 2: Configure vite.config.ts with Tailwind and API proxy**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5058',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 3: Set up Tailwind in index.css**

Replace `client/src/index.css` with:

```css
@import "tailwindcss";
```

**Step 4: Clean up default Vite files**

Remove `client/src/App.css`. Clear `client/src/App.tsx` to a minimal shell.

**Step 5: Commit**

```bash
git add client/
git commit -m "feat: scaffold React/Vite/Tailwind frontend with API proxy"
```

---

### Task 9: Frontend API Layer

**Files:**
- Create: `client/src/api.ts`

**Step 1: Create API client**

```typescript
export interface Findings {
  nvd: NvdCve[];
  cisa: CisaAdvisory[];
  arxiv: ArxivPaper[];
}

export interface NvdCve {
  cve_id: string;
  description: string;
  cvss_score: number;
  severity: string;
  affected_products: string[];
}

export interface CisaAdvisory {
  cve_id: string;
  vulnerability_name: string;
  vendor_project: string;
  product: string;
  required_action: string;
  due_date: string;
}

export interface ArxivPaper {
  title: string;
  summary: string;
  authors: string[];
  link: string;
}

export interface StatusResponse {
  last_run: string | null;
  num_findings: number;
  has_draft: boolean;
  scheduler_running: boolean;
  next_run: string | null;
}

export interface DraftResponse {
  draft: string | null;
  findings: Findings;
}

const BASE = '/api';

export async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${BASE}/status`);
  return res.json();
}

export async function triggerRun(): Promise<void> {
  await fetch(`${BASE}/run`, { method: 'POST' });
}

export async function getDraft(): Promise<DraftResponse> {
  const res = await fetch(`${BASE}/draft`);
  return res.json();
}

export async function regenerateDraft(tone: string): Promise<{ draft: string }> {
  const res = await fetch(`${BASE}/draft/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tone }),
  });
  return res.json();
}
```

**Step 2: Commit**

```bash
git add client/src/api.ts
git commit -m "feat: add typed API client for Flask backend"
```

---

### Task 10: Frontend Components & Dashboard

**Files:**
- Modify: `client/src/App.tsx`

**Step 1: Build the full dashboard in App.tsx**

Build a single-file dashboard (App.tsx) with:
- Header with bot name and last run time
- Status indicator (scheduler running, next run)
- "Run Now" teal button that triggers POST /run
- Draft card showing generated LinkedIn post with "Copy to Clipboard"
- Regenerate button with tone selector dropdown (Professional/Conversational/Technical)
- Collapsible Sources panel with 3 sections (CVEs, CISA, arXiv)
- Loading spinner during fetch+generate cycle
- Poll /api/status every 3 seconds while loading to detect completion

Design tokens:
- bg: #0D1117
- card: #161B22
- border: #30363D
- accent: #20D3BE
- text: #E6EDF3
- secondary: #8B949E

**Step 2: Commit**

```bash
git add client/src/App.tsx
git commit -m "feat: build full dashboard UI with dark theme"
```

---

### Task 11: CI/CD GitHub Actions

**Files:**
- Create: `.github/workflows/security.yml`

**Step 1: Create security workflow**

```yaml
name: Security Checks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install bandit pip-audit

      - name: Bandit SAST scan
        run: |
          bandit -r . -x ./client,./node_modules,./.venv -f json -o bandit-report.json --severity-level high || true
          bandit -r . -x ./client,./node_modules,./.venv --severity-level high

      - name: pip-audit dependency scan
        run: pip-audit -r requirements.txt

      - name: Gitleaks secrets detection
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload security reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            bandit-report.json
```

**Step 2: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "ci: add security workflow with Bandit, pip-audit, and Gitleaks"
```

---

### Task 12: Final Cleanup & Push

**Step 1: Update README.md with setup instructions**

**Step 2: Verify .gitignore covers node_modules, .env, __pycache__**

**Step 3: Final commit and push**

```bash
git add -A
git commit -m "docs: update README with setup and usage instructions"
git push origin main
```
