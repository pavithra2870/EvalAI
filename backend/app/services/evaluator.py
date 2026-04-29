"""
LLM-based answer evaluator using Ollama.

Pipeline per request:
  1. Input validation (too short → immediate fallback)
  2. Difficulty classification (EASY / MEDIUM / HARD)
  3. Prompt construction (difficulty-aware, per-criterion instructions)
  4. LLM call → raw text
  5. JSON extraction (brace-depth parser, robust to surrounding text)
  6. Output validation (marks range, all criteria present in justification)
  7. Retry up to 2 more times if validation fails, with stricter prompt
  8. Self-check pass on final result (second LLM call, lightweight)
  9. Return normalized result or graceful fallback
"""
import json
from typing import Any, Dict, List, Literal

import requests

from app.utils.logger import get_logger

log = get_logger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:latest"

_MIN_ANSWER_CHARS = 5
_MAX_RETRIES = 2  # total attempts = 1 + _MAX_RETRIES

# ── Difficulty ────────────────────────────────────────────────────────────────

_HARD_CUES = {
    "prove", "derive", "analyze", "analyse", "evaluate",
    "compare", "contrast", "discuss", "explain why", "justify",
}
_EASY_CUES = {
    "what is", "define", "name", "list", "state",
    "who is", "when did", "where is", "what are",
}

_DIFFICULTY_GUIDANCE: Dict[str, str] = {
    "EASY": (
        "This is a simple recall or definition question. "
        "Award marks generously if the core concept is correctly stated. "
        "Do NOT penalise for lack of depth or examples."
    ),
    "MEDIUM": (
        "This is an explanation question. "
        "Award partial marks for partially correct explanations. "
        "Require basic reasoning but not exhaustive detail."
    ),
    "HARD": (
        "This is a complex reasoning or multi-step question. "
        "Be strict — require clear demonstration of understanding for each criterion. "
        "Penalise vague or unsupported statements."
    ),
}

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a strict academic evaluator. Score a student's answer using ONLY the rubric provided.

RULES (follow every rule without exception):
1. Evaluate EACH criterion separately — never skip one.
2. Assign an integer mark per criterion. The marks MUST sum to marks_awarded.
3. Never award more than max_marks in total.
4. Give partial credit where the student partially satisfies a criterion.
5. Do not invent criteria not listed in the rubric.
6. Output ONLY valid JSON — no preamble, no markdown fences, nothing else.

OUTPUT FORMAT (exact schema):
{
  "marks_awarded": <integer ≤ max_marks>,
  "max_marks": <integer>,
  "feedback": "<1-2 sentence student-facing comment>",
  "justification": "<per-criterion: CriterionName: X/Y — reason. One line per criterion.>"
}

