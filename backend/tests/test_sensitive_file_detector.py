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
