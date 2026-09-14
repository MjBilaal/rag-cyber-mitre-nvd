from pathlib import Path
import json
from sentence_transformers import SentenceTransformer
from config import DATA_PROCESSED

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
file_path = Path(DATA_PROCESSED) / "rag_chunks.json"

with open(file_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

sample_chunks = chunks[:5]
texts = [chunk["text"] for chunk in sample_chunks]

print("Chargement du modèle d'embeddings...")
model = SentenceTransformer(MODEL_NAME)

print("Création des embeddings...")
embeddings = model.encode(texts, show_progress_bar=False)

print("Nombre de chunks testés :", len(texts))
print("Nombre d'embeddings créés :", len(embeddings))
print("Dimension d'un embedding :", len(embeddings[0]))

print("\n=== EXEMPLE ===")
print("chunk_id =", sample_chunks[0]["chunk_id"])
print("Début du texte =")
print(texts[0][:250] + "...")