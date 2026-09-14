from pathlib import Path
import json
import re
import numpy as np
import faiss
import requests
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from config import FAISS_DIR

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "mistral"
INDEX_FILE = Path(FAISS_DIR) / "full.index"
META_FILE = Path(FAISS_DIR) / "full_chunks.json"

TOP_K = 5
FAISS_CANDIDATES = 10
BM25_CANDIDATES = 10
ALPHA = 0.6
BETA = 0.4

def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())

def extract_exact_id(query):
    match = re.search(r"(CVE-\d{4}-\d+|T\d{4}(?:\.\d{3})?)", query, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

def hybrid_retrieve(query, index, chunks, bm25, embed_model):
    exact_id = extract_exact_id(query)
    if exact_id:
        exact_chunks = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            cve_id = str(metadata.get("cve_id", "")).upper()
            attack_id = str(metadata.get("attack_id", "")).upper()

            if exact_id == cve_id or exact_id == attack_id:
                exact_chunks.append(chunk)

        if exact_chunks:
            return exact_chunks[:TOP_K], "exact", None

    # Partie vectorielle
    query_vector = embed_model.encode([query], show_progress_bar=False)
    query_vector = np.array(query_vector).astype("float32")
    faiss_distances, faiss_indices = index.search(query_vector, FAISS_CANDIDATES)

    vector_scores = {}
    for dist, idx in zip(faiss_distances[0], faiss_indices[0]):
        vector_scores[int(idx)] = 1.0 / (1.0 + float(dist))

    # Partie BM25
    tokenized_query = tokenize(query)
    bm25_all_scores = bm25.get_scores(tokenized_query)
    top_bm25_indices = np.argsort(bm25_all_scores)[::-1][:BM25_CANDIDATES]

    bm25_scores = {}
    top_bm25_values = [float(bm25_all_scores[i]) for i in top_bm25_indices]
    max_bm25 = max(top_bm25_values) if top_bm25_values else 1.0

    for idx in top_bm25_indices:
        value = float(bm25_all_scores[idx])
        normalized = value / max_bm25 if max_bm25 > 0 else 0.0
        bm25_scores[int(idx)] = normalized

    # Fusion
    candidate_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
    ranked = []

    for idx in candidate_ids:
        v_score = vector_scores.get(idx, 0.0)
        b_score = bm25_scores.get(idx, 0.0)
        hybrid_score = ALPHA * v_score + BETA * b_score
        ranked.append((idx, hybrid_score, v_score, b_score))

    ranked.sort(key=lambda x: x[1], reverse=True)

    selected = []
    details = []

    for idx, hybrid_score, v_score, b_score in ranked[:TOP_K]:
        selected.append(chunks[idx])
        details.append({
            "chunk_id": chunks[idx].get("chunk_id"),
            "hybrid_score": hybrid_score,
            "vector_score": v_score,
            "bm25_score": b_score
        })

    return selected, "hybrid", details

def build_prompt(query, retrieved_chunks):
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
    return prompt

def ask_ollama(prompt):
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
    return result.get("response", "").strip()

query = input("Pose ta question : ").strip()

if not query:
    print("Tu n'as pas écrit de question.")
    raise SystemExit

print("Chargement de l'index FAISS...")
index = faiss.read_index(str(INDEX_FILE))

print("Chargement des chunks...")
with open(META_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print("Construction de l'index BM25...")
tokenized_corpus = [tokenize(chunk.get("text", "")) for chunk in chunks]
bm25 = BM25Okapi(tokenized_corpus)

print("Chargement du modèle d'embeddings...")
embed_model = SentenceTransformer(EMBED_MODEL)

print("Recherche hybride...")
retrieved_chunks, mode, details = hybrid_retrieve(query, index, chunks, bm25, embed_model)

prompt = build_prompt(query, retrieved_chunks)

print("Envoi de la requête à Ollama...")
answer = ask_ollama(prompt)

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
    print("chunk_id =", chunk.get("chunk_id"))
    print("parent_doc_id =", chunk.get("parent_doc_id"))
    print("source =", chunk.get("source"))

    if mode == "hybrid" and details is not None:
        print("hybrid_score =", round(details[i - 1]["hybrid_score"], 4))
        print("vector_score =", round(details[i - 1]["vector_score"], 4))
        print("bm25_score =", round(details[i - 1]["bm25_score"], 4))
    else:
        print("match = exact-id")

    print("texte =", text)