EXAMPLE:
Rubric: Max 3 marks. Criteria: Definition (2 marks): Define photosynthesis. | Example (1 mark): Give an example.
Student: "Photosynthesis is the process by which plants make food using sunlight."
Output:
{
  "marks_awarded": 2,
  "max_marks": 3,
  "feedback": "Good definition but no example was provided.",
  "justification": "Definition: 2/2 — accurate definition given. Example: 0/1 — no example mentioned."
}
"""

# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(
    question: str,
    answer: str,
    rubric: Dict[str, Any],
    difficulty: str,
    attempt: int,
) -> str:
    criteria_block = "\n".join(
        f"  {i + 1}. {c['name']} ({c['marks_weight']} marks): {c['description']}"
        for i, c in enumerate(rubric["criteria"])
    )
    retry_note = ""
    if attempt == 1:
        retry_note = (
            "\n⚠ RETRY: Previous attempt was rejected. "
            "Ensure EVERY criterion name appears in the justification field.\n"
        )
    elif attempt >= 2:
        retry_note = (
            f"\n⚠ FINAL ATTEMPT: You MUST address all {len(rubric['criteria'])} criteria "
            "individually. Output strict JSON only.\n"
        )

    return (
        f"{_SYSTEM_PROMPT}"
        f"{retry_note}"
        f"\nDIFFICULTY LEVEL: {difficulty}\n"
        f"Guidance: {_DIFFICULTY_GUIDANCE[difficulty]}\n\n"
        f"Question: {question}\n\n"
        f"Student Answer: {answer}\n\n"
        f"Rubric: {rubric['topic']} (Max marks: {rubric['max_marks']})\n"
        f"Criteria:\n{criteria_block}\n\n"
        f"Justification must include one line per criterion: "
        f"\"CriterionName: awarded/weight — reason\"\n\n"
        f"Output ONLY JSON:"
    )

# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.25},
        },
        timeout=400,
    )
    response.raise_for_status()
    return response.json().get("response", "")

# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(text: str) -> Dict[str, Any]:
    """
    Brace-depth tracker: finds the first complete JSON object in raw text.
    More robust than find/rfind for responses that contain preamble or fences.
    """
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(text[start: i + 1])
                except json.JSONDecodeError:
                    start = -1  # this candidate was malformed; look for next
    raise ValueError("No valid JSON object found in LLM response")

# ── Validation ────────────────────────────────────────────────────────────────

def _validate_output(result: Dict[str, Any], rubric: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    marks = result.get("marks_awarded")
    if not isinstance(marks, (int, float)):
        errors.append("marks_awarded missing or not a number")
    elif int(marks) > rubric["max_marks"]:
        errors.append(f"marks_awarded={marks} exceeds max_marks={rubric['max_marks']}")
    elif int(marks) < 0:
        errors.append("marks_awarded is negative")

    if len(str(result.get("feedback", ""))) < 10:
        errors.append("feedback too short (< 10 chars)")

    justification = str(result.get("justification", ""))
    if len(justification) < 15:
        errors.append("justification too short (< 15 chars)")
    else:
        j_lower = justification.lower()
        for c in rubric["criteria"]:
            if c["name"].lower() not in j_lower:
                errors.append(f"criterion '{c['name']}' missing from justification")

    return errors

# ── Difficulty classifier ─────────────────────────────────────────────────────

def _classify_difficulty(question: str, answer: str) -> Literal["EASY", "MEDIUM", "HARD"]:
    q = question.lower()
    word_count = len(answer.split())
    if any(cue in q for cue in _HARD_CUES) or word_count > 80:
        return "HARD"
    if any(cue in q for cue in _EASY_CUES) or word_count < 20:
        return "EASY"
    return "MEDIUM"

# ── Normalise ─────────────────────────────────────────────────────────────────

def _normalize(result: Dict[str, Any], rubric: Dict[str, Any]) -> Dict[str, Any]:
    result["marks_awarded"] = max(0, min(int(result.get("marks_awarded", 0)), rubric["max_marks"]))
    result["max_marks"] = rubric["max_marks"]
    result.setdefault("feedback", "No feedback provided.")
    result.setdefault("justification", "No justification provided.")
    return result

# ── Self-check ────────────────────────────────────────────────────────────────

def _self_check(result: Dict[str, Any], rubric: Dict[str, Any]) -> bool:
    """
    Lightweight second LLM call to verify the result is internally consistent.
    Returns True (pass) on any error — self-check failure should not block output.
    """
    criteria_names = ", ".join(c["name"] for c in rubric["criteria"])
    verify_prompt = (
        f"Verify this evaluation. Reply ONLY with JSON: "
        f'{{\"valid\": true}} or {{\"valid\": false, \"reason\": \"...\"}}\n\n'
        f"Criteria required in justification: {criteria_names}\n"
        f"max_marks: {rubric['max_marks']}\n"
        f"marks_awarded: {result['marks_awarded']}\n"
        f"justification: {result['justification']}\n\n"
        f"Is marks_awarded ≤ max_marks AND every criterion mentioned?"
    )
    try:
        raw = _call_llm(verify_prompt)
        check = _extract_json(raw)
        passed = bool(check.get("valid", True))
        if not passed:
            log.warning({"event": "self_check_failed", "reason": check.get("reason", "")})
        return passed
    except Exception as exc:
        log.warning({"event": "self_check_error", "error": str(exc)})
        return True  # fail open — don't block on self-check errors

# ── Main entry point ──────────────────────────────────────────────────────────

def evaluate(question: str, answer: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    # ── Input guard ───────────────────────────────────────────────────────────
    if len(answer.strip()) < _MIN_ANSWER_CHARS:
        log.warning({"event": "answer_too_short", "length": len(answer.strip())})
        return _fallback_response(rubric, "Answer too short to evaluate meaningfully.")

    difficulty = _classify_difficulty(question, answer)
    log.info({"event": "eval_start", "difficulty": difficulty, "rubric": rubric["id"]})

    last_result: Dict[str, Any] = {}
    last_errors: List[str] = []

    for attempt in range(_MAX_RETRIES + 1):
        try:
            prompt = _build_prompt(question, answer, rubric, difficulty, attempt)
            raw = _call_llm(prompt)

            log.info({"event": "llm_response", "attempt": attempt, "preview": raw[:200]})

            result = _extract_json(raw)
            errors = _validate_output(result, rubric)

            if not errors:
                result = _normalize(result, rubric)
                # Self-check on accepted result
                if not _self_check(result, rubric):
                    last_result = result
                    last_errors = ["self_check_failed"]
                    continue  # retry with stricter prompt
                log.info({
                    "event": "eval_success",
                    "attempt": attempt,
                    "marks": f"{result['marks_awarded']}/{result['max_marks']}",
                    "difficulty": difficulty,
                })
                return result

            last_result = result
            last_errors = errors
            log.warning({"event": "validation_failed", "attempt": attempt, "errors": errors})

        except (ValueError, json.JSONDecodeError) as exc:
            last_errors = [str(exc)]
            log.warning({"event": "parse_error", "attempt": attempt, "error": str(exc)})

        except requests.exceptions.RequestException as exc:
            log.error({"event": "llm_unreachable", "error": str(exc)})
            return _fallback_response(rubric, f"LLM service unavailable: {exc}")

    # ── Best-effort: return last parsed result with validation warnings ────────
    if last_result:
        result = _normalize(last_result, rubric)
        log.warning({"event": "best_effort_result", "unresolved_errors": last_errors})
        return result

    return _fallback_response(rubric, f"All {_MAX_RETRIES + 1} attempts failed: {last_errors}")


def _fallback_response(rubric: Dict[str, Any], reason: str) -> Dict[str, Any]:
    log.error({"event": "fallback_triggered", "reason": reason})
    return {
        "marks_awarded": 0,
        "max_marks": rubric["max_marks"],
        "feedback": "Evaluation could not be completed automatically.",
        "justification": f"Fallback triggered — {reason}",
    }
