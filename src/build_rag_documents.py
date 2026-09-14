from pathlib import Path
import json
from config import DATA_PROCESSED

mitre_file = Path(DATA_PROCESSED) / "mitre_techniques.json"
nvd_file = Path(DATA_PROCESSED) / "nvd_recent_cves.json"
output_file = Path(DATA_PROCESSED) / "rag_documents.json"

def clean_value(value):
    if value is None:
        return "UNKNOWN"

    if isinstance(value, list):
        if not value:
            return "UNKNOWN"
        return ", ".join(str(v) for v in value)

    value = str(value).strip()

    if value == "" or value.upper() == "NONE":
        return "UNKNOWN"

    return value

with open(mitre_file, "r", encoding="utf-8") as f:
    mitre_techniques = json.load(f)

with open(nvd_file, "r", encoding="utf-8") as f:
    nvd_cves = json.load(f)

documents = []

for i, tech in enumerate(mitre_techniques, start=1):
    attack_id = clean_value(tech.get("attack_id"))
    name = clean_value(tech.get("name"))
    description = clean_value(tech.get("description"))
    is_subtechnique = tech.get("is_subtechnique", False)
    platforms = clean_value(tech.get("platforms"))
    data_sources = clean_value(tech.get("data_sources"))
    detection = clean_value(tech.get("detection"))

    text = (
        f"[MITRE ATT&CK]\n"
        f"ID: {attack_id}\n"
        f"Name: {name}\n"
        f"Is subtechnique: {is_subtechnique}\n"
        f"Platforms: {platforms}\n"
        f"Data Sources: {data_sources}\n"
        f"Detection: {detection}\n"
        f"Description: {description}"
    )

    documents.append({
        "doc_id": f"mitre_{i}",
        "source": "mitre",
        "text": text,
        "metadata": {
            "attack_id": attack_id,
            "name": name,
            "is_subtechnique": is_subtechnique
        }
    })

for i, cve in enumerate(nvd_cves, start=1):
    cve_id = clean_value(cve.get("cve_id"))
    published = clean_value(cve.get("published"))
    last_modified = clean_value(cve.get("last_modified"))
    description = clean_value(cve.get("description"))
    severity = clean_value(cve.get("severity"))
    cvss_score = clean_value(cve.get("cvss_score"))
    weaknesses = clean_value(cve.get("weaknesses"))

    text = (
        f"[CVE]\n"
        f"ID: {cve_id}\n"
        f"Published: {published}\n"
        f"Last Modified: {last_modified}\n"
        f"Severity: {severity}\n"
        f"CVSS Score: {cvss_score}\n"
        f"Weaknesses: {weaknesses}\n"
        f"Description: {description}"
    )

    documents.append({
        "doc_id": f"cve_{i}",
        "source": "nvd",
        "text": text,
        "metadata": {
            "cve_id": cve_id,
            "severity": severity,
            "cvss_score": cvss_score
        }
    })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(documents, f, ensure_ascii=False, indent=2)

print("Documents MITRE :", len(mitre_techniques))
print("Documents CVE :", len(nvd_cves))
print("Total documents RAG :", len(documents))
print("Fichier créé :", output_file)

example = documents[0] if documents else {}

print("\n=== EXEMPLE ===")
print("doc_id =", example.get("doc_id"))
print("source =", example.get("source"))
print("text =")
print(example.get("text"))