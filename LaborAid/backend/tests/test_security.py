"""Tests for app.core.security – rate limiting, password hashing, filename
sanitization, file validation, text sanitization, JWT tokens, and injection
scanning.
"""

import threading
import time
from datetime import timedelta, timezone, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core import security
from app.core.security import (
    _cleanup_rate_limit_store,
    _rate_limit_store,
    _scan_content_for_injections,
    check_rate_limit,
    create_access_token,
    hash_password,
    is_token_expired,
    sanitize_filename,
    sanitize_text,
    validate_file_extension,
    validate_mime_type,
    validate_password_strength,
    verify_password,
)


# ---------------------------------------------------------------------------
# 1. Rate limiting – check_rate_limit
# ---------------------------------------------------------------------------

class TestRateLimit:
    """Tests for the in-memory sliding-window rate limiter."""

    def setup_method(self):
        """Reset the global rate-limit store before each test."""
        with security._rate_limit_lock:
            _rate_limit_store.clear()

    def test_under_limit_returns_true(self):
        """Requests within the limit should return True."""
        for _ in range(5):
            assert check_rate_limit("user:a", max_requests=5, window_seconds=60) is True

    def test_at_limit_returns_false(self):
        """Once the limit is reached, the next request returns False."""
        for _ in range(3):
            check_rate_limit("user:b", max_requests=3, window_seconds=60)
        assert check_rate_limit("user:b", max_requests=3, window_seconds=60) is False

    def test_different_keys_independent(self):
        """Different keys should have independent counters."""
        for _ in range(3):
            check_rate_limit("key:x", max_requests=3, window_seconds=60)
        assert check_rate_limit("key:x", max_requests=3, window_seconds=60) is False
        assert check_rate_limit("key:y", max_requests=3, window_seconds=60) is True

    def test_window_expiry_allows_new_requests(self):
        """After the window expires, new requests should be allowed."""
        now = time.monotonic()
        with security._rate_limit_lock:
            _rate_limit_store["user:expire"] = [now - 61]
        assert check_rate_limit("user:expire", max_requests=1, window_seconds=60) is True


# ---------------------------------------------------------------------------
# 2. Rate limit cleanup – _cleanup_rate_limit_store
# ---------------------------------------------------------------------------

class TestRateLimitCleanup:
    """Tests for the stale-key cleanup routine."""

    def setup_method(self):
        with security._rate_limit_lock:
            _rate_limit_store.clear()

    def test_removes_stale_keys(self):
        """Keys with only old timestamps should be removed after cleanup."""
        now = time.monotonic()
        # Simulate a stale key (timestamps older than 3600s)
        _rate_limit_store["stale"] = [now - 4000]
        # Fresh key should remain
        _rate_limit_store["fresh"] = [now]

        # Force cleanup by resetting the last-cleanup timestamp
        security._rate_limit_last_cleanup = 0
        _cleanup_rate_limit_store()

        assert "stale" not in _rate_limit_store
        assert "fresh" in _rate_limit_store

    def test_skips_cleanup_within_interval(self):
        """Cleanup should be a no-op if called within the cooldown interval."""
        now = time.monotonic()
        _rate_limit_store["stale2"] = [now - 4000]
        # Set last cleanup to now so the interval guard kicks in
        security._rate_limit_last_cleanup = now

        _cleanup_rate_limit_store()
        # Stale key should still exist because cleanup was suppressed
        assert "stale2" in _rate_limit_store


