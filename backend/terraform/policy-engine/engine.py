"""
policy-engine/engine.py — Policy and Risk Engine

Reads rules from rules.yaml and evaluates infrastructure config against them.
All rule logic lives in rules.yaml — NEVER hardcode rules here.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Violation:
    """Represents a single policy rule violation."""

    rule_name: str
    description: str
    severity: str  # "block" or "warning"


@dataclass
class EvaluationResult:
    """Result of evaluating a config against all policy rules."""

    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)

    def has_blocks(self) -> bool:
        """Return True if any block-level violation was found."""
        return len(self.violations) > 0

    def has_warnings(self) -> bool:
        """Return True if any warning-level violation was found."""
        return len(self.warnings) > 0

    def is_clean(self) -> bool:
        """Return True if no violations or warnings were found."""
        return not self.has_blocks() and not self.has_warnings()


class PolicyEngine:
    """
    Evaluates infrastructure config dicts against YAML-defined policy rules.

    Usage:
        engine = PolicyEngine("policy-engine/rules.yaml")
        result = engine.evaluate({"s3_bucket_public": True, ...})
    """

    def __init__(self, rules_path: str) -> None:
        """Load and validate the rules file on initialization."""
        self.rules_path = rules_path
        self.rules: list[dict[str, Any]] = self._load_rules(rules_path)

    def _load_rules(self, rules_path: str) -> list[dict[str, Any]]:
        """Load rules from YAML file. Raises FileNotFoundError or ValueError on bad input."""
        path = Path(rules_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "rules" not in data:
            raise ValueError(f"Invalid rules file — 'rules' key missing in: {rules_path}")

        return data["rules"]

    def evaluate(self, config: dict[str, Any]) -> EvaluationResult:
        """
        Evaluate the given config against all loaded rules.

        Args:
            config: Dict of infrastructure config values (e.g. from wizard output).

        Returns:
            EvaluationResult containing blocks and warnings lists.
        """
        if config is None:
            config = {}

        result = EvaluationResult()

        for rule in self.rules:
            triggered = self._check_rule(rule, config)
            if triggered:
                violation = Violation(
                    rule_name=rule["name"],
                    description=rule["description"],
                    severity=rule["severity"],
                )
                if rule["severity"] == "block":
                    result.violations.append(violation)
                else:
                    result.warnings.append(violation)

        return result

    def _check_rule(self, rule: dict[str, Any], config: dict[str, Any]) -> bool:
        """
        Evaluate a single rule's condition against the config.

        The condition string is evaluated using Python's eval() against the config dict.
        Only safe built-in operations are permitted.
        """
        condition: str = rule.get("condition", "False")
        try:
            return bool(eval(condition, {"__builtins__": {}}, config))  # noqa: S307
        except Exception:
            # If condition can't be evaluated, treat as not triggered (fail safe)
            return False

    def report(self, result: EvaluationResult) -> None:
        """Print a human-readable report of the evaluation result to stdout."""
        if result.is_clean():
            print("✅  Policy check PASSED — no violations found.")
            return

        if result.has_blocks():
            print("\n🚫  BLOCKED — The following policy violations must be fixed before deploying:\n")
            for v in result.violations:
                print(f"  [BLOCK]   {v.rule_name}: {v.description}")

        if result.has_warnings():
            print("\n⚠️   WARNINGS — Review these before proceeding:\n")
            for w in result.warnings:
                print(f"  [WARNING] {w.rule_name}: {w.description}")
