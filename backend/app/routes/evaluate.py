import json

from fastapi import APIRouter, HTTPException

from app.models.schemas import EvaluateRequest, EvaluateResponse
from app.services.evaluator import evaluate
from app.services.rag import RubricRetriever
from app.services.rubric_engine import get_rubrics
from app.utils.logger import get_logger
from app.utils.subject_detector import detect_subject

router = APIRouter()
log = get_logger(__name__)

# Built once at import time — safe to reuse across requests
_retriever = RubricRetriever()

_MIN_ANSWER_LENGTH = 5   # characters
_CONFIDENCE_FALLBACK_ID = "fallback"


def _fallback_rubric() -> dict:
    for r in get_rubrics():
        if r["id"] == _CONFIDENCE_FALLBACK_ID:
            return r
    return get_rubrics()[-1]


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_answer(request: EvaluateRequest):
    question = request.question.strip()
    answer = request.answer.strip()

    # ── Input validation ──────────────────────────────────────────────────────
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    if not answer:
        raise HTTPException(status_code=400, detail="Answer must not be empty.")
    if len(answer) < _MIN_ANSWER_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Answer is too short (minimum {_MIN_ANSWER_LENGTH} characters).",
        )

    # ── Subject detection (logged, used as extra signal) ──────────────────────
    subject = detect_subject(question)

    # ── Rubric retrieval ──────────────────────────────────────────────────────
    rubric, score, is_confident = _retriever.retrieve(question)

    if not is_confident:
        log.warning({
            "event": "low_confidence_fallback",
            "detected_subject": subject,
            "retrieval_score": round(score, 3),
            "rejected_rubric": rubric["id"],
            "fallback_to": _CONFIDENCE_FALLBACK_ID,
        })
        rubric = _fallback_rubric()

    log.info({
        "event": "evaluate_request",
        "subject_detected": subject,
        "rubric_id": rubric["id"],
        "retrieval_score": round(score, 3),
        "confident": is_confident,
    })

    # ── LLM evaluation ────────────────────────────────────────────────────────
    result = evaluate(question, answer, rubric)

    return EvaluateResponse(
        rubric=rubric,
        marks_awarded=result["marks_awarded"],
        max_marks=result["max_marks"],
        feedback=result["feedback"],
        justification=result["justification"],
        rubric_id=rubric["id"],
    )
