"""Public API handler for submitting a citizen report."""
from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from luanda_pulse.analyzer import (
    InputValidationError,
    MAX_IMAGE_BYTES,
    ReportAnalysis,
    classify_labels,
    validate_address_text,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALLOWED_TYPES = {"image/jpeg": ("jpg", b"\xff\xd8\xff"), "image/png": ("png", b"\x89PNG\r\n\x1a\n")}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_ISSUE_TYPES = {"POTHOLE", "TRASH_ACCUMULATION", "BROKEN_STREETLIGHT", "FLOODING", "UNKNOWN"}


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
            "cache-control": "no-store",
            "access-control-allow-origin": os.environ.get("CORS_ALLOW_ORIGIN", "*"),
            "access-control-allow-headers": "content-type",
            "access-control-allow-methods": "POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Validate a base64 image, store it privately, analyze it and persist the report."""
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "POST"
    )
    if method == "OPTIONS":
        return _response(204, {})
    try:
        if not isinstance(event, dict):
            raise InputValidationError("Request must be a JSON object")
        body = event.get("body", event)
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            raise InputValidationError("Request body must be a JSON object")

        address = validate_address_text(body.get("address_text"))
        issue_type = body.get("issue_type", "UNKNOWN")
        if issue_type not in ALLOWED_ISSUE_TYPES:
            raise InputValidationError("issue_type is not supported")
        description = body.get("description", "")
        if not isinstance(description, str) or len(description) > 1000:
            raise InputValidationError("description must be a string of 1000 characters or fewer")

        content_type = body.get("image_content_type")
        if content_type not in ALLOWED_TYPES:
            raise InputValidationError("Only JPEG and PNG images are accepted")
        encoded = body.get("image_base64")
        if not isinstance(encoded, str) or not encoded:
            raise InputValidationError("image_base64 is required")
        # Bound encoded size before decoding to prevent excessive memory use.
        if len(encoded) > ((MAX_UPLOAD_BYTES + 2) // 3) * 4 + 8:
            return _response(413, {"error": "IMAGE_TOO_LARGE"})
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InputValidationError("image_base64 is invalid") from exc
        if not image_bytes or len(image_bytes) > MAX_UPLOAD_BYTES:
            return _response(413, {"error": "IMAGE_SIZE_INVALID"})
        extension, magic = ALLOWED_TYPES[content_type]
        if not image_bytes.startswith(magic):
            raise InputValidationError("Image content does not match its declared type")

        bucket = os.environ.get("LUANDA_PULSE_REPORTS_BUCKET", "").strip()
        place_index = os.environ.get("LUANDA_PULSE_PLACE_INDEX", "").strip()
        if not bucket or not place_index:
            logger.error("Required Lambda configuration is missing")
            return _response(500, {"error": "SERVICE_NOT_CONFIGURED"})

        region = os.environ.get("AWS_REGION", "us-east-1")
        s3 = boto3.client("s3", region_name=region)
        rekognition = boto3.client("rekognition", region_name=region)
        location = boto3.client("location", region_name=region)
        report_id = str(uuid.uuid4())
        image_key = f"photos/{report_id}.{extension}"

        # The bucket is private; object access is only through this Lambda role.
        s3.put_object(
            Bucket=bucket,
            Key=image_key,
            Body=image_bytes,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            Metadata={"report-id": report_id},
        )
        detected = rekognition.detect_labels(
            Image={"Bytes": image_bytes}, MaxLabels=50, MinConfidence=70.0
        )
        detected_type, confidence, severity = classify_labels(detected.get("Labels", []))
        geo = location.search_place_index_for_text(
            IndexName=place_index, Text=address, MaxResults=1
        )
        results = geo.get("Results", [])
        if not results:
            # Retain the photo only as an internal object; do not return a successful report.
            s3.delete_object(Bucket=bucket, Key=image_key)
            return _response(422, {"error": "ADDRESS_NOT_FOUND"})
        place = results[0].get("Place", {})
        point = place.get("Geometry", {}).get("Point")
        coordinates = point if isinstance(point, list) and len(point) == 2 else None
        analysis = ReportAnalysis(
            issue_type=detected_type,
            classification_confidence=confidence,
            severity_label=severity,
            description_for_report=(
                f"Citizen selected {issue_type}. Automated image signal: {detected_type}. "
                "Human review required."
            ),
            formatted_address=place.get("Label"),
            coordinates=coordinates,
            location_source="USER_PROVIDED_ADDRESS",
            location_verified=False,
            status="PENDING_REVIEW",
        )
        report = {
            "report_id": report_id,
            "created_at": datetime.now(UTC).isoformat(),
            "citizen_selected_issue_type": issue_type,
            "citizen_description": description.strip(),
            "image_key": image_key,
            **analysis.to_dict(),
        }
        s3.put_object(
            Bucket=bucket,
            Key=f"reports/{report_id}.json",
            Body=json.dumps(report, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        return _response(201, {
            "report_id": report_id,
            "status": "PENDING_REVIEW",
            "issue_type": detected_type,
            "classification_confidence": confidence,
            "severity_label": severity,
            "formatted_address": place.get("Label"),
            "location_verified": False,
            "message": "Report stored and awaiting human review.",
        })
    except (json.JSONDecodeError, InputValidationError) as exc:
        return _response(400, {"error": "INVALID_INPUT", "message": str(exc)})
    except (ClientError, BotoCoreError):
        logger.exception("AWS service call failed")
        return _response(502, {"error": "UPSTREAM_SERVICE_ERROR"})
    except Exception:
        logger.exception("Unexpected report submission failure")
        return _response(500, {"error": "INTERNAL_ERROR"})
