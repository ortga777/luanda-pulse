"""Input validation and conservative classification helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_ISSUE_TYPES = {
    "POTHOLE", "TRASH_ACCUMULATION", "BROKEN_STREETLIGHT", "FLOODING", "UNKNOWN"
}


class InputValidationError(ValueError):
    """Raised when a report input fails validation."""


@dataclass(frozen=True)
class ReportAnalysis:
    issue_type: str
    classification_confidence: float | None
    severity_label: str
    description_for_report: str
    formatted_address: str | None
    coordinates: list[float] | None
    location_source: str
    location_verified: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """Parse a strict s3://bucket/key URI."""
    if not isinstance(s3_uri, str) or not s3_uri.startswith("s3://"):
        raise InputValidationError("s3_path must be an s3://bucket/key URI")
    parsed = urlparse(s3_uri)
    bucket, key = parsed.netloc, parsed.path.lstrip("/")
    if not bucket or not key or ".." in key.split("/"):
        raise InputValidationError("s3_path must include a valid bucket and object key")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise InputValidationError("s3_path must not contain credentials, query, or fragment")
    return bucket, key


def validate_address_text(address_text: str) -> str:
    """Normalize and validate the user-provided address."""
    if not isinstance(address_text, str):
        raise InputValidationError("address_text must be a string")
    normalized = " ".join(address_text.split())
    if not normalized:
        raise InputValidationError("address_text is required")
    if len(normalized) > 500:
        raise InputValidationError("address_text must be 500 characters or fewer")
    return normalized


def classify_labels(labels: list[dict[str, Any]]) -> tuple[str, float | None, str]:
    """Accept only exact issue labels; generic labels do not prove an issue.

    Confidence is not severity. A domain-specific classifier must be evaluated
    before predictions are used as operational classifications.
    """
    scores: dict[str, float] = {}
    for label in labels:
        name, confidence = label.get("Name"), label.get("Confidence")
        if not isinstance(name, str) or not isinstance(confidence, (int, float)):
            continue
        normalized = name.strip().upper().replace(" ", "_")
        if normalized in SUPPORTED_ISSUE_TYPES - {"UNKNOWN"}:
            scores[normalized] = max(scores.get(normalized, 0.0), float(confidence) / 100)
    if not scores:
        return "UNKNOWN", None, "UNASSESSED"
    issue_type, confidence = max(scores.items(), key=lambda item: item[1])
    return issue_type, round(min(max(confidence, 0.0), 1.0), 4), "UNASSESSED"
