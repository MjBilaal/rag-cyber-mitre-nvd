from pathlib import Path
import json
from config import DATA_PROCESSED

file_path = Path(DATA_PROCESSED) / "rag_chunks.json"

with open(file_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print("Nombre total de chunks :", len(chunks))

word_counts = [len(chunk.get("text", "").split()) for chunk in chunks]

print("Nombre minimum de mots :", min(word_counts))
print("Nombre maximum de mots :", max(word_counts))
print("Nombre moyen de mots :", round(sum(word_counts) / len(word_counts), 2))

print("\n=== 3 PREMIERS CHUNKS ===")

for i, chunk in enumerate(chunks[:3], start=1):
    text = chunk.get("text", "")
    if len(text) > 300:
        text = text[:300] + "..."

    print(f"\n--- CHUNK {i} ---")
    print("chunk_id =", chunk.get("chunk_id"))
    print("parent_doc_id =", chunk.get("parent_doc_id"))
    print("source =", chunk.get("source"))
    print("nombre de mots =", len(chunk.get("text", "").split()))
    print("texte =", text)