from pathlib import Path
import json
import re
import numpy as np
import faiss
import requests
from sentence_transformers import SentenceTransformer
from config import FAISS_DIR

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "mistral"
INDEX_FILE = Path(FAISS_DIR) / "full.index"
META_FILE = Path(FAISS_DIR) / "full_chunks.json"
TOP_K = 5

def extract_exact_id(query):
    match = re.search(r"(CVE-\d{4}-\d+|T\d{4}(?:\.\d{3})?)", query, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

query = input("Pose ta question : ").strip()

if not query:
    print("Tu n'as pas écrit de question.")
    raise SystemExit

print("Chargement de l'index FAISS complet...")
index = faiss.read_index(str(INDEX_FILE))

with open(META_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

exact_id = extract_exact_id(query)
retrieved_chunks = []
mode = "faiss"
distances = None

if exact_id:
    print(f"Identifiant exact détecté : {exact_id}")
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        cve_id = str(metadata.get("cve_id", "")).upper()
        attack_id = str(metadata.get("attack_id", "")).upper()

        if exact_id == cve_id or exact_id == attack_id:
            retrieved_chunks.append(chunk)

    if retrieved_chunks:
        mode = "exact"
        retrieved_chunks = retrieved_chunks[:TOP_K]
        print(f"{len(retrieved_chunks)} chunk(s) trouvé(s) par correspondance exacte.")

if not retrieved_chunks:
    print("Aucune correspondance exacte trouvée. Passage à FAISS...")
    print("Chargement du modèle d'embeddings...")
    embed_model = SentenceTransformer(EMBED_MODEL)

    print("Création de l'embedding de la question...")
    query_vector = embed_model.encode([query], show_progress_bar=False)
    query_vector = np.array(query_vector).astype("float32")

    print("Recherche des meilleurs chunks...")
    distances, indices = index.search(query_vector, TOP_K)

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
Do not invent facts.

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
    timeout=180
)

response.raise_for_status()
result = response.json()
answer = result.get("response", "").strip()

print("\n=== QUESTION ===")
print(query)

print("\n=== MODE DE RECHERCHE ===")
print(mode)

print("\n=== RÉPONSE ===")
print(answer)

print("\n=== SOURCES UTILISÉES ===")
for i, chunk in enumerate(retrieved_chunks, start=1):
    text = chunk.get("text", "")
    if len(text) > 200:
        text = text[:200] + "..."

    print(f"\n--- Source {i} ---")
    if mode == "faiss" and distances is not None:
        print("distance =", distances[0][i - 1])
    else:
        print("distance = exact-match")

    print("chunk_id =", chunk.get("chunk_id"))
    print("parent_doc_id =", chunk.get("parent_doc_id"))
    print("source =", chunk.get("source"))
    print("texte =", text)