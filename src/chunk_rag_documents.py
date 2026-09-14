from pathlib import Path
import json
from config import DATA_PROCESSED

input_file = Path(DATA_PROCESSED) / "rag_documents.json"
output_file = Path(DATA_PROCESSED) / "rag_chunks.json"

CHUNK_SIZE = 120
CHUNK_OVERLAP = 30

def split_text_into_chunks(text, chunk_size=120, overlap=30):
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)

        if end >= len(words):
            break

        start += step

    return chunks

with open(input_file, "r", encoding="utf-8") as f:
    documents = json.load(f)

all_chunks = []

for doc in documents:
    doc_id = doc.get("doc_id")
    source = doc.get("source")
    text = doc.get("text", "")
    metadata = doc.get("metadata", {})

    chunks = split_text_into_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)

    for i, chunk_text in enumerate(chunks, start=1):
        all_chunks.append({
            "chunk_id": f"{doc_id}_chunk_{i}",
            "parent_doc_id": doc_id,
            "source": source,
            "text": chunk_text,
            "metadata": metadata
        })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False, indent=2)

print("Nombre de documents d'origine :", len(documents))
print("Nombre total de chunks :", len(all_chunks))
print("Fichier créé :", output_file)

example = all_chunks[0] if all_chunks else {}

print("\n=== EXEMPLE DE CHUNK ===")
print("chunk_id =", example.get("chunk_id"))
print("parent_doc_id =", example.get("parent_doc_id"))
print("source =", example.get("source"))
print("text =")
print(example.get("text"))