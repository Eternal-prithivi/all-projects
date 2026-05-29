#!/usr/bin/env python3
"""Benchmark sensitive_file_detector against labeled fixtures (viva / report metrics)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.security.sensitive_file_detector import scan_file_content  # noqa: E402

DATASET = Path(__file__).resolve().parents[1] / "app/security/datasets/sensitive_scan_labeled.json"


def main() -> int:
    rows = json.loads(DATASET.read_text(encoding="utf-8"))
    tp = fp = tn = fn = 0

    for row in rows:
        result = scan_file_content(row["text"].encode("utf-8"), f"{row['id']}.txt")
        predicted = result.is_sensitive
        expected = row["expect_sensitive"]
        if expected and predicted:
            tp += 1
        elif expected and not predicted:
            fn += 1
        elif not expected and predicted:
            fp += 1
        else:
            tn += 1

    total = len(rows)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    print("Sensitive file detector benchmark")
    print(f"  Dataset: {DATASET.name} ({total} samples)")
    print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"  Accuracy:  {accuracy:.1%}")
    print(f"  Precision: {precision:.1%}")
    print(f"  Recall:    {recall:.1%}")
    print(f"  F1:        {f1:.1%}")
    return 0 if accuracy >= 0.85 and recall >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
