"""Tests for webhook HMAC signing and verification."""

import time
from core.webhook_signing import (
    sign_webhook_payload,
    verify_webhook_signature,
    generate_webhook_secret,
)


class TestSignWebhookPayload:
    """Test outbound webhook signing."""

    def test_returns_required_headers(self):
        headers = sign_webhook_payload(b'{"event": "test"}', "secret123")
        assert "X-RPA-Signature" in headers
        assert "X-RPA-Timestamp" in headers
        assert "X-RPA-Delivery" in headers
        assert "Content-Type" in headers

    def test_signature_format(self):
        headers = sign_webhook_payload(b"test", "secret")
        assert headers["X-RPA-Signature"].startswith("sha256=")
        # SHA-256 hex digest is 64 chars
        sig = headers["X-RPA-Signature"][7:]
        assert len(sig) == 64

    def test_custom_timestamp(self):
        headers = sign_webhook_payload(b"test", "secret", timestamp=1234567890)
        assert headers["X-RPA-Timestamp"] == "1234567890"

    def test_custom_delivery_id(self):
        headers = sign_webhook_payload(b"test", "secret", delivery_id="my-id")
        assert headers["X-RPA-Delivery"] == "my-id"

    def test_different_payloads_different_signatures(self):
        h1 = sign_webhook_payload(b"payload1", "secret", timestamp=1000)
        h2 = sign_webhook_payload(b"payload2", "secret", timestamp=1000)
        assert h1["X-RPA-Signature"] != h2["X-RPA-Signature"]

    def test_different_secrets_different_signatures(self):
        h1 = sign_webhook_payload(b"payload", "secret1", timestamp=1000)
        h2 = sign_webhook_payload(b"payload", "secret2", timestamp=1000)
        assert h1["X-RPA-Signature"] != h2["X-RPA-Signature"]


class TestVerifyWebhookSignature:
    """Test inbound webhook verification."""

    def test_valid_signature(self):
        payload = b'{"event": "workflow.completed"}'
        secret = "test-secret"
        ts = int(time.time())
        headers = sign_webhook_payload(payload, secret, timestamp=ts)

        assert verify_webhook_signature(
            payload, secret,
            headers["X-RPA-Signature"],
            headers["X-RPA-Timestamp"],
        ) is True

    def test_wrong_secret(self):
        payload = b"test"
        headers = sign_webhook_payload(payload, "correct-secret")

        assert verify_webhook_signature(
            payload, "wrong-secret",
            headers["X-RPA-Signature"],
            headers["X-RPA-Timestamp"],
        ) is False

    def test_tampered_payload(self):
        headers = sign_webhook_payload(b"original", "secret")

        assert verify_webhook_signature(
            b"tampered", "secret",
            headers["X-RPA-Signature"],
            headers["X-RPA-Timestamp"],
        ) is False

    def test_expired_timestamp(self):
        old_ts = int(time.time()) - 600  # 10 minutes ago
        headers = sign_webhook_payload(b"test", "secret", timestamp=old_ts)

        assert verify_webhook_signature(
            b"test", "secret",
            headers["X-RPA-Signature"],
            headers["X-RPA-Timestamp"],
            tolerance=300,  # 5 min tolerance
        ) is False

    def test_future_timestamp_within_tolerance(self):
        future_ts = int(time.time()) + 60  # 1 minute in future
        headers = sign_webhook_payload(b"test", "secret", timestamp=future_ts)

        assert verify_webhook_signature(
            b"test", "secret",
            headers["X-RPA-Signature"],
            headers["X-RPA-Timestamp"],
            tolerance=300,
        ) is True

    def test_invalid_signature_format(self):
        assert verify_webhook_signature(
            b"test", "secret",
            "invalid-format",
            str(int(time.time())),
        ) is False

    def test_invalid_timestamp(self):
        headers = sign_webhook_payload(b"test", "secret")
        assert verify_webhook_signature(
            b"test", "secret",
            headers["X-RPA-Signature"],
            "not-a-number",
        ) is False


class TestGenerateWebhookSecret:
    """Test webhook secret generation."""

    def test_prefix(self):
        secret = generate_webhook_secret()
        assert secret.startswith("whsec_")

    def test_sufficient_length(self):
        secret = generate_webhook_secret()
        assert len(secret) > 40

    def test_uniqueness(self):
        secrets = {generate_webhook_secret() for _ in range(100)}
        assert len(secrets) == 100
