from pathlib import Path
import requests
from config import DATA_RAW_MITRE

URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

save_dir = Path(DATA_RAW_MITRE)
save_dir.mkdir(parents=True, exist_ok=True)

output_file = save_dir / "enterprise-attack.json"

print("Téléchargement du fichier MITRE ATT&CK...")
response = requests.get(URL, timeout=120)
response.raise_for_status()

with open(output_file, "wb") as f:
    f.write(response.content)

size_mb = output_file.stat().st_size / (1024 * 1024)

print("Téléchargement terminé.")
print(f"Fichier enregistré : {output_file}")
print(f"Taille : {size_mb:.2f} MB")