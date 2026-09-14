from pathlib import Path
import json
import requests

OLLAMA_MODEL = "mistral"
QUESTIONS_FILE = Path("data/eval/questions.json")
OUTPUT_FILE = Path("data/eval/llm_only_results.json")

def ask_ollama_without_context(question):
    prompt = f"""
You are a cybersecurity assistant.
Answer in French.
Do your best to answer the question directly.
Mention IDs when present.

Question:
{question}

Answer:
"""

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

print("Chargement des questions...")
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

results = []

for i, q in enumerate(questions, start=1):
    qid = q["id"]
    category = q["category"]
    question = q["question"]
    expected_contains = q["expected_contains"]

    print(f"[{i}/{len(questions)}] {qid} - {question}")

    answer = ask_ollama_without_context(question)
    matched, score = compute_match_score(answer, expected_contains)

    result = {
        "id": qid,
        "category": category,
        "question": question,
        "expected_contains": expected_contains,
        "matched_contains": matched,
        "coverage_score": score,
        "mode": "llm_only",
        "answer": answer
    }

    results.append(result)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

average_score = sum(r["coverage_score"] for r in results) / len(results)

print("\n=== TERMINÉ ===")
print("Nombre de questions évaluées :", len(results))
print("Score moyen de couverture :", round(average_score, 3))
print("Fichier créé :", OUTPUT_FILE)