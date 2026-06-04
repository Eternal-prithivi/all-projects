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


def test_rejects_invalid_luhn_card():
    result = scan_file_content(b"Invalid test PAN 4111111111111112 should not count.")
    assert not result.is_sensitive


def test_detects_aws_access_key_id():
    result = scan_file_content(b"key_id=AKIAIOSFODNN7EXAMPLE")
    assert result.is_sensitive
    assert "aws_access_key_id" in result.reasons


def test_detects_ssn():
    result = scan_file_content(b"Employee SSN 078-05-1120 on file")
    assert result.is_sensitive
    assert "ssn_pattern" in result.reasons


def test_sensitive_filename_pem():
    result = scan_file_content(b"", filename="server.pem")
    assert result.is_sensitive
    assert "sensitive_filename" in result.reasons


def test_sensitive_filename_env():
    result = scan_file_content(b"PORT=3000", filename=".env")
    assert result.is_sensitive
    assert "sensitive_filename" in result.reasons


def test_detects_azure_storage_connection():
    conn = (
        b"DefaultEndpointsProtocol=https;AccountName=demo;AccountKey="
        b"dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXRlc3Q=;EndpointSuffix=core.windows.net"
    )
    result = scan_file_content(conn)
    assert result.is_sensitive
    assert "azure_storage_secret" in result.reasons


def test_detects_azure_client_secret():
    result = scan_file_content(b"AZURE_CLIENT_SECRET=ab12cd34ef56gh78ij90kl12mn34op56")
    assert result.is_sensitive
    assert "azure_client_secret" in result.reasons


def test_detects_gcp_service_account_json():
    result = scan_file_content(b'{"type": "service_account", "project_id": "x"}')
    assert result.is_sensitive
    assert "gcp_service_account" in result.reasons


def test_detects_gcp_api_key():
    # Google API keys are 39 chars: AIza + 35 alphanumeric
    api_key = b"key=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567"
    result = scan_file_content(api_key)
    assert result.is_sensitive
    assert "gcp_api_key" in result.reasons


def test_detects_pem_private_key():
    result = scan_file_content(b"-----BEGIN RSA PRIVATE KEY-----\nMIIfake\n-----END RSA PRIVATE KEY-----")
    assert result.is_sensitive
    assert "pem_private_key" in result.reasons


def test_clean_cloud_names_only():
    result = scan_file_content(b"Deploy to AWS, Azure, and GCP for redundancy.")
    assert not result.is_sensitive


def test_labeled_dataset_benchmark():
    """Regression: labeled JSON fixtures should meet minimum accuracy."""
    import json
    from pathlib import Path

    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "app/security/datasets/sensitive_scan_labeled.json"
    )
    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    correct = 0
    for row in rows:
        predicted = scan_file_content(row["text"].encode("utf-8")).is_sensitive
        if predicted == row["expect_sensitive"]:
            correct += 1
    accuracy = correct / len(rows)
    assert accuracy >= 0.85, f"Detector accuracy {accuracy:.1%} below 85% threshold"
