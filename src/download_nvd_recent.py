from pathlib import Path
import requests
import gzip
import shutil
from config import DATA_RAW_NVD

URL = "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.json.gz"

save_dir = Path(DATA_RAW_NVD)
save_dir.mkdir(parents=True, exist_ok=True)

gz_file = save_dir / "nvdcve-2.0-recent.json.gz"
json_file = save_dir / "nvdcve-2.0-recent.json"

print("Téléchargement du feed NVD recent...")
response = requests.get(URL, timeout=120)
response.raise_for_status()

with open(gz_file, "wb") as f:
    f.write(response.content)

print("Décompression du fichier...")
with gzip.open(gz_file, "rb") as f_in:
    with open(json_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print("Téléchargement terminé.")
print(f"Fichier compressé : {gz_file}")
print(f"Fichier JSON : {json_file}")
print(f"Taille JSON : {json_file.stat().st_size / (1024 * 1024):.2f} MB")