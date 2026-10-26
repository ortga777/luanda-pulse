# Architecture

## Intended flow

1. A client submits a photo and a user-provided address.
2. An authenticated API or a deliberately limited public flow authorizes upload to a private S3 bucket.
3. A backend workflow invokes the analysis Lambda with the configured bucket/key and address.
4. Rekognition supplies visual labels. A domain-specific model must be evaluated before predictions are treated as urban-issue classifications.
5. Amazon Location geocodes the supplied address. This is a candidate location, not proof of where the image was captured.
6. A report is persisted with classification confidence, severity assessment state, location provenance, and review status.
7. Authorized reviewers validate reports before any official escalation.

## Current implementation boundary

This initial foundation contains input validation, guarded AWS calls, conservative generic-label handling, and unit tests. It does not yet provide authentication, upload URL issuance, durable report storage, a map UI, deduplication, or official municipal submission.

## Production gates

- Evaluate the classifier against a documented representative test set.
- Implement authentication, authorization, rate limits, and abuse controls.
- Configure private S3, encryption, lifecycle/retention, and least-privilege IAM.
- Add durable storage and idempotent report submission.
- Add structured logs, metrics, alarms, tracing, and operational runbooks.
- Publish privacy/consent information appropriate for citizen images.
- Deploy reviewed infrastructure-as-code with environment separation and rollback.
