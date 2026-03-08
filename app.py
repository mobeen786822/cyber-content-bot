import threading
from pathlib import Path
from datetime import datetime

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
    "scheduler_running": False,
    "next_run": None,
    "cycle_running": False,
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
            "cycle_running": store["cycle_running"],
        })


@app.route("/api/run", methods=["POST"])
def run():
    with store_lock:
        if store["cycle_running"]:
            return jsonify({"message": "Cycle already running"}), 409
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
    app.run(host="0.0.0.0", port=5058, debug=True, use_reloader=False, threaded=True)
