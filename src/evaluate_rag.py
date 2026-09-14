from pathlib import Path
import json
import re
import numpy as np
import faiss
import requests
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "mistral"
INDEX_FILE = Path("vectorstore/faiss_index/full.index")
META_FILE = Path("vectorstore/faiss_index/full_chunks.json")
QUESTIONS_FILE = Path("data/eval/questions.json")
OUTPUT_FILE = Path("data/eval/rag_results.json")
TOP_K = 5

def extract_exact_id(query):
    match = re.search(r"(CVE-\d{4}-\d+|T\d{4}(?:\.\d{3})?)", query, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

def retrieve_chunks(query, index, chunks, embed_model):
    exact_id = extract_exact_id(query)
    retrieved_chunks = []
    distances = None
    mode = "faiss"

    if exact_id:
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            cve_id = str(metadata.get("cve_id", "")).upper()
            attack_id = str(metadata.get("attack_id", "")).upper()

            if exact_id == cve_id or exact_id == attack_id:
                retrieved_chunks.append(chunk)

        if retrieved_chunks:
            return retrieved_chunks[:TOP_K], distances, "exact"

    query_vector = embed_model.encode([query], show_progress_bar=False)
    query_vector = np.array(query_vector).astype("float32")

    distances, indices = index.search(query_vector, TOP_K)

    for idx in indices[0]:
        retrieved_chunks.append(chunks[idx])

    return retrieved_chunks, distances, mode

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

def compute_match_score(answer, expected_contains):
    answer_upper = answer.upper()
    matched = []

    for item in expected_contains:
        if item.upper() in answer_upper:
            matched.append(item)

    if expected_contains:
        score = len(matched) / len(expected_contains)
    else:
        score = 0

    return matched, score

print("Chargement de l'index FAISS...")
index = faiss.read_index(str(INDEX_FILE))

print("Chargement des chunks...")
with open(META_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print("Chargement des questions...")
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

print("Chargement du modèle d'embeddings...")
embed_model = SentenceTransformer(EMBED_MODEL)

results = []

for i, q in enumerate(questions, start=1):
    qid = q["id"]
    category = q["category"]
    question = q["question"]
    expected_contains = q["expected_contains"]

    print(f"[{i}/{len(questions)}] {qid} - {question}")

    retrieved_chunks, distances, mode = retrieve_chunks(question, index, chunks, embed_model)
    prompt = build_prompt(question, retrieved_chunks)
    answer = ask_ollama(prompt)

    matched, score = compute_match_score(answer, expected_contains)

    result = {
        "id": qid,
        "category": category,
        "question": question,
        "expected_contains": expected_contains,
        "matched_contains": matched,
        "coverage_score": score,
        "mode": mode,
        "answer": answer,
        "sources": [chunk.get("chunk_id") for chunk in retrieved_chunks]
    }

    results.append(result)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

average_score = sum(r["coverage_score"] for r in results) / len(results)

print("\n=== TERMINÉ ===")
print("Nombre de questions évaluées :", len(results))
print("Score moyen de couverture :", round(average_score, 3))
print("Fichier créé :", OUTPUT_FILE)