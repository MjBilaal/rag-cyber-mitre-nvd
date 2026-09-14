from pathlib import Path
import json
import re
import numpy as np
import faiss
import requests
import streamlit as st
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "mistral"
INDEX_FILE = Path("vectorstore/faiss_index/full.index")
META_FILE = Path("vectorstore/faiss_index/full_chunks.json")

TOP_K = 5
FAISS_CANDIDATES = 10
BM25_CANDIDATES = 10
ALPHA = 0.6
BETA = 0.4

st.set_page_config(page_title="P17 RAG Cybersécurité - Hybrid", layout="wide")
st.title("P17 - RAG Cybersécurité (Hybrid Search)")
st.write("Question -> exact-match / BM25 + FAISS -> Mistral")

def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())

def extract_exact_id(query):
    match = re.search(r"(CVE-\d{4}-\d+|T\d{4}(?:\.\d{3})?)", query, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

@st.cache_resource
def load_embed_model():
    return SentenceTransformer(EMBED_MODEL)

@st.cache_resource
def load_faiss_index():
    return faiss.read_index(str(INDEX_FILE))

@st.cache_data
def load_chunks():
    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_resource
def build_bm25(chunks):
    tokenized_corpus = [tokenize(chunk.get("text", "")) for chunk in chunks]
    return BM25Okapi(tokenized_corpus)

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

    # Vector search
    query_vector = embed_model.encode([query], show_progress_bar=False)
    query_vector = np.array(query_vector).astype("float32")
    faiss_distances, faiss_indices = index.search(query_vector, FAISS_CANDIDATES)

    vector_scores = {}
    for dist, idx in zip(faiss_distances[0], faiss_indices[0]):
        vector_scores[int(idx)] = 1.0 / (1.0 + float(dist))

    # BM25 search
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

    # Hybrid fusion
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

def query_ollama(prompt):
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

index = load_faiss_index()
chunks = load_chunks()
bm25 = build_bm25(chunks)
embed_model = load_embed_model()

question = st.text_input("Pose ta question", placeholder="Ex: What is CVE-2025-14037?")

if st.button("Interroger le RAG hybride"):
    if not question.strip():
        st.warning("Écris une question.")
    else:
        with st.spinner("Recherche hybride et génération en cours..."):
            retrieved_chunks, mode, details = hybrid_retrieve(question, index, chunks, bm25, embed_model)
            prompt = build_prompt(question, retrieved_chunks)
            answer = query_ollama(prompt)

        st.subheader("Réponse")
        st.write(answer)

        st.subheader("Mode de recherche")
        st.write(mode)

        st.subheader("Sources utilisées")
        for i, chunk in enumerate(retrieved_chunks, start=1):
            text = chunk.get("text", "")
            if len(text) > 300:
                text = text[:300] + "..."

            with st.expander(f"Source {i} - {chunk.get('chunk_id')}"):
                if mode == "hybrid" and details is not None:
                    st.write(f"Hybrid score : {details[i - 1]['hybrid_score']:.4f}")
                    st.write(f"Vector score : {details[i - 1]['vector_score']:.4f}")
                    st.write(f"BM25 score : {details[i - 1]['bm25_score']:.4f}")
                else:
                    st.write("Distance : exact-match")

                st.write(f"Parent doc : {chunk.get('parent_doc_id')}")
                st.write(f"Source : {chunk.get('source')}")
                st.write(text)