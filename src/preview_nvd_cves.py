from pathlib import Path
import json
from collections import Counter
from config import DATA_PROCESSED

file_path = Path(DATA_PROCESSED) / "nvd_recent_cves.json"

with open(file_path, "r", encoding="utf-8") as f:
    cves = json.load(f)

print("Nombre total de CVE :", len(cves))

severity_counter = Counter(cve.get("severity", "UNKNOWN") for cve in cves)

print("\n=== RÉPARTITION DES SÉVÉRITÉS ===")
for severity, count in severity_counter.items():
    print(f"{severity}: {count}")

print("\n=== 5 PREMIERS CVE ===")

for i, cve in enumerate(cves[:5], start=1):
    print(f"\n--- CVE {i} ---")
    print("ID :", cve.get("cve_id"))
    print("Sévérité :", cve.get("severity"))
    print("CVSS :", cve.get("cvss_score"))
    print("CWE :", cve.get("weaknesses"))

    description = cve.get("description", "")
    if len(description) > 200:
        description = description[:200] + "..."

    print("Description :", description)