"""Map NLP / keywords to per-cloud provision module flags (S3, EC2, VPC, …)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.provision.provision_catalog import modules_for_csp
from app.vm.models import ClusterType

# Keywords keyed by module catalog `key` (per CSP — only matching keys are scored).
AWS_KEYWORDS: dict[str, list[str]] = {
    "s3": [
        "s3", "bucket", "object storage", "file storage", "blob", "store files",
        "upload files", "static assets", "media files", "backup files", "archival",
    ],
    "dynamodb": [
        "dynamodb", "nosql", "key-value", "key value", "document store", "serverless db",
    ],
    "ec2": [
        "ec2", "server", "vm", "virtual machine", "compute", "instance", "host",
        "api", "backend", "application server", "web app", "microservice",
    ],
    "vpc": ["vpc", "private network", "subnet", "network isolation", "isolated network"],
    "cloudwatch": [
        "cloudwatch", "monitor", "monitoring", "alert", "alarm", "metrics",
        "logging", "observability", "cpu alert", "email alert",
    ],
    "billing": [
        "budget", "cost alert", "spending", "spend limit", "aws budgets", "bill alert",
        "cost cap", "monthly limit",
    ],
    "iam": ["iam", "role", "permissions", "access control", "service role", "least privilege"],
}

GCP_KEYWORDS: dict[str, list[str]] = {
    "gcs": ["gcs", "google cloud storage", "bucket", "object storage", "file storage", "blob"],
    "firestore": ["firestore", "nosql", "document database", "serverless db"],
    "gce": ["gce", "compute engine", "vm", "server", "instance", "api", "backend"],
    "gcp_network": ["vpc", "network", "subnet"],
    "gcp_monitoring": ["monitoring", "alert", "metrics", "cloud monitoring"],
    "gcp_service_account": ["service account", "iam", "permissions"],
}

AZURE_KEYWORDS: dict[str, list[str]] = {
    "azure_storage": ["blob", "storage account", "object storage", "file storage", "bucket"],
    "cosmos": ["cosmos", "nosql", "document db"],
    "azure_vm": ["vm", "virtual machine", "server", "compute", "linux vm", "api", "backend"],
    "vnet": ["vnet", "virtual network", "subnet"],
    "azure_monitor": ["monitor", "alert", "azure monitor", "email alert"],
}

_KEYWORDS_BY_CSP = {
    "AWS": AWS_KEYWORDS,
    "GCP": GCP_KEYWORDS,
    "Azure": AZURE_KEYWORDS,
}

_STORAGE_MODULE_KEYS = frozenset({"s3", "gcs", "azure_storage"})
_DB_MODULE_KEYS = frozenset({"dynamodb", "firestore", "cosmos"})
_COMPUTE_MODULE_KEYS = frozenset({"ec2", "gce", "azure_vm"})
_NETWORK_MODULE_KEYS = frozenset({"vpc", "gcp_network", "vnet"})


@dataclass
class ModuleRecommendation:
    suggested_modules: List[dict[str, Any]]
    module_flags: Dict[str, bool]
    module_reasons: Dict[str, str] = field(default_factory=dict)


def _keyword_map(csp: str) -> dict[str, list[str]]:
    from app.cloud.providers import normalize_provider

    return _KEYWORDS_BY_CSP.get(normalize_provider(csp), AWS_KEYWORDS)


def _score_modules(
    text: str,
    csp: str,
    *,
    cluster_type: Optional[ClusterType] = None,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Return module_key → score and module_key → reason lines."""
    lower = (text or "").lower()
    modules = modules_for_csp(csp)
    kw_map = _keyword_map(csp)
    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}

    for mod in modules:
        key = mod["key"]
        hits = [kw for kw in kw_map.get(key, []) if kw in lower]
        if hits:
            scores[key] = scores.get(key, 0) + len(hits) * 2
            reasons.setdefault(key, []).append(
                f"Keywords: {', '.join(hits[:4])}"
            )

    # NLP cluster boosts — storage → object storage module, not database
    for mod in modules:
        key = mod["key"]
        if cluster_type == ClusterType.STORAGE and key in _STORAGE_MODULE_KEYS:
            scores[key] = scores.get(key, 0) + 4
            reasons.setdefault(key, []).append("NLP: storage-oriented workload")
        elif cluster_type in (ClusterType.PERFORMANCE, ClusterType.AI_ML, ClusterType.MEMORY):
            if key in _COMPUTE_MODULE_KEYS:
                scores[key] = scores.get(key, 0) + 2
                reasons.setdefault(key, []).append(f"NLP: {cluster_type.value} compute workload")
        elif cluster_type == ClusterType.GENERAL and key in _COMPUTE_MODULE_KEYS:
            scores[key] = scores.get(key, 0) + 1

    # Explicit database keywords (not object storage)
    db_hits = [kw for kw in AWS_KEYWORDS["dynamodb"] if kw in lower]
    if db_hits and not any(k in scores for k in _STORAGE_MODULE_KEYS.intersection({m["key"] for m in modules})):
        for mod in modules:
            if mod["key"] in _DB_MODULE_KEYS:
                scores[mod["key"]] = scores.get(mod["key"], 0) + len(db_hits) * 2

    return scores, reasons


