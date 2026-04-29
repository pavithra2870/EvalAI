# Mini Answer Evaluator (RAG + LLM)

A minimal, production-grade academic answer grading system combining **hybrid rubric retrieval** (RAG) with a **local LLaMA model** (via Ollama). Answers are evaluated against structured rubrics with per-criterion scoring, retry logic, and self-verification.

---

## Overview

Given a question and a student's answer, the system:

1. Detects the subject from the question using keyword matching
2. Enriches the query with subject-specific hints
3. Retrieves the best rubric using **hybrid scoring** (semantic embeddings + keyword overlap)
4. Classifies answer difficulty (EASY / MEDIUM / HARD)
5. Sends a difficulty-aware, per-criterion prompt to LLaMA
6. Validates the JSON output; retries up to 2× if invalid
7. Runs a lightweight self-check LLM pass on the final result
8. Returns structured feedback with marks, per-criterion justification, and rubric details

---

## Architecture

```
User Request
    │
    ▼
FastAPI (POST /api/evaluate)
    │
    ├─ subject_detector   →  keyword-frequency subject hint
    │
    ├─ RubricRetriever    →  query enrichment
    │      ├─ sentence-transformers (all-MiniLM-L6-v2)   ← primary
    │      └─ TF-IDF bigrams                              ← fallback if not installed
    │      + keyword_score (per-rubric keyword list)
    │      → hybrid_score = 0.7 × semantic + 0.3 × keyword
    │      → is_confident (score ≥ threshold)
    │
    ├─ evaluate()
    │      ├─ input guard (< 5 chars → immediate fallback)
    │      ├─ _classify_difficulty  (EASY / MEDIUM / HARD)
    │      ├─ _build_prompt         (difficulty-aware, per-criterion)
    │      ├─ _call_llm             (Ollama, temp=0.25, timeout=60s)
    │      ├─ _extract_json         (brace-depth parser)
    │      ├─ _validate_output      (marks range, all criteria in justification)
    │      ├─ retry ×2 if invalid   (stricter prompt each attempt)
    │      └─ _self_check           (second LLM verification call)
    │
    └─ EvaluateResponse  →  JSON to frontend
```

---

## RAG Explanation

### Why RAG?

Without RAG, the LLM would be asked to score an answer with no grounding — it would invent its own criteria, hallucinate standards, and produce inconsistent results. RAG anchors the LLM to a specific rubric.

### Pipeline

**1. Indexing (at startup)**
Each rubric is flattened into a text representation: `subject + topic + keywords + criteria names + descriptions`. These are encoded into dense vectors (sentence-transformers) or sparse TF-IDF vectors.

**2. Query Enrichment**
Short questions are ambiguous for TF-IDF. The enrichment step appends subject-specific context words when trigger words are detected:
- `"solve"` → `"algebra mathematics equation variable"`
- `"wave"` → `"physics frequency wavelength amplitude"`
- `"essay"` → `"english writing structure argument"`

**3. Hybrid Retrieval**
```
hybrid_score = 0.7 × semantic_similarity + 0.3 × keyword_overlap
```
- **Semantic similarity** — cosine similarity between encoded question and encoded rubric text
- **Keyword overlap** — fraction of rubric-specific keywords present in the question

**4. Confidence Threshold**
- Embeddings backend: threshold = 0.35
- TF-IDF backend: threshold = 0.10

If the best score is below threshold, the fallback (General Knowledge) rubric is used instead.

**5. Top-K Logging**
Top-3 candidates are logged with scores for every request, enabling offline analysis of retrieval quality.

---

## LLM Prompt Design

### Key design decisions

**Strict JSON-only output**
The system prompt opens with `"Output ONLY valid JSON — no preamble, no markdown fences, nothing else."` and the user prompt closes with `"Output ONLY JSON:"`. This dramatically reduces fence artifacts and preambles.

**Difficulty-aware guidance**

| Difficulty | Trigger | LLM Instruction |
|---|---|---|
| EASY | "what is", "define", "list", word count < 20 | Award marks generously for core concept |
| MEDIUM | default | Partial marks for partial explanations |
| HARD | "prove", "analyse", "justify", word count > 80 | Strict — require clear demonstration |

**Per-criterion structure**
The prompt explicitly lists each criterion with its name, mark weight, and description — and instructs the model to produce one justification line per criterion:
```
CriterionName: awarded/weight — reason
```
This makes validation deterministic: the validator checks whether each criterion name appears in the justification string.

**One-shot example**
A worked example in the system prompt establishes the expected format, dramatically improving output consistency on first attempt.

**Temperature 0.25**
Higher than the original 0.1 — reduces the model's tendency to output zero marks (which was the main cause of the 0% easy-question score) while maintaining reasonable consistency.

### Retry logic

```
Attempt 0  →  standard prompt
Attempt 1  →  "RETRY: Previous attempt was rejected. Ensure EVERY criterion..."
Attempt 2  →  "FINAL ATTEMPT: address all N criteria..."
```
After 3 failed attempts, the last parsed result is returned as best-effort (marks clamped to valid range). If no JSON was ever parsed, the fallback response is returned.

### Self-check

After a result passes validation, a second lightweight LLM call verifies:
- Is `marks_awarded ≤ max_marks`?
- Are all criterion names present in justification?

If the self-check fails, one more retry is triggered. Self-check errors are logged but do not block the response.

---

## Rubric Coverage

