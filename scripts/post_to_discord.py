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
from io import BytesIO
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


def truncate(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def build_findings_message(findings: dict) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    counts = (
        f"NVD: {len(findings['nvd'])} | "
        f"CISA KEV: {len(findings['cisa'])} | "
        f"arXiv: {len(findings['arxiv'])}"
    )

    lines = [
        "**Cybersecurity source summary**",
        f"Generated: {generated_at}",
        f"Sources: {counts}",
        "",
    ]

    if findings["nvd"]:
        lines.append("**Top NVD CVEs**")
        for cve in findings["nvd"][:3]:
            products = ", ".join(cve.get("affected_products", [])[:3]) or "unknown products"
            lines.append(
                f"- `{cve.get('cve_id')}` ({cve.get('severity')} {cve.get('cvss_score')}): "
                f"{truncate(cve.get('description', ''), 180)} Affected: {products}."
            )
        lines.append("")

    if findings["cisa"]:
        lines.append("**Recent CISA KEV additions**")
        for advisory in findings["cisa"][:3]:
            lines.append(
                f"- `{advisory.get('cve_id')}`: {advisory.get('vendor_project')} "
                f"{advisory.get('product')} — {truncate(advisory.get('vulnerability_name', ''), 120)}"
            )
        lines.append("")

    if findings["arxiv"]:
        lines.append("**AI/security research**")
        for paper in findings["arxiv"][:2]:
            lines.append(f"- {truncate(paper.get('title', ''), 160)}")
        lines.append("")

    lines.append("Draft LinkedIn post coming next.")
    return "\n".join(lines)


def build_post_message(draft: str) -> str:
    return (
        "**LinkedIn post draft**\n\n"
        f"{draft}\n\n"
        "Copy this into LinkedIn after review."
    )


def send_to_discord(content: str, filename: str = "discord-message.txt") -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    if len(content) <= 2000:
        response = requests.post(
            webhook_url,
            json={
                "content": content,
                "username": "Cyber Content Bot",
            },
            timeout=30,
        )
    else:
        preview = content[:1800].rstrip()
        response = requests.post(
            webhook_url,
            data={
                "content": f"{preview}\n\nFull message attached as `{filename}`.",
                "username": "Cyber Content Bot",
            },
            files={
                "file": (filename, BytesIO(content.encode("utf-8")), "text/plain"),
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

    send_to_discord(build_findings_message(findings), filename="cyber-findings-summary.txt")
    send_to_discord(build_post_message(draft), filename="linkedin-draft.txt")
    print("Discord findings summary and post draft sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
