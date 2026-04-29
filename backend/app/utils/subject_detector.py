SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "physics": [
        "force", "velocity", "acceleration", "momentum", "energy", "work",
        "power", "gravity", "newton", "motion", "wave", "light", "frequency",
        "wavelength", "amplitude", "electric", "magnetic", "charge", "current",
        "voltage", "resistance", "thermodynamics", "heat", "temperature",
        "pressure", "density", "friction", "mass", "speed", "inertia",
        "torque", "optics", "refraction", "reflection",
    ],
    "mathematics": [
        "solve", "equation", "algebra", "geometry", "calculus", "derivative",
        "integral", "matrix", "vector", "probability", "statistics", "proof",
        "theorem", "function", "graph", "triangle", "circle", "angle",
        "differentiate", "integrate", "polynomial", "quadratic", "linear",
        "coordinate", "sequence", "series", "limit", "logarithm", "prime",
        "factorial", "permutation", "combination",
    ],
    "english": [
        "essay", "write", "literary", "analysis", "poem", "poetry", "novel",
        "character", "theme", "metaphor", "simile", "grammar", "punctuation",
        "paragraph", "introduction", "conclusion", "narrative", "author",
        "literature", "language", "vocabulary", "comprehension", "passage",
        "argument", "persuade", "describe", "story", "fiction", "genre",
        "imagery", "symbolism", "tone",
    ],
}


def detect_subject(question: str) -> str:
    """Return the most likely subject from keyword frequency, or 'general' if unclear."""
    question_lower = question.lower()
    scores = {subject: 0 for subject in SUBJECT_KEYWORDS}

    for subject, keywords in SUBJECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in question_lower:
                scores[subject] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"
