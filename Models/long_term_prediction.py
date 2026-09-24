def predict_long_term(avg_tenure):

    if avg_tenure >= 36:
        return {
            "long_term_probability": 90,
            "recommendation": "Very High"
        }

    elif avg_tenure >= 24:
        return {
            "long_term_probability": 75,
            "recommendation": "High"
        }

    elif avg_tenure >= 12:
        return {
            "long_term_probability": 55,
            "recommendation": "Medium"
        }

    else:
        return {
            "long_term_probability": 30,
            "recommendation": "Low"
        }
