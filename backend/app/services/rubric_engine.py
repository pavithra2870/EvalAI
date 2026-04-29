from typing import Any, Dict, List

# Module-level cache — built and validated once on first access
_RUBRICS: List[Dict[str, Any]] | None = None


def get_rubrics() -> List[Dict[str, Any]]:
    global _RUBRICS
    if _RUBRICS is None:
        _RUBRICS = _build_rubrics()
        _validate(_RUBRICS)
    return _RUBRICS


def _validate(rubrics: List[Dict[str, Any]]) -> None:
    """Raise ValueError early if any rubric has structural issues."""
    required_fields = {"id", "subject", "topic", "max_marks", "criteria", "keywords"}
    for r in rubrics:
        missing = required_fields - set(r.keys())
        if missing:
            raise ValueError(f"Rubric '{r.get('id', '?')}' missing fields: {missing}")
        weight_sum = sum(c["marks_weight"] for c in r["criteria"])
        if weight_sum != r["max_marks"]:
            raise ValueError(
                f"Rubric '{r['id']}': criteria weights sum to {weight_sum}, "
                f"expected max_marks={r['max_marks']}"
            )


def _build_rubrics() -> List[Dict[str, Any]]:
    return [
        # ── Physics ─────────────────────────────────────────────────────────────
        {
            "id": "physics_1",
            "subject": "physics",
            "topic": "Newton's Laws of Motion",
            "max_marks": 5,
            "keywords": [
                "force", "acceleration", "inertia", "mass", "newton",
                "motion", "velocity", "momentum", "second law", "first law",
            ],
            "criteria": [
                {
                    "name": "Conceptual Understanding",
                    "description": "Correctly states and explains Newton's laws",
                    "marks_weight": 2,
                },
                {
                    "name": "Application",
                    "description": "Applies laws to a given scenario or example",
                    "marks_weight": 2,
                },
                {
                    "name": "Terminology",
                    "description": "Uses correct physics terminology",
                    "marks_weight": 1,
                },
            ],
        },
        {
            "id": "physics_2",
            "subject": "physics",
            "topic": "Energy and Work",
            "max_marks": 5,
            "keywords": [
                "energy", "work", "kinetic", "potential", "joule",
                "power", "displacement", "W=Fd", "KE", "conservation",
            ],
            "criteria": [
                {
                    "name": "Definition",
                    "description": "Correctly defines work and energy",
                    "marks_weight": 2,
                },
                {
                    "name": "Formula Usage",
                    "description": "Uses correct formulas (W=Fd, KE=½mv²)",
                    "marks_weight": 2,
                },
                {
                    "name": "Units",
                    "description": "States correct SI units (Joules, Newtons)",
                    "marks_weight": 1,
                },
            ],
        },
        {
            "id": "physics_3",
            "subject": "physics",
            "topic": "Waves and Light",
            "max_marks": 4,
            "keywords": [
                "wave", "light", "frequency", "wavelength", "amplitude",
                "sound", "electromagnetic", "transverse", "refraction", "reflection",
            ],
            "criteria": [
                {
                    "name": "Properties",
                    "description": "Describes wave properties: wavelength, frequency, amplitude",
                    "marks_weight": 2,
                },
                {
                    "name": "Examples",
                    "description": "Provides relevant real-world examples of waves",
                    "marks_weight": 1,
                },
                {
                    "name": "Equation",
                    "description": "Uses wave equation v = fλ correctly",
                    "marks_weight": 1,
                },
            ],
        },
        # ── Mathematics ──────────────────────────────────────────────────────────
        {
            "id": "math_1",
            "subject": "mathematics",
            "topic": "Algebra — Equations",
            "max_marks": 5,
            "keywords": [
                "solve", "equation", "variable", "algebra", "linear",
                "quadratic", "simplify", "expression", "coefficient", "substitute",
            ],
            "criteria": [
                {
                    "name": "Setup",
                    "description": "Correctly sets up the equation from the problem",
                    "marks_weight": 1,
                },
                {
                    "name": "Method",
                    "description": "Uses a valid algebraic method to solve",
                    "marks_weight": 2,
                },
                {
                    "name": "Calculation",
                    "description": "Arithmetic steps are correct",
                    "marks_weight": 1,
                },
                {
                    "name": "Final Answer",
                    "description": "Correct final answer with units if applicable",
                    "marks_weight": 1,
                },
            ],
        },
        {
            "id": "math_2",
            "subject": "mathematics",
            "topic": "Geometry — Shapes and Proofs",
            "max_marks": 5,
            "keywords": [
                "triangle", "angle", "theorem", "proof", "circle",
                "polygon", "geometry", "area", "perimeter", "pythagoras",
            ],
            "criteria": [
                {
                    "name": "Theorem Identification",
                    "description": "Correctly identifies the relevant geometric theorem",
                    "marks_weight": 2,
                },
                {
                    "name": "Logical Steps",
                    "description": "Proof proceeds in clear, logical steps",
                    "marks_weight": 2,
                },
                {
                    "name": "Conclusion",
                    "description": "Reaches and states the correct conclusion",
                    "marks_weight": 1,
                },
            ],
        },
        {
            "id": "math_3",
            "subject": "mathematics",
            "topic": "Calculus — Differentiation",
            "max_marks": 5,
            "keywords": [
                "differentiate", "derivative", "calculus", "function",
                "rate of change", "gradient", "chain rule", "product rule", "integrate",
            ],
            "criteria": [
                {
                    "name": "Rule Application",
                    "description": "Applies correct differentiation rules (power, chain, product)",
                    "marks_weight": 2,
                },
                {
                    "name": "Computation",
                    "description": "Computes the derivative correctly",
                    "marks_weight": 2,
                },
                {
                    "name": "Simplification",
                    "description": "Simplifies the result to its standard form",
                    "marks_weight": 1,
                },
            ],
        },
        # ── English ──────────────────────────────────────────────────────────────
        {
            "id": "english_1",
            "subject": "english",
            "topic": "Essay Writing",
            "max_marks": 5,
            "keywords": [
                "essay", "write", "paragraph", "argument", "introduction",
                "conclusion", "persuasive", "structure", "body", "topic sentence",
            ],
            "criteria": [
                {
                    "name": "Structure",
                    "description": "Clear introduction, body paragraphs, and conclusion",
                    "marks_weight": 2,
                },
                {
                    "name": "Content",
                    "description": "Arguments are relevant and well-developed",
                    "marks_weight": 2,
                },
                {
                    "name": "Language",
                    "description": "Correct grammar, varied vocabulary, and appropriate style",
                    "marks_weight": 1,
                },
            ],
        },
        {
            "id": "english_2",
            "subject": "english",
            "topic": "Literary Analysis",
            "max_marks": 5,
            "keywords": [
                "analyze", "analyse", "poem", "poetry", "novel", "character",
                "theme", "metaphor", "literary", "author", "imagery", "symbolism",
            ],
            "criteria": [
                {
                    "name": "Comprehension",
                    "description": "Demonstrates understanding of the text",
                    "marks_weight": 2,
                },
                {
                    "name": "Analysis",
                    "description": "Analyses literary devices, themes, and techniques",
                    "marks_weight": 2,
                },
                {
                    "name": "Evidence",
                    "description": "Supports claims with direct quotes or specific examples",
                    "marks_weight": 1,
                },
            ],
        },
        # ── Fallback ─────────────────────────────────────────────────────────────
        {
            "id": "fallback",
            "subject": "general",
            "topic": "General Knowledge",
            "max_marks": 5,
            "keywords": [],  # no keyword boost — relies entirely on semantic match
            "criteria": [
                {
                    "name": "Relevance",
                    "description": "Answer directly addresses the question",
                    "marks_weight": 2,
                },
                {
                    "name": "Accuracy",
                    "description": "Information provided is factually correct",
                    "marks_weight": 2,
                },
                {
                    "name": "Clarity",
                    "description": "Answer is clearly expressed and well-organised",
                    "marks_weight": 1,
                },
            ],
        },
    ]
