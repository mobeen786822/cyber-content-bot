import os
import threading
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / '.env', override=True)

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
    "cycle_running": False,
}
store_lock = threading.Lock()


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
            "cycle_running": store["cycle_running"],
        })


@app.route("/api/run", methods=["POST"])
def run():
    with store_lock:
        if store["cycle_running"]:
            return jsonify({"message": "Cycle already running"}), 409
    thread = threading.Thread(target=run_cycle)
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
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5058, debug=debug, use_reloader=False, threaded=True)
