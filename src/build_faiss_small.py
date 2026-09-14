from pathlib import Path
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import DATA_PROCESSED, FAISS_DIR

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INPUT_FILE = Path(DATA_PROCESSED) / "rag_chunks.json"
INDEX_FILE = Path(FAISS_DIR) / "small_test.index"
META_FILE = Path(FAISS_DIR) / "small_test_chunks.json"

Path(FAISS_DIR).mkdir(parents=True, exist_ok=True)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

sample_chunks = chunks[:100]
texts = [chunk["text"] for chunk in sample_chunks]

print("Chargement du modèle...")
model = SentenceTransformer(MODEL_NAME)

print("Création des embeddings pour 100 chunks...")
embeddings = model.encode(texts, show_progress_bar=False)

embeddings = np.array(embeddings).astype("float32")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)

print("Ajout des embeddings dans FAISS...")
index.add(embeddings)

faiss.write_index(index, str(INDEX_FILE))

with open(META_FILE, "w", encoding="utf-8") as f:
    json.dump(sample_chunks, f, ensure_ascii=False, indent=2)

print("Base FAISS créée.")
print("Nombre de chunks indexés :", len(sample_chunks))
print("Dimension :", dimension)
print("Fichier index :", INDEX_FILE)
print("Fichier metadata :", META_FILE)