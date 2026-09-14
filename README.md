# rag-cyber-mitre-nvd

Assistant de questions-réponses en cybersécurité qui répond à partir de MITRE ATT&CK et des CVE récentes du NVD, via une recherche hybride (exact-match + BM25 + FAISS) et un LLM exécuté en local (Mistral via Ollama).

## Description

Un LLM seul connaît mal les CVE récentes (publiées après son entraînement) et invente facilement des identifiants ou des scores. Ce projet construit un pipeline RAG complet qui ancre les réponses dans des sources officielles :

1. **Collecte** : téléchargement du bundle STIX MITRE ATT&CK Enterprise et du flux JSON 2.0 « recent » du NVD.
2. **Extraction** : techniques ATT&CK non révoquées et non dépréciées (ID, plateformes, sources de données, détection) ; CVE avec description, score et sévérité CVSS (v4.0 → v2 par ordre de priorité), CWE associées.
3. **Documents et chunks** : un document texte par technique ou CVE, découpé en chunks de 120 mots avec 30 mots de recouvrement.
4. **Indexation** : embeddings `all-MiniLM-L6-v2` (384 dimensions) dans un index FAISS `IndexFlatL2`.
5. **Recherche** en deux étapes :
   - si la question contient un identifiant (`CVE-AAAA-NNNN`, `T1053`, `T1053.005`), recherche exacte sur les métadonnées ;
   - sinon, recherche hybride : 10 candidats FAISS (score `1 / (1 + distance)`) et 10 candidats BM25 (normalisés), fusionnés avec `0.6 × vecteur + 0.4 × BM25`, top 5 conservé.
6. **Génération** : prompt contraint (« répondre uniquement à partir du contexte », citer les ID, signaler un contexte insuffisant), réponse en français par Mistral via Ollama.

Deux interfaces Streamlit affichent la réponse et les sources utilisées avec leurs scores :
- `app.py` : exact-match + FAISS ;
- `app_hybrid.py` : exact-match + BM25 + FAISS.

Corpus complet utilisé : 691 techniques ATT&CK, 1 948 CVE, soit 2 639 documents et 3 926 chunks.

### Évaluation : RAG vs LLM seul

20 questions (10 MITRE, 10 CVE) dans `data/eval/questions.json`. Le score de couverture est la part des éléments attendus (ID, nom, sévérité, CWE) présents dans la réponse.

| Score moyen de couverture | RAG (`evaluate_rag.py`) | LLM seul |
|---|---|---|
| Global | **0,85** | 0,40 |
| MITRE ATT&CK | **0,80** | 0,55 |
| CVE | **0,90** | 0,25 |

Le RAG est meilleur sur 15 questions, à égalité sur 5, jamais moins bon. Résultats détaillés dans `data/eval/`.

## Stack technique

- Python 3.11
- `sentence-transformers` (all-MiniLM-L6-v2), `faiss-cpu`, `rank-bm25`
- Ollama + modèle `mistral` (inférence locale)
- Streamlit
- Sources : [MITRE ATT&CK](https://github.com/mitre/cti) (STIX 2.1), [NVD CVE JSON 2.0 feeds](https://nvd.nist.gov/vuln/data-feeds)

## Structure

```
.
├── app.py                      # Interface Streamlit : exact-match + FAISS
├── app_hybrid.py               # Interface Streamlit : exact-match + BM25 + FAISS
├── requirements.txt
├── .env.example
├── data/
│   ├── sample/                 # Échantillon : 50 techniques + 50 CVE (couvre les 20 questions d'évaluation)
│   └── eval/                   # Questions, résultats RAG / LLM seul, comparaison
└── src/
    ├── config.py               # Chemins et paramètres (lus depuis .env)
    ├── download_*.py           # Téléchargement MITRE / NVD
    ├── extract_*.py            # Extraction des champs utiles
    ├── build_rag_documents.py  # Construction des documents texte
    ├── chunk_rag_documents.py  # Découpage en chunks
    ├── build_faiss_*.py        # Construction de l'index FAISS (petit test / complet)
    ├── mini_rag_*.py           # Versions CLI successives (small → full → v2 exact-match → hybride)
    ├── evaluate_*.py           # Évaluation RAG et LLM seul
    ├── compare_results.py      # Tableau comparatif
    └── read_* / preview_* / test_* / search_*  # Scripts d'exploration
```

Les données brutes, les données traitées et l'index FAISS ne sont pas versionnés : les scripts les régénèrent.

## Installation et lancement

Prérequis : Python 3.11 et [Ollama](https://ollama.com) installé.

```bash
ollama pull mistral
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Toutes les commandes se lancent **depuis la racine du dépôt** (chemins relatifs).

### Option A : échantillon (quelques minutes)

Dans `.env`, remplacer `DATA_PROCESSED=data/processed` par `DATA_PROCESSED=data/sample`, puis :

```bash
python src/build_rag_documents.py
python src/chunk_rag_documents.py
python src/build_faiss_full.py
```

### Option B : corpus complet

Avec `DATA_PROCESSED=data/processed` :

```bash
python src/download_mitre.py
python src/download_nvd_recent.py
python src/extract_mitre_techniques.py
python src/extract_nvd_recent.py
python src/build_rag_documents.py
python src/chunk_rag_documents.py
python src/build_faiss_full.py
```

Le flux NVD « recent » évolue en continu : un nouveau téléchargement ne contiendra plus forcément les CVE des questions d'évaluation. L'échantillon les conserve.

### Lancer l'interface

```bash
streamlit run app_hybrid.py
```

### Rejouer l'évaluation

```bash
python src/evaluate_rag.py
python src/evaluate_llm_only.py
python src/compare_results.py
```

## Ce que j'ai appris / côté sécurité

- **Les identifiants exacts sont le point faible des embeddings.** Mesuré avec all-MiniLM-L6-v2 (similarité cosinus) :
  - « What is CVE-2025-14037? » et « What is CVE-2025-14038? » : **0,976** ;
  - « What is CVE-2025-14037? » et son vrai sujet (CSRF dans un plugin WordPress) : **0,151**.

  Le modèle encode la forme de la question, pas l'identifiant. D'où la recherche exacte par expression régulière sur les métadonnées, puis BM25 pour les termes lexicaux (noms de produits, CWE).
- **Le LLM seul hallucine surtout sur les CVE** (0,25 de couverture) : les CVE récentes sont postérieures à son entraînement. Le RAG passe à 0,90, et l'affichage des sources permet de vérifier chaque réponse.
- **Inférence locale** : aucune donnée envoyée à une API tierce et aucune clé à gérer. C'est un critère réel pour un usage en SOC ou sur des données sensibles.
- **Injection de prompt indirecte** : les descriptions CVE et ATT&CK sont du texte externe injecté tel quel dans le prompt. Une description malveillante pourrait tenter de détourner le modèle. La consigne « uniquement le contexte » limite l'effet sans l'empêcher ; un filtrage du contexte serait l'étape suivante.
- **Limites de l'évaluation**, à garder en tête :
  - le score est une recherche de sous-chaînes, donc indulgent ;
  - 19 questions sur 20 contiennent un identifiant, ce qui mesure surtout la voie exact-match ;
  - `evaluate_rag.py` évalue la version exact-match + FAISS, pas la version hybride.

## Données

MITRE ATT&CK® est une marque déposée de The MITRE Corporation ; les données sont reproduites selon ses [conditions d'utilisation](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/). Les données CVE proviennent de la National Vulnerability Database (NIST).
