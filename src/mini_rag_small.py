from pathlib import Path
import json
import numpy as np
import faiss
import requests
from sentence_transformers import SentenceTransformer
from config import FAISS_DIR

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "mistral"
INDEX_FILE = Path(FAISS_DIR) / "small_test.index"
META_FILE = Path(FAISS_DIR) / "small_test_chunks.json"
TOP_K = 3

query = input("Pose ta question : ").strip()

if not query:
    print("Tu n'as pas écrit de question.")
    raise SystemExit

print("Chargement de l'index FAISS...")
index = faiss.read_index(str(INDEX_FILE))

with open(META_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print("Chargement du modèle d'embeddings...")
embed_model = SentenceTransformer(EMBED_MODEL)

print("Création de l'embedding de la question...")
query_vector = embed_model.encode([query], show_progress_bar=False)
query_vector = np.array(query_vector).astype("float32")

print("Recherche des meilleurs chunks...")
distances, indices = index.search(query_vector, TOP_K)

retrieved_chunks = []
for idx in indices[0]:
    retrieved_chunks.append(chunks[idx])

context_parts = []
for i, chunk in enumerate(retrieved_chunks, start=1):
    context_parts.append(f"Source {i} ({chunk['chunk_id']}):\n{chunk['text']}")

context = "\n\n".join(context_parts)

prompt = f"""
You are a cybersecurity assistant.
Answer ONLY using the provided context.
If the context is insufficient, say so clearly.
Answer in French.
Mention IDs when present.

Question:
{query}

Context:
{context}

Answer:
"""

print("Envoi de la requête à Ollama...")
response = requests.post(
    "http://127.0.0.1:11434/api/generate",
    json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    },
    timeout=120
)

response.raise_for_status()
result = response.json()
answer = result.get("response", "").strip()

print("\n=== QUESTION ===")
print(query)

print("\n=== RÉPONSE ===")
print(answer)

print("\n=== SOURCES UTILISÉES ===")
for i, chunk in enumerate(retrieved_chunks, start=1):
    print(f"\n--- Source {i} ---")
    print("distance =", distances[0][i - 1])
    print("chunk_id =", chunk.get("chunk_id"))
    print("parent_doc_id =", chunk.get("parent_doc_id"))
    print("source =", chunk.get("source"))