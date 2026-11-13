# Hiring Recommendation System

A FastAPI-based prototype with an HTML/JavaScript interface for parsing candidate resumes, calculating configurable recommendation signals, and supporting recruiter review.

## Current capabilities

- Accepts resume uploads in PDF, DOCX, and TXT formats.
- Extracts available candidate details such as name, email, experience, salary information, and skills.
- Calculates component scores and excludes components when required source data is unavailable rather than treating missing values as zero.
- Compares the resulting score with a configurable threshold.
- Supports recruiter-triggered interview or rejection email actions through SMTP.

## Technology

Python, FastAPI, Pydantic, HTML/CSS/JavaScript, PDF/DOCX text extraction libraries, Pandas, scikit-learn/joblib, and SMTP. See the source tree and `requirements.txt` for exact dependencies.

## Run locally

1. Clone the repository and create a Python virtual environment.
2. Install dependencies from `requirements.txt`.
3. Configure environment-specific email and application settings.
4. Start the FastAPI application using `app.py`.
5. Open the frontend served or referenced by the application.

Do not commit real credentials. Use environment variables or a local ignored environment file for secrets.

## Recommendation limitations and responsible use

This is decision-support software, not an automated hiring authority. Resume extraction is heuristic/regex-oriented, and the long-term prediction component includes a model trained using synthetic data. Scores are not objective measures of a person's ability or future performance.

- Make job-related skills and verified experience the primary criteria.
- Do not use proxies such as cultural fit, salary expectations, employment gaps, or inferred stability as automatic rejection criteria.
- Keep a qualified human reviewer in the decision loop.
- Test for disparate impact and document the purpose, provenance, and limitations of each feature.
- Give candidates a way to correct inaccurate extracted information.

## Security and reliability

Before production use, add strict upload-size limits, content-type and file-signature validation, safe parsing/timeouts, and controlled error handling. Restrict CORS to trusted frontend origins. Protect recruiter actions with authentication and authorization, validate email settings, and add audit logs. Minimize resume retention and define access controls.

## Suggested engineering improvements

- Split the application into routers, schemas, services, and model modules.
- Add tests for parsing, scoring, threshold decisions, and email flows.
- Version model artifacts and document training data, evaluation, and reproducibility.
- Add structured logging, deployment configuration, and API documentation.

## Author

Piyush Rai — [GitHub](https://github.com/Piyushupc)
