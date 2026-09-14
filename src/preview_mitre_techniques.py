from pathlib import Path
import json
from config import DATA_PROCESSED

file_path = Path(DATA_PROCESSED) / "mitre_techniques.json"

with open(file_path, "r", encoding="utf-8") as f:
    techniques = json.load(f)

print("Nombre total de techniques :", len(techniques))

subtechniques = sum(1 for t in techniques if t.get("is_subtechnique"))
print("Nombre de sous-techniques :", subtechniques)
print("Nombre de techniques principales :", len(techniques) - subtechniques)

print("\n=== 5 PREMIÈRES TECHNIQUES ===")

for i, tech in enumerate(techniques[:5], start=1):
    print(f"\n--- Technique {i} ---")
    print("ID :", tech.get("attack_id"))
    print("Nom :", tech.get("name"))
    print("Sous-technique :", tech.get("is_subtechnique"))

    description = tech.get("description", "")
    description = description.replace("\n", " ")

    if len(description) > 200:
        description = description[:200] + "..."

    print("Description :", description)