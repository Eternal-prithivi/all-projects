from app.security.security_scan_ml import train_security_scan_classifier
from app.security.sensitive_file_detector import scan_file_content_hybrid


def test_train_security_scan_classifier_meets_gate():
    _, accuracy = train_security_scan_classifier(min_accuracy=0.85)
    assert accuracy >= 0.85


def test_hybrid_scan_rules_still_win():
    content = b"password: MyStr0ng!Pass"
    result = scan_file_content_hybrid(content, "notes.txt", ml_enabled=False)
    assert result.is_sensitive is True
    assert "credential_keywords" in result.reasons


def test_hybrid_scan_with_ml():
    content = b"api_key=sk-live-abc123notreal"
    result = scan_file_content_hybrid(content, "config.txt", ml_enabled=True)
    assert result.is_sensitive is True
