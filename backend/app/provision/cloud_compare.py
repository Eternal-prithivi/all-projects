"""Tri-cloud cost + fit comparison for provision templates."""

from __future__ import annotations

from typing import Any, List, Optional

from app.cloud.availability import CloudFeature, available_providers
from app.cloud.providers import normalize_provider
from app.provision.cost_estimator import estimate_from_config
from app.provision.provision_defaults import skeleton_config_for_template


def compare_clouds_for_intent(
    username: str,
    *,
    template: str,
    size_profile: str = "micro",
    environment: str = "free-tier",
    fit_base: int = 70,
    reasons: Optional[List[str]] = None,
) -> List[dict[str, Any]]:
    """
    Build estimate + fit score per available CSP for the same logical template.
    """
    providers = available_providers(username, CloudFeature.PROVISION)
    if not providers:
        providers = ["AWS", "GCP", "Azure"]

    results: List[dict[str, Any]] = []
    base_reasons = list(reasons or [])

    for csp in providers:
        provider = normalize_provider(csp)
        cfg = skeleton_config_for_template(
            provider,
            template,
            size_profile=size_profile,
            environment=environment,
        )
        estimate = estimate_from_config(cfg)
        monthly = float(estimate.total_monthly_cost or "0")
        instance = _primary_instance(cfg, provider)
        fit = min(100, fit_base + (5 if monthly < 20 else 0))

        results.append({
            "csp": provider,
            "template": template,
            "monthly_cost": estimate.total_monthly_cost,
            "monthly_cost_numeric": monthly,
            "fit_score": fit,
            "recommended_instance": instance,
            "reasons": base_reasons + [f"Estimated for {provider} {template}"],
            "resources": estimate.resources,
        })

    results.sort(key=lambda r: (-r["fit_score"], r["monthly_cost_numeric"]))
    if results:
        results[0]["badge"] = "best_fit"
        cheapest = min(results, key=lambda r: r["monthly_cost_numeric"])
        if cheapest["csp"] != results[0]["csp"]:
            for r in results:
                if r["csp"] == cheapest["csp"]:
                    r["badge"] = "best_value"
                    break
        elif len(results) == 1:
            results[0]["badge"] = "best_value"

    return results


def _primary_instance(cfg: dict[str, Any], csp: str) -> str:
    if csp == "AWS" and cfg.get("enable_ec2"):
        return str(cfg.get("instance_type", "t2.micro"))
    if csp == "GCP" and cfg.get("enable_gce"):
        return str(cfg.get("machine_type", "e2-micro"))
    if csp == "Azure" and cfg.get("enable_azure_vm"):
        return str(cfg.get("vm_size", "Standard_B1s"))
    if cfg.get("enable_s3") or cfg.get("enable_gcs") or cfg.get("enable_azure_storage"):
        return "storage"
    if cfg.get("enable_dynamodb") or cfg.get("enable_firestore") or cfg.get("enable_cosmos"):
        return "database"
    return "stack"
