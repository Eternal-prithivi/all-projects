# =============================================================================
# MODULE: provision/opa_engine.py
# PURPOSE: OPA CLI wrapper class — evaluates Rego policies against Terraform configs
# SOURCE: Adapted from aws-provision-using-terraform/opa-policies/opa_engine.py
# USED BY: policy_checker.py (evaluate_opa_policies)
# DO NOT:
#   - Remove graceful degradation when OPA is not installed
#   - Cache OPA availability across requests — it may be installed mid-session
# =============================================================================
"""
OPA Policy Engine Wrapper.

Runs OPA CLI to evaluate Rego policies against an infrastructure config dict.
Augments the YAML-based policy engine; does NOT replace it.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Cached once per process — avoids spawning `opa version` on every review request
_OPA_CLI_AVAILABLE: bool | None = None


def is_opa_cli_available() -> bool:
    """Return whether OPA CLI is installed (cached after first check)."""
    global _OPA_CLI_AVAILABLE
    if _OPA_CLI_AVAILABLE is not None:
        return _OPA_CLI_AVAILABLE
    try:
        result = subprocess.run(
            ["opa", "version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        _OPA_CLI_AVAILABLE = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _OPA_CLI_AVAILABLE = False
    return _OPA_CLI_AVAILABLE


@dataclass
class OPAResult:
    """Holds OPA policy evaluation output."""

    blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    opa_available: bool = True
    error: str = ""

    def has_blocks(self) -> bool:
        """Return True if any block-level violations were found."""
        return len(self.blocks) > 0

    def has_warnings(self) -> bool:
        """Return True if any warnings were found."""
        return len(self.warnings) > 0

    def is_empty(self) -> bool:
        """Return True if OPA produced no output (clean result)."""
        return not self.blocks and not self.warnings


class OPAEngine:
    """Wraps the OPA CLI to evaluate Rego policies against a config dict."""

    def __init__(self, policies_dir: str | Path) -> None:
        """Initialise the OPA engine with a path to the Rego policies directory.

        Args:
            policies_dir: Path to directory containing .rego policy files.
        """
        self.policies_dir = Path(policies_dir).resolve()
        self.policy_file = self.policies_dir / "aws_security.rego"

    def is_opa_available(self) -> bool:
        """Check whether the OPA CLI binary is installed and reachable."""
        return is_opa_cli_available()

    def evaluate(self, config: dict[str, Any]) -> OPAResult:
        """Evaluate an infrastructure config dict against the Rego policy file.

        Args:
            config: Dictionary of infrastructure configuration values.

        Returns:
            OPAResult with blocks and warnings extracted from OPA output.
        """
        if not self.is_opa_available():
            return OPAResult(
                opa_available=False,
                error="OPA CLI is not installed. Install from: https://www.openpolicyagent.org/docs/latest/#1-download-opa",
            )

        if not self.policy_file.exists():
            return OPAResult(
                opa_available=True,
                error=f"Policy file not found: {self.policy_file}",
            )

        result = OPAResult()

        # Evaluate deny rules (blocks)
        blocks = self._run_opa_query("data.aws.security.deny", config)
        result.blocks = blocks

        # Evaluate warn rules (warnings)
        warnings = self._run_opa_query("data.aws.security.warn", config)
        result.warnings = warnings

        return result

    def _run_opa_query(
        self,
        query: str,
        config: dict[str, Any],
    ) -> list[str]:
        """Run a single OPA query and return the string results.

        Args:
            query: Rego query string (e.g. ``data.aws.security.deny``).
            config: Input data to pass to OPA as JSON.

        Returns:
            List of result strings from OPA, or empty list on failure.
        """
        try:
            proc = subprocess.run(
                [
                    "opa", "eval",
                    "--format", "json",
                    "--data", str(self.policy_file),
                    "--input", "/dev/stdin",
                    query,
                ],
                input=json.dumps(config),
                capture_output=True,
                text=True,
                timeout=8,
            )

            if proc.returncode != 0:
                logger.warning(f"OPA eval returned exit code {proc.returncode}: {proc.stderr[:200]}")
                return []

            data = json.loads(proc.stdout)
            # OPA eval returns: {"result": [{"expressions": [{"value": [...]}]}]}
            results = data.get("result", [])
            if not results:
                return []

            expressions = results[0].get("expressions", [])
            if not expressions:
                return []

            value = expressions[0].get("value", [])
            if isinstance(value, list):
                return [str(v) for v in value]
            return []

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"OPA query failed for '{query}': {e}")
            return []

    def report(self, result: OPAResult) -> str:
        """Format an OPA evaluation report as a string.

        Args:
            result: OPAResult from evaluate().

        Returns:
            Formatted report string.
        """
        lines: list[str] = []

        if not result.opa_available:
            lines.append(f"⚠️  OPA not available: {result.error}")
            return "\n".join(lines)

        if result.error:
            lines.append(f"⚠️  OPA error: {result.error}")
            return "\n".join(lines)

        if result.is_empty():
            lines.append("✅  OPA: No additional violations found.")
            return "\n".join(lines)

        if result.blocks:
            for msg in result.blocks:
                lines.append(f"🚫  {msg}")

        if result.warnings:
            for msg in result.warnings:
                lines.append(f"⚠️  {msg}")

        return "\n".join(lines)
