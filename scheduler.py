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
