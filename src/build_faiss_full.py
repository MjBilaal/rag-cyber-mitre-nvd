from pathlib import Path
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import DATA_PROCESSED, FAISS_DIR

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INPUT_FILE = Path(DATA_PROCESSED) / "rag_chunks.json"
INDEX_FILE = Path(FAISS_DIR) / "full.index"
META_FILE = Path(FAISS_DIR) / "full_chunks.json"

Path(FAISS_DIR).mkdir(parents=True, exist_ok=True)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

texts = [chunk["text"] for chunk in chunks]

print("Nombre total de chunks à indexer :", len(chunks))
print("Chargement du modèle d'embeddings...")
model = SentenceTransformer(MODEL_NAME)

print("Création des embeddings pour tous les chunks...")
embeddings = model.encode(
    texts,
    show_progress_bar=True,
    batch_size=32
)

embeddings = np.array(embeddings).astype("float32")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)

print("Ajout des embeddings dans FAISS...")
index.add(embeddings)

faiss.write_index(index, str(INDEX_FILE))

with open(META_FILE, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print("\n=== TERMINÉ ===")
print("Dimension :", dimension)
print("Nombre de vecteurs indexés :", index.ntotal)
print("Fichier index :", INDEX_FILE)
print("Fichier metadata :", META_FILE)