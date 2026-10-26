import json

from luanda_pulse.submit_handler import handler


def test_options_preflight_returns_cors_headers():
    result = handler({"requestContext": {"http": {"method": "OPTIONS"}}}, None)
    assert result["statusCode"] == 204
    assert result["headers"]["access-control-allow-methods"] == "POST,OPTIONS"


def test_missing_address_is_rejected_before_aws_calls():
    event = {"body": json.dumps({"image_content_type": "image/jpeg", "image_base64": "abc"})}
    result = handler(event, None)
    assert result["statusCode"] == 400
    assert json.loads(result["body"])["error"] == "INVALID_INPUT"


def test_unsupported_content_type_is_rejected():
    payload = {
        "address_text": "Maianga, Luanda",
        "image_content_type": "image/gif",
        "image_base64": "abc",
    }
    result = handler({"body": json.dumps(payload)}, None)
    assert result["statusCode"] == 400


def test_malformed_base64_is_rejected():
    payload = {
        "address_text": "Maianga, Luanda",
        "image_content_type": "image/jpeg",
        "image_base64": "not valid base64!",
    }
    result = handler({"body": json.dumps(payload)}, None)
    assert result["statusCode"] == 400
