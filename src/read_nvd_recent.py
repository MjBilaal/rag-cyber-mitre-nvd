from pathlib import Path
import json
from config import DATA_RAW_NVD

file_path = Path(DATA_RAW_NVD) / "nvdcve-2.0-recent.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== INFORMATIONS GÉNÉRALES ===")
print("version =", data.get("version"))
print("timestamp =", data.get("timestamp"))
print("totalResults =", data.get("totalResults"))

vulnerabilities = data.get("vulnerabilities", [])
print("Nombre d'éléments dans vulnerabilities =", len(vulnerabilities))

print("\n=== 3 PREMIERS CVE ===")

for i, item in enumerate(vulnerabilities[:3], start=1):
    cve = item.get("cve", {})
    cve_id = cve.get("id")

    descriptions = cve.get("descriptions", [])
    english_description = ""

    for desc in descriptions:
        if desc.get("lang") == "en":
            english_description = desc.get("value", "")
            break

    if len(english_description) > 200:
        english_description = english_description[:200] + "..."

    print(f"\n--- CVE {i} ---")
    print("ID =", cve_id)
    print("Description =", english_description)