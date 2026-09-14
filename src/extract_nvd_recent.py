from pathlib import Path
import json
from config import DATA_RAW_NVD, DATA_PROCESSED

input_file = Path(DATA_RAW_NVD) / "nvdcve-2.0-recent.json"
output_file = Path(DATA_PROCESSED) / "nvd_recent_cves.json"

output_file.parent.mkdir(parents=True, exist_ok=True)

def get_english_description(cve):
    descriptions = cve.get("descriptions", [])
    for desc in descriptions:
        if desc.get("lang") == "en":
            return desc.get("value", "")
    return ""

def get_cvss_info(cve):
    metrics = cve.get("metrics", {})

    for key in ["cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
        metric_list = metrics.get(key)
        if metric_list:
            first_metric = metric_list[0]
            cvss_data = first_metric.get("cvssData", {})

            score = cvss_data.get("baseScore")
            severity = cvss_data.get("baseSeverity") or first_metric.get("baseSeverity")

            return score, severity

    return None, None

def get_weaknesses(cve):
    weaknesses = []

    for weakness in cve.get("weaknesses", []):
        for desc in weakness.get("description", []):
            value = desc.get("value")
            if value and value not in ["NVD-CWE-noinfo", "NVD-CWE-Other"]:
                weaknesses.append(value)

    return list(dict.fromkeys(weaknesses))

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

vulnerabilities = data.get("vulnerabilities", [])
clean_cves = []

for item in vulnerabilities:
    cve = item.get("cve", {})

    cve_id = cve.get("id")
    description = get_english_description(cve)
    score, severity = get_cvss_info(cve)
    weaknesses = get_weaknesses(cve)

    clean_item = {
        "cve_id": cve_id,
        "published": cve.get("published"),
        "last_modified": cve.get("lastModified"),
        "description": description,
        "cvss_score": score,
        "severity": severity,
        "weaknesses": weaknesses,
        "source": "nvd"
    }

    clean_cves.append(clean_item)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(clean_cves, f, ensure_ascii=False, indent=2)

print("Nombre de CVE extraits :", len(clean_cves))
print("Fichier créé :", output_file)

example = clean_cves[0] if clean_cves else {}

print("\n=== EXEMPLE ===")
print("cve_id =", example.get("cve_id"))
print("severity =", example.get("severity"))
print("cvss_score =", example.get("cvss_score"))
print("weaknesses =", example.get("weaknesses"))