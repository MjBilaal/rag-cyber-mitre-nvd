from pathlib import Path
import json
from config import DATA_RAW_MITRE, DATA_PROCESSED

input_file = Path(DATA_RAW_MITRE) / "enterprise-attack.json"
output_file = Path(DATA_PROCESSED) / "mitre_techniques.json"

output_file.parent.mkdir(parents=True, exist_ok=True)

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

objects = data.get("objects", [])
techniques = []

for obj in objects:
    if obj.get("type") != "attack-pattern":
        continue

    if obj.get("revoked", False):
        continue

    if obj.get("x_mitre_deprecated", False):
        continue

    attack_id = None
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            attack_id = ref.get("external_id")
            break

    technique = {
        "attack_id": attack_id,
        "name": obj.get("name"),
        "description": obj.get("description", ""),
        "is_subtechnique": obj.get("x_mitre_is_subtechnique", False),
        "platforms": obj.get("x_mitre_platforms", []),
        "data_sources": obj.get("x_mitre_data_sources", []),
        "detection": obj.get("x_mitre_detection", "")
    }

    techniques.append(technique)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(techniques, f, ensure_ascii=False, indent=2)

print("Nombre de techniques extraites :", len(techniques))
print("Fichier créé :", output_file)

example = next((t for t in techniques if t.get("attack_id")), techniques[0] if techniques else {})

print("\n=== EXEMPLE ===")
print("attack_id =", example.get("attack_id"))
print("name =", example.get("name"))
print("is_subtechnique =", example.get("is_subtechnique"))