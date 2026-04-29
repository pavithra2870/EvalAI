"""
Hybrid rubric retrieval.

Scoring: final = 0.7 * semantic_similarity + 0.3 * keyword_overlap
Semantic backend: sentence-transformers (all-MiniLM-L6-v2) if installed,
                  TF-IDF bigrams otherwise.
Confidence: score >= threshold → is_confident=True, else caller uses fallback rubric.
"""
import json
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.rubric_engine import get_rubrics
from app.utils.logger import get_logger

log = get_logger(__name__)

# ── Query enrichment map ──────────────────────────────────────────────────────
# Adds subject-specific context words when matching keywords are found in the
# question, improving TF-IDF recall for short or ambiguous questions.

_QUERY_HINTS: Dict[str, str] = {
    # Mathematics
    "solve":        "algebra mathematics equation variable",
    "calculate":    "mathematics formula computation",
    "equation":     "algebra mathematics variable linear",
    "differentiate":"calculus derivative mathematics",
    "integrate":    "calculus integral mathematics",
    "prove":        "geometry proof mathematics theorem",
    "triangle":     "geometry mathematics angle shape",
    "probability":  "statistics mathematics",
    "quadratic":    "algebra mathematics equation polynomial",
    # Physics
    "force":        "physics newton mechanics dynamics",
    "velocity":     "physics kinematics motion",
    "acceleration": "physics newton motion dynamics",
    "energy":       "physics work joule power",
    "wave":         "physics frequency wavelength amplitude",
    "light":        "physics optics wave refraction reflection",
    "gravity":      "physics newton force mass",
    "momentum":     "physics motion mass velocity",
    "inertia":      "physics newton mass motion",
    # English
    "essay":        "english writing structure argument",
    "analyze":      "english literary analysis",
    "analyse":      "english literary analysis",
    "poem":         "english poetry literary",
    "character":    "english literary narrative",
    "theme":        "english literary analysis",
    "metaphor":     "english literary device",
    "simile":       "english literary device",
}

_EMBEDDING_CONFIDENCE = 0.35
_TFIDF_CONFIDENCE = 0.10
_TOP_K = 3  # retrieve top-K candidates before picking best


def _enrich_query(question: str) -> str:
    """Append subject hints for any matching trigger words in the question."""
    q_lower = question.lower()
    extras = [exp for trigger, exp in _QUERY_HINTS.items() if trigger in q_lower]
    return question + (" " + " ".join(extras) if extras else "")


def _keyword_score(rubric: Dict[str, Any], question_lower: str) -> float:
    """Fraction of rubric keywords present in the question (0.0–1.0)."""
    kws = rubric.get("keywords", [])
    if not kws:
        return 0.0
    return sum(1 for kw in kws if kw in question_lower) / len(kws)


class RubricRetriever:
    """
    Primary: sentence-transformers (all-MiniLM-L6-v2).
    Fallback: TF-IDF with bigrams (if sentence-transformers not installed).
    Both use the same hybrid scoring and confidence threshold logic.
    """

    def __init__(self) -> None:
        self.rubrics = get_rubrics()
        self._use_embeddings = False

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            texts = [self._rubric_to_text(r) for r in self.rubrics]
            self._embeddings = self._model.encode(texts, convert_to_numpy=True)
            self._use_embeddings = True
            self._threshold = _EMBEDDING_CONFIDENCE
            log.info({"event": "retriever_init", "backend": "sentence-transformers"})
        except ImportError:
            self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            texts = [self._rubric_to_text(r) for r in self.rubrics]
            self._tfidf_matrix = self._vectorizer.fit_transform(texts)
            self._threshold = _TFIDF_CONFIDENCE
            log.info({"event": "retriever_init", "backend": "tfidf-bigram"})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _rubric_to_text(self, rubric: Dict[str, Any]) -> str:
        parts = [rubric["subject"], rubric["topic"]] + rubric.get("keywords", [])
        for c in rubric["criteria"]:
            parts += [c["name"], c["description"]]
        return " ".join(parts)

    def _semantic_scores(self, enriched: str) -> np.ndarray:
        if self._use_embeddings:
            q_vec = self._model.encode([enriched], convert_to_numpy=True)
            return cosine_similarity(q_vec, self._embeddings).flatten()
        q_vec = self._vectorizer.transform([enriched])
        return cosine_similarity(q_vec, self._tfidf_matrix).flatten()

    # ── Public API ────────────────────────────────────────────────────────────

    def retrieve(self, question: str) -> Tuple[Dict[str, Any], float, bool]:
        """
        Returns:
            rubric       — best matching rubric dict
            score        — hybrid score [0, 1]
            is_confident — True when score >= confidence threshold
        """
        enriched = _enrich_query(question)
        q_lower = question.lower()

        sem = self._semantic_scores(enriched)
        hybrid = np.array([
            0.7 * sem[i] + 0.3 * _keyword_score(self.rubrics[i], q_lower)
            for i in range(len(self.rubrics))
        ])

        top_k_idx = np.argsort(hybrid)[::-1][:_TOP_K]
        best_idx = int(top_k_idx[0])
        best_score = float(hybrid[best_idx])
        is_confident = best_score >= self._threshold

        top_k_summary = [
            {"id": self.rubrics[i]["id"], "score": round(float(hybrid[i]), 3)}
            for i in top_k_idx
        ]
        log.info({
            "event": "rubric_retrieved",
            "top_k": top_k_summary,
            "selected": self.rubrics[best_idx]["id"],
            "score": round(best_score, 3),
            "confident": is_confident,
            "backend": "embeddings" if self._use_embeddings else "tfidf",
        })

        return self.rubrics[best_idx], best_score, is_confident