| ID        | Subject     | Topic                        | Max | Criteria |
|-----------|-------------|------------------------------|-----|----------|
| physics_1 | Physics     | Newton's Laws of Motion      | 5   | 3        |
| physics_2 | Physics     | Energy and Work              | 5   | 3        |
| physics_3 | Physics     | Waves and Light              | 4   | 3        |
| math_1    | Mathematics | Algebra — Equations          | 5   | 4        |
| math_2    | Mathematics | Geometry — Shapes and Proofs | 5   | 3        |
| math_3    | Mathematics | Calculus — Differentiation   | 5   | 3        |
| english_1 | English     | Essay Writing                | 5   | 3        |
| english_2 | English     | Literary Analysis            | 5   | 3        |
| fallback  | General     | General Knowledge            | 5   | 3        |

All rubrics are validated at startup: `sum(criteria.marks_weight) == max_marks`.

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) with `llama3.2` pulled

```bash
ollama pull llama3.2
ollama serve          # binds to http://localhost:11434
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

> **Note on `sentence-transformers`:** This installs PyTorch (CPU build, ~300 MB) and downloads `all-MiniLM-L6-v2` (~90 MB) on first run. If you prefer a zero-extra-dependency mode, remove the `sentence-transformers` line from `requirements.txt` — the system falls back to TF-IDF automatically.

```bash
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Health check: `GET /`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:5173`.

---

## Dependencies

### Backend (`requirements.txt`)

| Package | Purpose |
|---|---|
| `fastapi` | HTTP framework |
| `uvicorn[standard]` | ASGI server |
| `pydantic` | Request/response validation |
| `requests` | Ollama HTTP client |
| `scikit-learn` | TF-IDF vectoriser (retrieval fallback) |
| `numpy` | Vector maths |
| `sentence-transformers` | Semantic embeddings (recommended) |

### Frontend (`package.json`)

| Package | Purpose |
|---|---|
| `react` + `react-dom` | UI library |
| `vite` | Build tool / dev server |
| `@vitejs/plugin-react` | Vite React plugin |

---

## API Reference

### `POST /api/evaluate`

**Request**
```json
{
  "question": "Explain Newton's second law and give an example.",
  "answer": "F = ma means force equals mass times acceleration. A heavier cart needs more force."
}
```

**Response**
```json
{
  "rubric_id": "physics_1",
  "marks_awarded": 4,
  "max_marks": 5,
  "feedback": "Good explanation with a relevant example. Terminology could be more precise.",
  "justification": "Conceptual Understanding: 2/2 — correct law stated with formula. Application: 2/2 — clear real-world example. Terminology: 0/1 — 'net force' and vector nature not mentioned.",
  "rubric": {
    "id": "physics_1",
    "subject": "physics",
    "topic": "Newton's Laws of Motion",
    "max_marks": 5,
    "keywords": ["force", "acceleration", "inertia", "mass", "newton", "..."],
    "criteria": [
      { "name": "Conceptual Understanding", "description": "...", "marks_weight": 2 },
      { "name": "Application",              "description": "...", "marks_weight": 2 },
      { "name": "Terminology",             "description": "...", "marks_weight": 1 }
    ]
  }
}
```

**Error responses**

| Code | Condition |
|---|---|
| 400 | Question or answer empty, or answer < 5 characters |
| 500 | Unexpected server error |

---

## Structured Logs

All events are emitted as JSON lines to stdout:

```json
{"event": "retriever_init", "backend": "sentence-transformers", "level": "INFO", "logger": "app.services.rag"}
{"event": "rubric_retrieved", "top_k": [{"id": "physics_1", "score": 0.72}], "selected": "physics_1", "score": 0.72, "confident": true, "level": "INFO"}
{"event": "eval_start", "difficulty": "MEDIUM", "rubric": "physics_1", "level": "INFO"}
{"event": "llm_response", "attempt": 0, "preview": "{\"marks_awarded\": 4 ...", "level": "INFO"}
{"event": "eval_success", "attempt": 0, "marks": "4/5", "difficulty": "MEDIUM", "level": "INFO"}
```

Key events to monitor:

| Event | Meaning |
|---|---|
| `low_confidence_fallback` | Retrieval score below threshold — fallback rubric used |
| `validation_failed` | LLM output didn't pass validation — retry triggered |
| `self_check_failed` | Self-check found inconsistency — retry triggered |
| `best_effort_result` | All retries exhausted — returning best available result |
| `fallback_triggered` | Hard failure — returning zero-score fallback |

---

## Project Structure

```
backend/
  app/
    main.py                   # FastAPI app, CORS
    routes/
      evaluate.py             # POST /api/evaluate — orchestration
    services/
      rubric_engine.py        # 9 rubrics with keywords; startup validation
      rag.py                  # Hybrid retriever (embeddings + keyword); query enrichment
      evaluator.py            # Difficulty classify, prompt build, retry, self-check
    models/
      schemas.py              # Pydantic request/response models
    utils/
      subject_detector.py     # Keyword-frequency subject detection
      logger.py               # Structured JSON logger
  requirements.txt

frontend/
  src/
    components/ResultCard.jsx # Score banner, rubric, feedback display
    App.jsx                   # Form + state management
    api.js                    # fetch wrapper
    styles.css                # Plain CSS
    main.jsx                  # React entry point
  index.html
  package.json
  vite.config.js

README.md
```

---

## Future Improvements

- **Rubric classifier** — train a small classifier (question → rubric_id) to replace retrieval entirely for known rubric types
- **Persistent rubric store** — move rubrics to SQLite or YAML for editor-friendly management
- **Streaming responses** — stream Ollama output to reduce time-to-first-byte
- **Async LLM calls** — use `httpx` + FastAPI `async def` for non-blocking evaluation
- **Auth + history** — save evaluations per student/session to a database
- **Confidence in response** — expose retrieval score in the API so the UI can warn when rubric match is weak
