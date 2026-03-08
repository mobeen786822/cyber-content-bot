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
