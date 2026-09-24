import os
import joblib
import pandas as pd

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "long_term_model.pkl")
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = joblib.load(_MODEL_PATH)
    return _model


def predict_long_term_ml(avg_tenure, companies, salary_jump, experience):
    """
    Uses the trained RandomForestClassifier to predict long-term retention.
    Feature order must match training: avg_tenure, companies, salary_jump, experience.
    Returns a dict shaped like the rule-based predictor for easy comparison.
    """
    model = _get_model()

    features = pd.DataFrame(
        [[avg_tenure, companies, salary_jump, experience]],
        columns=["avg_tenure", "companies", "salary_jump", "experience"]
    )

    stayed_long_term = int(model.predict(features)[0])
    probability = float(model.predict_proba(features)[0][1]) * 100

    if probability >= 80:
        recommendation = "Very High"
    elif probability >= 60:
        recommendation = "High"
    elif probability >= 40:
        recommendation = "Medium"
    else:
        recommendation = "Low"

    return {
        "long_term_probability": round(probability, 2),
        "recommendation": recommendation,
        "predicted_class": stayed_long_term
    }
