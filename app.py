from pathlib import Path
import json
import re
import numpy as np
import faiss
import requests
import streamlit as st
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "mistral"
INDEX_FILE = Path("vectorstore/faiss_index/full.index")
META_FILE = Path("vectorstore/faiss_index/full_chunks.json")
TOP_K = 5

st.set_page_config(page_title="P17 RAG Cybersécurité", layout="wide")
st.title("P17 - RAG Cybersécurité")
st.write("Question -> embeddings -> FAISS -> Mistral")

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
            retrieved_chunks = retrieved_chunks[:TOP_K]
            mode = "exact"
            return retrieved_chunks, distances, mode

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
embed_model = load_embed_model()

question = st.text_input("Pose ta question", placeholder="Ex: What is CVE-2025-14037?")

if st.button("Interroger le RAG"):
    if not question.strip():
        st.warning("Écris une question.")
    else:
        with st.spinner("Recherche et génération en cours..."):
            retrieved_chunks, distances, mode = retrieve_chunks(question, index, chunks, embed_model)
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
                if mode == "faiss" and distances is not None:
                    st.write(f"Distance : {distances[0][i - 1]}")
                else:
                    st.write("Distance : exact-match")

                st.write(f"Parent doc : {chunk.get('parent_doc_id')}")
                st.write(f"Source : {chunk.get('source')}")
                st.write(text)