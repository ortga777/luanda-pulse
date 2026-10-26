"""AWS Lambda entry point for urban-issue photo analysis."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from luanda_pulse.analyzer import (
    MAX_IMAGE_BYTES,
    InputValidationError,
    ReportAnalysis,
    classify_labels,
    parse_s3_uri,
    validate_address_text,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Analyze an S3 image and geocode the user-provided address."""
    try:
        if not isinstance(event, dict):
            raise InputValidationError("Request body must be a JSON object")
        bucket, key = parse_s3_uri(event.get("s3_path"))
        address = validate_address_text(event.get("address_text"))

        configured_bucket = os.environ.get("LUANDA_PULSE_REPORTS_BUCKET", "").strip()
        place_index = os.environ.get("LUANDA_PULSE_PLACE_INDEX", "").strip()
        if not configured_bucket or not place_index:
            logger.error("Required Lambda configuration is missing")
            return _response(500, {"error": "SERVICE_NOT_CONFIGURED"})
        if bucket != configured_bucket:
            return _response(400, {"error": "S3_BUCKET_NOT_ALLOWED"})

        region = os.environ.get("AWS_REGION", "us-east-1")
        s3 = boto3.client("s3", region_name=region)
        rekognition = boto3.client("rekognition", region_name=region)
        location = boto3.client("location", region_name=region)

        obj = s3.get_object(Bucket=bucket, Key=key)
        content_type = obj.get("ContentType", "")
        body = obj["Body"]
        image_bytes = body.read(MAX_IMAGE_BYTES + 1)
        body.close()
        if content_type not in {"image/jpeg", "image/png"}:
            return _response(415, {"error": "UNSUPPORTED_IMAGE_TYPE"})
        if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
            return _response(413, {"error": "IMAGE_SIZE_INVALID"})

        detected = rekognition.detect_labels(
            Image={"Bytes": image_bytes}, MaxLabels=50, MinConfidence=70.0
        )
        issue_type, confidence, severity = classify_labels(detected.get("Labels", []))
        geo = location.search_place_index_for_text(
            IndexName=place_index, Text=address, MaxResults=1
        )
        results = geo.get("Results", [])
        if not results:
            return _response(422, {"error": "ADDRESS_NOT_FOUND"})

        place = results[0].get("Place", {})
        point = place.get("Geometry", {}).get("Point")
        coordinates = point if isinstance(point, list) and len(point) == 2 else None
        result = ReportAnalysis(
            issue_type=issue_type,
            classification_confidence=confidence,
            severity_label=severity,
            description_for_report=(
                f"Potential urban issue classified as {issue_type}."
                if issue_type != "UNKNOWN"
                else "Issue could not be classified reliably; review required."
            ),
            formatted_address=place.get("Label"),
            coordinates=coordinates,
            location_source="USER_PROVIDED_ADDRESS",
            location_verified=False,
            status="PENDING_REVIEW",
        )
        return _response(200, result.to_dict())
    except InputValidationError as exc:
        return _response(400, {"error": "INVALID_INPUT", "message": str(exc)})
    except (ClientError, BotoCoreError):
        logger.exception("AWS service call failed")
        return _response(502, {"error": "UPSTREAM_SERVICE_ERROR"})
    except Exception:
        logger.exception("Unexpected analysis failure")
        return _response(500, {"error": "INTERNAL_ERROR"})
