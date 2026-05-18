import pytest

from app.utils.url_safety import validate_public_http_url


def test_rejects_localhost():
    with pytest.raises(ValueError, match="not allowed"):
        validate_public_http_url("http://localhost/image.png")


def test_rejects_private_ip_literal():
    with pytest.raises(ValueError, match="not allowed"):
        validate_public_http_url("http://127.0.0.1/image.png")


def test_accepts_public_https_url():
    validate_public_http_url("https://example.com/image.jpg")
