import pytest

from luanda_pulse.analyzer import (
    InputValidationError, classify_labels, parse_s3_uri, validate_address_text,
)


def test_parse_s3_uri():
    assert parse_s3_uri("s3://reports/photos/test.jpg") == ("reports", "photos/test.jpg")


@pytest.mark.parametrize("value", [
    "", "reports/key.jpg", "s3://bucket", "s3:///key.jpg", "s3://bucket/a/../b.jpg",
])
def test_parse_s3_uri_rejects_invalid_paths(value):
    with pytest.raises(InputValidationError):
        parse_s3_uri(value)


def test_parse_s3_uri_rejects_query():
    with pytest.raises(InputValidationError):
        parse_s3_uri("s3://bucket/key.jpg?download=1")


def test_address_is_normalized():
    assert validate_address_text("  Rua   da Samba, Luanda  ") == "Rua da Samba, Luanda"


@pytest.mark.parametrize("value", ["", "  ", "x" * 501, None])
def test_address_rejects_invalid_values(value):
    with pytest.raises(InputValidationError):
        validate_address_text(value)


def test_generic_labels_do_not_guess_issue_type():
    issue, confidence, severity = classify_labels([
        {"Name": "Road", "Confidence": 99.0}, {"Name": "Vehicle", "Confidence": 98.0}
    ])
    assert (issue, confidence, severity) == ("UNKNOWN", None, "UNASSESSED")


def test_exact_issue_label_does_not_infer_severity():
    issue, confidence, severity = classify_labels([{"Name": "Pothole", "Confidence": 92.0}])
    assert (issue, confidence, severity) == ("POTHOLE", 0.92, "UNASSESSED")
