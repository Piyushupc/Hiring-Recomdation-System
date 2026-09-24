"""
Combines the individual component scores into one final score.

Any component that couldn't be computed (because the underlying data --
e.g. experience, current/expected salary -- wasn't available) is passed
in as None. Those components are dropped entirely and the remaining
weights are rescaled proportionally, so a missing field never drags the
score down (and never silently gets treated as 0). If everything is
missing, there's no score to give.
"""

from typing import Dict, Optional

DEFAULT_WEIGHTS = {
    "stability": 0.30,
    "long_term": 0.30,
    "monetary": 0.20,
    "culture": 0.20,
}


def generate_final_score(
    stability: Optional[float],
    long_term: Optional[float],
    monetary: Optional[float],
    culture: Optional[float],
    weights: Dict[str, float] = None,
) -> Optional[float]:
    weights = weights or DEFAULT_WEIGHTS
    components = {
        "stability": stability,
        "long_term": long_term,
        "monetary": monetary,
        "culture": culture,
    }

    available = {k: v for k, v in components.items() if v is not None}
    if not available:
        return None

    weight_total = sum(weights[k] for k in available)
    weighted_sum = sum(available[k] * weights[k] for k in available)

    final_score = weighted_sum / weight_total
    return round(final_score, 2)
