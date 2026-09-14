from pathlib import Path
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import FAISS_DIR

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_FILE = Path(FAISS_DIR) / "small_test.index"
META_FILE = Path(FAISS_DIR) / "small_test_chunks.json"

QUERY = "What is Scheduled Task in MITRE ATT&CK?"
TOP_K = 3

print("Chargement de l'index FAISS...")
index = faiss.read_index(str(INDEX_FILE))

with open(META_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print("Chargement du modèle d'embeddings...")
model = SentenceTransformer(MODEL_NAME)

print("Création de l'embedding de la question...")
query_embedding = model.encode([QUERY], show_progress_bar=False)
query_embedding = np.array(query_embedding).astype("float32")

print("Recherche dans FAISS...")
distances, indices = index.search(query_embedding, TOP_K)

print("\nQuestion :", QUERY)
print("\n=== TOP RÉSULTATS ===")

for rank, idx in enumerate(indices[0], start=1):
    chunk = chunks[idx]
    text = chunk.get("text", "")

    if len(text) > 300:
        text = text[:300] + "..."

    print(f"\n--- Résultat {rank} ---")
    print("distance =", distances[0][rank - 1])
    print("chunk_id =", chunk.get("chunk_id"))
    print("parent_doc_id =", chunk.get("parent_doc_id"))
    print("source =", chunk.get("source"))
    print("texte =", text)