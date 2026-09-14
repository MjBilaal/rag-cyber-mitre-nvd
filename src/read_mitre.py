from pathlib import Path
import json
from collections import Counter
from config import DATA_RAW_MITRE

file_path = Path(DATA_RAW_MITRE) / "enterprise-attack.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== INFORMATIONS GÉNÉRALES ===")
print("Type du document :", data.get("type"))

objects = data.get("objects", [])
print("Nombre total d'objets :", len(objects))

type_counter = Counter(obj.get("type", "UNKNOWN") for obj in objects)

print("\n=== TYPES D'OBJETS LES PLUS FRÉQUENTS ===")
for obj_type, count in type_counter.most_common(10):
    print(f"{obj_type}: {count}")

example = next((obj for obj in objects if obj.get("name")), objects[0] if objects else {})

print("\n=== EXEMPLE D'OBJET ===")
print("type =", example.get("type"))
print("id =", example.get("id"))
print("name =", example.get("name"))