def _resolve_requires(selected: set[str], modules: list[dict]) -> set[str]:
    """Auto-enable dependency modules (e.g. EC2 → VPC)."""
    by_key = {m["key"]: m for m in modules}
    changed = True
    while changed:
        changed = False
        for key in list(selected):
            mod = by_key.get(key)
            if not mod:
                continue
            for req in mod.get("requires") or []:
                if req not in selected:
                    selected.add(req)
                    changed = True
    return selected


def _select_module_keys(scores: dict[str, int], modules: list[dict]) -> set[str]:
    if not scores:
        return set()

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    top_score = ranked[0][1]

    # Single clear intent (e.g. "S3 bucket only")
    if top_score >= 3 and (len(ranked) == 1 or ranked[1][1] <= 1):
        return {ranked[0][0]}

    selected = {k for k, s in scores.items() if s >= 2}
    if not selected and top_score >= 1:
        selected = {ranked[0][0]}
    return selected


def template_from_module_flags(csp: str, module_flags: dict[str, bool]) -> str:
    """Derive catalog template key from enabled module flags."""
    modules = modules_for_csp(csp)
    enabled_keys = {m["key"] for m in modules if module_flags.get(m["flag"])}

    has_storage = bool(enabled_keys & _STORAGE_MODULE_KEYS)
    has_db = bool(enabled_keys & _DB_MODULE_KEYS)
    has_compute = bool(enabled_keys & _COMPUTE_MODULE_KEYS)
    has_network = bool(enabled_keys & _NETWORK_MODULE_KEYS)

    if has_storage and not has_db and not has_compute:
        return "static-site"
    if has_db and not has_compute:
        return "serverless-db"
    if has_compute or has_network:
        return "backend-app"
    if enabled_keys:
        return "custom"
    return "backend-app"


def recommend_modules(
    workload_description: str,
    *,
    csp: str = "AWS",
    cluster_type: Optional[ClusterType] = None,
) -> ModuleRecommendation:
    """Score catalog modules and return flags + human-readable module list."""
    modules = modules_for_csp(csp)
    scores, reason_lists = _score_modules(
        workload_description, csp, cluster_type=cluster_type
    )
    selected = _resolve_requires(_select_module_keys(scores, modules), modules)

    module_flags: dict[str, bool] = {m["flag"]: m["key"] in selected for m in modules}
    module_reasons = {
        key: "; ".join(reason_lists.get(key, ["Suggested from your description"]))
        for key in selected
    }

    suggested_modules = [
        {
            "key": m["key"],
            "name": m["name"],
            "flag": m["flag"],
            "reason": module_reasons.get(m["key"], ""),
        }
        for m in modules
        if m["key"] in selected
    ]

    return ModuleRecommendation(
        suggested_modules=suggested_modules,
        module_flags=module_flags,
        module_reasons=module_reasons,
    )


def module_recommendation_to_dict(rec: ModuleRecommendation) -> dict[str, Any]:
    return {
        "suggested_modules": rec.suggested_modules,
        "module_flags": rec.module_flags,
        "module_reasons": rec.module_reasons,
    }
