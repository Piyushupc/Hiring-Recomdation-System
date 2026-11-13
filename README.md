# Hiring Recommendation System

A FastAPI application that parses candidate resumes, extracts selected fields, calculates configurable recommendation scores, and supports interview or rejection email workflows.

> **Important:** This is a decision-support prototype, not an autonomous hiring decision system. Resume parsing is heuristic-based and requires recruiter review. The included long-term prediction model is trained on synthetic/example data and is not validated for real hiring outcomes.

## Features

- Accept PDF, DOCX, and TXT resumes.
- Extract candidate details such as name, email, phone, experience, salary fields, and skills where available.
- Return missing fields as unavailable rather than silently treating them as zero.
- Calculate rule-based and ML-based score breakdowns.
- Expose a configurable pass threshold.
- Send interview or rejection emails through SMTP when configured.
- Provide interactive API documentation through FastAPI.

## Technology stack

- Python
- FastAPI and Uvicorn
- Pydantic
- scikit-learn and joblib
- pdfplumber and python-docx
- SMTP

## Repository structure

```text
Models/
  cultural_fit.py
  monetary_motivation.py
  stability_score.py
  long_term_prediction.py
  ml_long_term_predictor.py
  recommendation_engine.py
  resume_parser.py
services/
  email_service.py
frontend/
  index.html
app.py
requirements.txt
.env.example
```

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure SMTP settings only if email delivery is needed. Never commit real credentials.

Start the API:

```bash
uvicorn app:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

Open `frontend/index.html` in a browser for the simple frontend. Its API base URL may need adjustment if the backend runs elsewhere.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Basic service status |
| GET | `/health` | Health check |
| POST | `/parse-resume` | Parse an uploaded resume |
| POST | `/score` | Generate score breakdowns |
| POST | `/send-email` | Send an interview or rejection email |

See Swagger UI for request schemas and response examples.

## Scoring and data limitations

- The resume parser uses heuristics/regular expressions; extracted fields must be reviewed.
- Missing inputs should remain missing and must not be interpreted as evidence against a candidate.
- The example model and generated data do not establish predictive validity.
- Criteria such as culture fit, employment stability, and salary motivation can encode unfair proxies. Do not use them as unreviewed filters.
- Evaluate job-related criteria, accessibility, bias, privacy, and applicable employment law before any real-world use.
- Keep a human reviewer responsible for decisions and provide a way to correct extracted candidate information.

## Recommended engineering improvements

- Restrict CORS to explicitly trusted frontend origins outside local development.
- Add upload size limits and content-based file validation.
- Separate route handlers, schemas, and application services.
- Add unit and API integration tests.
- Add model/data versioning and documented evaluation.
- Add authentication and authorization before exposing endpoints publicly.
- Add deployment configuration and structured audit logging.

## Author

Piyush Rai — [GitHub](https://github.com/Piyushupc)
