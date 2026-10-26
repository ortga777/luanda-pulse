# Luanda Pulse

**From Citizen Photo to City Action** — an AI-assisted urban issue reporting platform designed for Luanda, Angola.

Luanda Pulse is intended to help citizens submit reports about road damage, accumulated waste, broken streetlights, and flooding. Reports combine image-analysis signals with a geocoded, user-provided address and remain pending review until validated.

> **Project status: submission build in progress.** A responsive citizen-reporting interface, a report-submission Lambda handler, a private S3 storage design, and a console deployment checklist are now included. The site and AWS API still require deployment and end-to-end verification; do not treat them as live until those steps pass.

## Principles

- **Evidence over guesses:** unknown classifications remain unknown.
- **Confidence is not severity:** model confidence never implies physical danger.
- **Location provenance:** geocoded user text is not proof of image capture location.
- **Privacy by default:** citizen photos must remain private and access must be limited.
- **Human review:** automated classifications are advisory, not official municipal decisions.

## Initial backend foundation

- Python package and Lambda handler.
- Validation for S3 object references and address input.
- AWS S3, Rekognition, and Location Service integration points.
- Conservative fallback classification using exact labels only.
- Unit tests and GitHub Actions CI.

Generic Rekognition labels are not sufficient to guarantee reliable recognition of the target urban issue categories. A custom classifier or suitable vision model must be evaluated on representative images before production use.

## Development

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1

python -m pip install --upgrade pip
pip install -e ".[dev]"
ruff check .
pytest
```

For AWS integration tests, configure credentials through an AWS profile or IAM Identity Center. Do not commit access keys or real citizen images.

## Environment

The Lambda runtime uses these environment variables:

- `AWS_REGION`
- `LUANDA_PULSE_REPORTS_BUCKET`
- `LUANDA_PULSE_PLACE_INDEX`
- Optional `REKOGNITION_PROJECT_VERSION_ARN` for a future Custom Labels integration.

The current handler uses `DetectLabels` as a conservative baseline and does not yet invoke Custom Labels. Do not treat its output as a validated domain-specific classifier.

## Web interface and deadline deployment

- Web app source: [web/index.html](web/index.html)
- AWS Lambda console-ready handler: [deployment/lambda_function.py](deployment/lambda_function.py)
- AWS Console checklist: [docs/deadline-deployment.md](docs/deadline-deployment.md)
- GitHub Pages workflow: [`.github/workflows/pages.yml`](.github/workflows/pages.yml)

The form remains disabled until a real HTTPS API Gateway endpoint is configured as the repository Actions variable `LUANDA_PULSE_API_URL`. The public endpoint needs throttling and end-to-end verification before real citizens use it.

## Architecture and security

See [docs/architecture.md](docs/architecture.md) and [SECURITY.md](SECURITY.md).

## Roadmap

1. Harden and test the backend foundation.
2. Add infrastructure as code, least-privilege IAM, and environment separation.
3. Add secure image-upload flow and durable report storage.
4. Evaluate a vision model against a documented Luanda-focused dataset.
5. Add authenticated review dashboard and map.
6. Add deduplication, audit trail, observability, retention policy, and deployment automation.
7. Run end-to-end tests and a cost/security review before public launch.

## License

No open-source license has been selected yet. All rights remain with the repository owner unless a license is added.
