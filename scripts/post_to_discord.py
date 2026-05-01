"""Generate a cybersecurity LinkedIn draft and send it to Discord.

Intended for scheduled GitHub Actions runs. Requires:
- ANTHROPIC_API_KEY
- DISCORD_WEBHOOK_URL

Optional:
- POST_TONE: professional | conversational | technical
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import requests

# Allow running this file directly from scripts/ without installing the package.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fetchers.arxiv import fetch_arxiv_papers
from fetchers.cisa import fetch_cisa_kev
from fetchers.nvd import fetch_nvd_cves
from generator.post_generator import generate_post


def build_discord_message(draft: str, findings: dict) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    counts = (
        f"NVD: {len(findings['nvd'])} | "
        f"CISA KEV: {len(findings['cisa'])} | "
        f"arXiv: {len(findings['arxiv'])}"
    )

    message = (
        "**Cyber LinkedIn draft ready for review**\n"
        f"Generated: {generated_at}\n"
        f"Sources: {counts}\n\n"
        f"{draft}\n\n"
        "Copy this into LinkedIn after review."
    )

    # Discord webhook content limit is 2000 chars.
    if len(message) > 2000:
        message = message[:1970].rstrip() + "\n\n...[truncated]"

    return message


def send_to_discord(content: str) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    response = requests.post(
        webhook_url,
        json={
            "content": content,
            "username": "Cyber Content Bot",
        },
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    tone = os.environ.get("POST_TONE", "professional")

    findings = {
        "nvd": fetch_nvd_cves(),
        "cisa": fetch_cisa_kev(),
        "arxiv": fetch_arxiv_papers(),
    }
    draft = generate_post(findings, tone=tone)

    if draft.startswith("Error:") or draft.startswith("Error generating post:"):
        print(draft, file=sys.stderr)
        return 1

    send_to_discord(build_discord_message(draft, findings))
    print("Discord post sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
