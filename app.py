import os
import secrets
import threading
from functools import wraps
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / '.env', override=True)

app = Flask(__name__)


def _csv_env(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


CORS(
    app,
    resources={r"/*": {"origins": _csv_env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# In-memory store
store = {
    "last_run": None,
    "findings": {
        "nvd": [],
        "cisa": [],
        "arxiv": [],
    },
    "draft": None,
    "cycle_running": False,
}
store_lock = threading.Lock()


def _request_api_key():
    header_key = request.headers.get("X-API-Key", "").strip()
    if header_key:
        return header_key
    auth_header = request.headers.get("Authorization", "")
    return auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""


def require_api_key(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if os.environ.get("CONTENT_BOT_REQUIRE_AUTH", "true").lower() != "true":
            return view_func(*args, **kwargs)
        configured_key = os.environ.get("CONTENT_BOT_API_KEY", "").strip()
        if not configured_key:
            app.logger.error("Authentication is required but CONTENT_BOT_API_KEY is not configured")
            return jsonify({"error": "Service misconfigured"}), 503
        supplied_key = _request_api_key()
        if not supplied_key or not secrets.compare_digest(supplied_key, configured_key):
            return jsonify({"error": "Unauthorized"}), 401
        return view_func(*args, **kwargs)

    return wrapped


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


def run_cycle():
    with store_lock:
        store["cycle_running"] = True

    try:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Starting fetch cycle...")

        from fetchers.nvd import fetch_nvd_cves
        from fetchers.cisa import fetch_cisa_kev
        from fetchers.arxiv import fetch_arxiv_papers
        from generator.post_generator import generate_post

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
    finally:
        with store_lock:
            store["cycle_running"] = False


@app.route("/status")
@require_api_key
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
            "cycle_running": store["cycle_running"],
        })


@app.route("/run", methods=["POST"])
@require_api_key
def run():
    with store_lock:
        if store["cycle_running"]:
            return jsonify({"message": "Cycle already running"}), 409
    thread = threading.Thread(target=run_cycle, daemon=True)
    thread.start()
    return jsonify({"message": "Cycle started"}), 202


@app.route("/draft")
@require_api_key
def get_draft():
    with store_lock:
        return jsonify({
            "draft": store["draft"],
            "findings": store["findings"],
        })


@app.route("/draft/regenerate", methods=["POST"])
@require_api_key
def regenerate_draft():
    tone = request.json.get("tone", "professional") if request.is_json else "professional"
    if tone not in {"professional", "conversational", "technical"}:
        return jsonify({"error": "Unsupported tone"}), 400
    from generator.post_generator import generate_post
    with store_lock:
        findings = store["findings"]
    draft = generate_post(findings, tone=tone)
    with store_lock:
        store["draft"] = draft
    return jsonify({"draft": draft})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5058")),
        debug=debug,
        use_reloader=False,
        threaded=True,
    )
