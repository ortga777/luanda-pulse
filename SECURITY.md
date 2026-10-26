# Security Policy

Do not disclose credentials, personal data, or exploitable details in public issues.
Use GitHub private vulnerability reporting when available.

## Security requirements

- Never commit AWS credentials, access tokens, or private citizen images.
- Keep the reports bucket private and enable encryption at rest.
- Scope the Lambda role to the required bucket/prefix, Rekognition actions, and Location index.
- Validate file size, media type, object key, address, and caller authorization.
- Define retention and deletion policies for citizen images and report metadata.
- Require authentication and authorization for administrative review and status changes.
- Do not expose internal exceptions or personal data in API responses.
- Treat AI classification as advisory; confidence is not physical severity.
