from app.security.sensitive_file_detector import scan_file_content


def test_detects_credential_keywords():
    result = scan_file_content(b"api_key=abc123secret")
    assert result.is_sensitive
    assert "credential_keywords" in result.reasons


def test_detects_private_ip():
    result = scan_file_content(b"connect to 192.168.1.50 locally")
    assert result.is_sensitive
    assert "private_ip_address" in result.reasons


def test_clean_file():
    result = scan_file_content(b"hello world summary report")
    assert not result.is_sensitive