# ---------------------------------------------------------------------------
# 3. Password hashing – hash_password / verify_password
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    """Tests for bcrypt password hashing and verification."""

    def test_verify_correct_password(self):
        hashed = hash_password("S3cureP@ss!")
        assert verify_password("S3cureP@ss!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correcthorse")
        assert verify_password("wronghorse", hashed) is False

    def test_hashes_are_unique(self):
        """Two hashes of the same password should differ (different salts)."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


# ---------------------------------------------------------------------------
# 4. Password strength validation
# ---------------------------------------------------------------------------

class TestPasswordStrength:
    """Tests for validate_password_strength."""

    def test_valid_password(self):
        ok, msg = validate_password_strength("Password1")
        assert ok is True
        assert msg == ""

    def test_too_short(self):
        ok, msg = validate_password_strength("Ab1")
        assert ok is False
        assert "8" in msg

    def test_no_letter(self):
        ok, msg = validate_password_strength("12345678")
        assert ok is False
        assert "字母" in msg

    def test_no_digit(self):
        ok, msg = validate_password_strength("abcdefgh")
        assert ok is False
        assert "数字" in msg


# ---------------------------------------------------------------------------
# 5. Filename sanitization
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    """Tests for sanitize_filename against path traversal and special chars."""

    def test_simple_name(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_path_traversal_removed(self):
        result = sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_backslash_traversal_removed(self):
        result = sanitize_filename("..\\..\\windows\\system32\\config")
        assert "\\" not in result
        assert ".." not in result

    def test_special_chars_replaced(self):
        result = sanitize_filename('file<>:"/\\|?*name.txt')
        # Unsafe chars should be replaced with underscores
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_long_name_truncated(self):
        long_name = "a" * 200 + ".pdf"
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50
        assert result.endswith(".pdf")

    def test_empty_name_returns_default(self):
        assert sanitize_filename("") == "upload"
        assert sanitize_filename("   ") == "upload"

    def test_preserves_unicode(self):
        result = sanitize_filename("合同文件.pdf")
        assert "合同文件" in result


# ---------------------------------------------------------------------------
# 6. File extension validation
# ---------------------------------------------------------------------------

class TestFileExtension:
    """Tests for validate_file_extension."""

    def test_allowed_extension(self):
        ext = validate_file_extension("document.pdf")
        assert ext == ".pdf"

    def test_allowed_extension_case_insensitive(self):
        ext = validate_file_extension("photo.JPG")
        assert ext == ".jpg"

    def test_disallowed_extension_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_extension("malware.exe")
        assert exc_info.value.status_code == 400

    def test_no_extension_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_file_extension("Makefile")
        assert exc_info.value.status_code == 400

    def test_custom_allowed_set(self):
        ext = validate_file_extension("data.csv", allowed_extensions={".csv"})
        assert ext == ".csv"

    def test_custom_set_rejects_others(self):
        with pytest.raises(HTTPException):
            validate_file_extension("doc.pdf", allowed_extensions={".csv"})


# ---------------------------------------------------------------------------
# 7. MIME type validation
# ---------------------------------------------------------------------------

class TestMIMEType:
    """Tests for validate_mime_type."""

    def test_matching_mime_passes(self):
        # Should not raise
        validate_mime_type("doc.pdf", "application/pdf")

    def test_mismatched_mime_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_mime_type("doc.pdf", "text/html")
        assert exc_info.value.status_code == 400

    def test_none_content_type_passes(self):
        # None content_type should be accepted without error
        validate_mime_type("doc.pdf", None)

    def test_mime_with_charset_param(self):
        # Should normalize and match despite charset parameter
        validate_mime_type("readme.txt", "text/plain; charset=utf-8")

    def test_unknown_extension_passes(self):
        # Extensions not in the MIME map should pass through
        validate_mime_type("archive.zip", "application/zip")


# ---------------------------------------------------------------------------
# 8. Text sanitization
# ---------------------------------------------------------------------------

class TestSanitizeText:
    """Tests for sanitize_text."""

    def test_none_returns_empty(self):
        assert sanitize_text(None) == ""

    def test_empty_string_returns_empty(self):
        assert sanitize_text("") == ""

    def test_strips_whitespace(self):
        assert sanitize_text("  hello world  ") == "hello world"

    def test_truncates_long_text(self):
        long_text = "x" * 100_000
        result = sanitize_text(long_text, max_length=1000)
        assert len(result) == 1000

    def test_normal_text_unchanged(self):
        assert sanitize_text("Hello, world!") == "Hello, world!"


# ---------------------------------------------------------------------------
# 9. JWT token creation and expiration
# ---------------------------------------------------------------------------

class TestJWT:
    """Tests for create_access_token and is_token_expired."""

    def test_create_and_decode(self):
        token = create_access_token({"sub": "42", "email": "a@b.com"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_not_expired(self):
        token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(minutes=15),
        )
        assert is_token_expired(token) is False

    def test_token_expired(self):
        # Create a token that expired 10 seconds ago
        token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(seconds=-10),
        )
        assert is_token_expired(token) is True

    def test_invalid_token_reported_expired(self):
        assert is_token_expired("not.a.valid.token") is True


# ---------------------------------------------------------------------------
# 10. Injection scanning – _scan_content_for_injections
# ---------------------------------------------------------------------------

class TestInjectionScanning:
    """Tests for _scan_content_for_injections."""

    def test_clean_file_passes(self):
        content = b"This is a perfectly fine text file."
        # Should not raise
        _scan_content_for_injections("notes.txt", content)

    def test_script_tag_detected(self):
        content = b'<script>alert("xss")</script>'
        with pytest.raises(HTTPException) as exc_info:
            _scan_content_for_injections("page.html", content)
        assert exc_info.value.status_code == 400

    def test_javascript_uri_detected(self):
        content = b'Click <a href="javascript:void(0)">here</a>'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("link.html", content)

    def test_event_handler_detected(self):
        content = b'<img src=x onerror="alert(1)">'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("evil.html", content)

    def test_iframe_detected(self):
        content = b"<iframe src=\"https://evil.com\"></iframe>"
        with pytest.raises(HTTPException):
            _scan_content_for_injections("embed.html", content)

    def test_binary_file_skipped(self):
        # Non-text extensions should be skipped without scanning
        malicious = b'<script>alert("xss")</script>'
        # Should NOT raise for a .pdf file
        _scan_content_for_injections("document.pdf", malicious)

    def test_onclick_detected(self):
        content = b'<div onclick="steal()">click me</div>'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("click.htm", content)

    def test_onmouseover_detected(self):
        content = b'<div onmouseover="bad()">hover</div>'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("hover.html", content)

    def test_svg_injection_detected(self):
        content = b'<svg onload="alert(1)">'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("icon.html", content)

    def test_json_file_with_safe_content(self):
        content = b'{"key": "value", "count": 42}'
        _scan_content_for_injections("data.json", content)

    def test_xml_file_with_script(self):
        content = b'<?xml version="1.0"?><root><script>bad()</script></root>'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("feed.xml", content)

    def test_csv_file_with_injection(self):
        content = b'name,email\nAlice,<script>xss</script>\n'
        with pytest.raises(HTTPException):
            _scan_content_for_injections("data.csv", content)
