from pathlib import Path
import json

RAG_FILE = Path("data/eval/rag_results.json")
LLM_FILE = Path("data/eval/llm_only_results.json")
OUTPUT_JSON = Path("data/eval/comparison_results.json")
OUTPUT_TXT = Path("data/eval/comparison_summary.txt")

with open(RAG_FILE, "r", encoding="utf-8") as f:
    rag_results = json.load(f)

with open(LLM_FILE, "r", encoding="utf-8") as f:
    llm_results = json.load(f)

rag_map = {item["id"]: item for item in rag_results}
llm_map = {item["id"]: item for item in llm_results}

comparison = []

rag_better = 0
llm_better = 0
equal = 0

for qid in rag_map:
    rag_item = rag_map[qid]
    llm_item = llm_map[qid]

    rag_score = rag_item["coverage_score"]
    llm_score = llm_item["coverage_score"]
    delta = rag_score - llm_score

    if rag_score > llm_score:
        winner = "RAG"
        rag_better += 1
    elif llm_score > rag_score:
        winner = "LLM_ONLY"
        llm_better += 1
    else:
        winner = "EQUAL"
        equal += 1

    comparison.append({
        "id": qid,
        "category": rag_item["category"],
        "question": rag_item["question"],
        "rag_score": rag_score,
        "llm_only_score": llm_score,
        "delta": delta,
        "winner": winner
    })

rag_avg = sum(item["coverage_score"] for item in rag_results) / len(rag_results)
llm_avg = sum(item["coverage_score"] for item in llm_results) / len(llm_results)

mitre_rag = [item["coverage_score"] for item in rag_results if item["category"] == "mitre"]
mitre_llm = [item["coverage_score"] for item in llm_results if item["category"] == "mitre"]

cve_rag = [item["coverage_score"] for item in rag_results if item["category"] == "cve"]
cve_llm = [item["coverage_score"] for item in llm_results if item["category"] == "cve"]

summary = {
    "rag_average_score": rag_avg,
    "llm_only_average_score": llm_avg,
    "average_gain": rag_avg - llm_avg,
    "rag_better_count": rag_better,
    "llm_only_better_count": llm_better,
    "equal_count": equal,
    "mitre_rag_average": sum(mitre_rag) / len(mitre_rag),
    "mitre_llm_average": sum(mitre_llm) / len(mitre_llm),
    "cve_rag_average": sum(cve_rag) / len(cve_rag),
    "cve_llm_average": sum(cve_llm) / len(cve_llm)
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(
        {
            "summary": summary,
            "comparison": comparison
        },
        f,
        ensure_ascii=False,
        indent=2
    )

report_text = f"""
=== COMPARAISON RAG vs LLM SEUL ===

Score moyen RAG : {rag_avg:.3f}
Score moyen LLM seul : {llm_avg:.3f}
Gain moyen du RAG : {rag_avg - llm_avg:.3f}

Nombre de questions où RAG est meilleur : {rag_better}
Nombre de questions où LLM seul est meilleur : {llm_better}
Nombre de questions à égalité : {equal}

--- Détail par catégorie ---
MITRE - RAG : {summary['mitre_rag_average']:.3f}
MITRE - LLM seul : {summary['mitre_llm_average']:.3f}

CVE - RAG : {summary['cve_rag_average']:.3f}
CVE - LLM seul : {summary['cve_llm_average']:.3f}
""".strip()

with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    f.write(report_text)

print("=== TERMINÉ ===")
print(report_text)
print("\nFichier JSON créé :", OUTPUT_JSON)
print("Fichier résumé créé :", OUTPUT_TXT)