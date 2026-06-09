"""Lightweight ML-assisted sensitive content scoring (TF-IDF + logistic regression)."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ML_THRESHOLD = 0.65
_ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "ml_artifacts" / "security_scan_classifier.joblib"
_LABELED_PATH = Path(__file__).resolve().parent / "datasets" / "sensitive_scan_labeled.json"

_pipeline: Optional[Pipeline] = None


def _load_labeled_rows() -> List[Dict[str, Any]]:
    with open(_LABELED_PATH, encoding="utf-8") as f:
        return json.load(f)


def generate_security_scan_rows(seed: int = 42) -> List[Dict[str, Any]]:
    """Augment labeled set with synthetic variants for training stability."""
    random.seed(seed)
    base = _load_labeled_rows()
    rows = list(base)
    templates_sensitive = [
        ("api_key={key}", ("key",)),
        ("password: {pwd}", ("pwd",)),
        ("export AWS_ACCESS_KEY_ID={key}", ("key",)),
        ("Contact {email} from {ip}", ("email", "ip")),
        ('{"type": "service_account", "project_id": "p"}', ()),
    ]
    templates_clean = [
        "Quarterly report for team {n}",
        "Deploy to production region {n}",
        "Invoice #{n} paid",
        "Meeting notes week {n}",
    ]
    for i in range(200):
        if i % 2 == 0:
            t, fields = random.choice(templates_sensitive)
            values = {
                "key": f"AKIA{random.randbytes(8).hex().upper()[:16]}",
                "pwd": f"Pass{random.randint(1000,9999)}!",
                "email": f"user{i}@example.com",
                "ip": f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
            }
            text = t.format(**{k: values[k] for k in fields}) if fields else t
            rows.append({"id": f"syn_s_{i}", "text": text, "expect_sensitive": True, "tags": ["synthetic"]})
        else:
            t = random.choice(templates_clean)
            rows.append(
                {
                    "id": f"syn_c_{i}",
                    "text": t.format(n=random.randint(1, 9999)),
                    "expect_sensitive": False,
                    "tags": ["synthetic"],
                }
            )
    return rows


def train_security_scan_classifier(
    *,
    min_accuracy: float = 0.90,
    save_path: Optional[Path] = None,
) -> Tuple[Pipeline, float]:
    rows = generate_security_scan_rows()
    texts = [r["text"] for r in rows]
    labels = [1 if r["expect_sensitive"] else 0 for r in rows]
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=4000, ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=500, class_weight="balanced")),
        ]
    )
    pipeline.fit(X_train, y_train)
    accuracy = float(pipeline.score(X_test, y_test))
    if accuracy < min_accuracy:
        raise RuntimeError(f"Security scan ML accuracy {accuracy:.3f} below gate {min_accuracy}")
    out = save_path or _ARTIFACT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, out)
    return pipeline, accuracy


def _get_pipeline() -> Optional[Pipeline]:
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    if _ARTIFACT_PATH.exists():
        try:
            _pipeline = joblib.load(_ARTIFACT_PATH)
            return _pipeline
        except Exception:
            return None
    try:
        _pipeline, _ = train_security_scan_classifier()
        return _pipeline
    except Exception:
        return None


def predict_security_risk(content: str, filename: Optional[str] = None) -> Tuple[float, List[str]]:
    """Return (probability 0-1, hint strings)."""
    pipeline = _get_pipeline()
    if pipeline is None:
        return 0.0, []
    sample = content
    if filename:
        sample = f"{filename}\n{content}"
    sample = sample[:50000]
    try:
        proba = pipeline.predict_proba([sample])[0][1]
    except Exception:
        return 0.0, []
    hints: List[str] = []
    if proba >= ML_THRESHOLD:
        hints.append("ml_elevated_risk")
    return float(proba), hints


def scan_text_features(content_str: str) -> Dict[str, Any]:
    """Expose ML score for API responses."""
    score, hints = predict_security_risk(content_str)
    return {"ml_scan_score": round(score, 4), "ml_scan_signals": hints}
