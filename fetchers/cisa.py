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
