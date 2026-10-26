# Deadline deployment checklist (AWS Console)

This is a short deployment path for the submission deadline, not a claim that the service is already deployed. The API accepts JPEG/PNG images up to 5 MiB and stores reports as JSON objects in a private S3 bucket.

## 1. Publish the web interface

1. Open the repository **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Open **Actions** and inspect the **Deploy Luanda Pulse web** workflow. The workflow deploys the `web/` directory.
4. In **Settings → Secrets and variables → Actions → Variables**, add a repository variable named `LUANDA_PULSE_API_URL` only after the API exists. Its value must be the full HTTPS endpoint ending in `/reports`.
5. The page URL should be `https://ortga777.github.io/luanda-pulse/` after a successful deployment.

Until the API variable is set and a deployment succeeds, the page intentionally reports that submissions are not enabled.

## 2. Create private storage

In AWS Console, choose the same region for all resources (for example, `us-east-1`, if available to the account).

1. Open **S3 → Create bucket**. Use a globally unique name such as `luanda-pulse-reports-<unique-suffix>`.
2. Keep **Block all public access** enabled.
3. Enable default server-side encryption and bucket versioning.
4. Add lifecycle expiration rules appropriate for the submission's data-retention needs. The included template proposes 180 days for photos and 365 days for JSON reports; review those periods before real public use.

Do not place AWS access keys or private images in GitHub.

## 3. Create the Amazon Location place index

1. Open **Amazon Location Service → Place indexes → Create place index**.
2. Give it a unique name (for example, `luanda-pulse-places`) and select a supported data provider.
3. Copy the exact place index name and use the same AWS region as the Lambda function.

Geocoding the citizen's address is not proof that the image was captured there.

## 4. Create the Lambda function

1. Open **Lambda → Create function → Author from scratch**.
2. Runtime: **Python 3.12**; architecture: **x86_64** or **arm64**.
3. Set the handler to `lambda_function.handler`.
4. Copy the complete contents of [deployment/lambda_function.py](../deployment/lambda_function.py) into the console editor's `lambda_function.py`, then choose **Deploy**.
5. Set timeout to 30 seconds and memory to 512 MB.
6. Add environment variables:
   - `LUANDA_PULSE_REPORTS_BUCKET`: exact S3 bucket name
   - `LUANDA_PULSE_PLACE_INDEX`: exact place index name
   - `CORS_ALLOW_ORIGIN`: `https://ortga777.github.io`
7. Give the execution role only the required permissions: CloudWatch Logs, `s3:PutObject` and `s3:DeleteObject` scoped to that bucket's `photos/*` and `reports/*`, `rekognition:DetectLabels`, and `geo:SearchPlaceIndexForText` scoped to the place index where supported.

The code stores photos privately and persists a JSON report. Rekognition's generic labels are **not** a validated urban-issue classifier; results may remain `UNKNOWN` and always require human review.

## 5. Create the HTTPS API

1. Open **API Gateway → Create API → HTTP API**.
2. Add an integration with the Lambda function created above.
3. Add route **POST /reports** and route **OPTIONS /reports**, both integrated with that function.
4. Deploy to a stage and copy the full invoke URL. The endpoint is the invoke URL plus `/reports`.
5. Configure CORS for origin `https://ortga777.github.io`, method `POST` and header `content-type`. Enable throttling/rate limits to reduce abuse.

Set the Lambda `CORS_ALLOW_ORIGIN` to the exact frontend origin (not the full page path). Set the repository variable `LUANDA_PULSE_API_URL` to the full HTTPS `/reports` endpoint, then trigger the Pages workflow again.

## 6. End-to-end verification

- Open the deployed site on desktop and mobile.
- Submit one small JPEG or PNG photo and a real Luanda address.
- Confirm the response has a report ID and `PENDING_REVIEW`.
- Confirm an object exists under `reports/<report-id>.json` and its photo under `photos/` in the private bucket.
- Test invalid file types, files larger than 5 MiB, an unrecognized address, and an AWS permission failure.
- Check CloudWatch logs and the AWS Billing dashboard. S3, Rekognition, Location Service, API Gateway and Lambda may incur charges.

**Security limitation for deadline:** this submission endpoint is public and does not yet include citizen accounts, CAPTCHA, deduplication, a moderator dashboard, or a durable abuse-prevention store. Apply API throttling and monitor usage. Do not describe it as production-hardened until those controls and end-to-end tests are complete.
