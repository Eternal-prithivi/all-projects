"""
Intent-aware follow-up questions — reactive to NLP cluster and detected modules.

Generic readiness slots (scale, environment) are replaced with questions that
match what the user is actually building (e.g. S3 → region & volume, not CPU).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.vm.models import ClusterType

# Labels merged into the effective description for NLP / module scoring
ANSWER_LABELS: Dict[str, str] = {
    "storage_region": "Storage region",
    "storage_volume": "Expected storage size",
    "storage_access": "Storage access pattern",
    "storage_environment": "Storage environment",
    "db_model": "Database workload pattern",
    "db_volume": "Database data size",
    "db_backup": "Backup requirement",
    "compute_traffic": "Expected traffic",
    "compute_region": "Compute region",
    "compute_environment": "Deployment environment",
    "static_traffic": "Expected visitors",
    "static_cdn": "CDN / caching needs",
}

REGION_PATTERNS = re.compile(
    r"\b("
    r"us-east-1|us-west-2|eu-west-1|ap-south-1|ap-southeast-1|"
    r"us-central1|europe-west1|asia-south1|"
    r"eastus|westeurope|southeastasia|"
    r"mumbai|singapore|virginia|ireland|london|ohio|oregon"
    r")\b",
    re.I,
)

VOLUME_PATTERNS = re.compile(
    r"\b\d+\s*(gb|tb|pb|mb)\b|"
    r"\b(under|less than|about|around)\s+\d+\s*(gb|tb)\b|"
    r"\b(5\s*gb|few\s*gb|small\s*files?|large\s*files?)\b",
    re.I,
)

ENV_PATTERNS = re.compile(
    r"\b(production|prod|staging|dev|test|demo|personal|prototype)\b",
    re.I,
)

TRAFFIC_PATTERNS = re.compile(
    r"\b(\d+\s*(users|requests|rps|qps|visitors)|high\s*traffic|low\s*traffic|"
    r"small\s*team|internal\s*only)\b",
    re.I,
)


def answer_label(question_id: str) -> str:
    return ANSWER_LABELS.get(question_id, question_id.replace("_", " ").title())


def _region_options(csp: str) -> List[str]:
    from app.cloud.providers import normalize_provider

    provider = normalize_provider(csp)
    if provider == "GCP":
        return [
            "us-central1 (Iowa)",
            "europe-west1 (Belgium)",
            "asia-south1 (Mumbai)",
            "Not sure — use a sensible default",
        ]
    if provider == "Azure":
        return [
            "East US",
            "West Europe",
            "Southeast Asia",
            "Not sure — use a sensible default",
        ]
    return [
        "ap-south-1 (Mumbai)",
        "us-east-1 (N. Virginia)",
        "eu-west-1 (Ireland)",
        "Not sure — use a sensible default",
    ]


def _classify_intent(
    text: str,
    cluster_type: Optional[ClusterType],
    module_keys: Optional[List[str]] = None,
) -> str:
    lower = (text or "").lower()
    keys = set(module_keys or [])

    storage_keys = {"s3", "gcs", "azure_storage"}
    db_keys = {"dynamodb", "firestore", "cosmos"}
    compute_keys = {"ec2", "gce", "azure_vm"}

    if keys & storage_keys or cluster_type == ClusterType.STORAGE:
        if re.search(r"\b(static|website|html|landing|cdn)\b", lower):
            return "static_web"
        return "storage"
    if keys & db_keys or re.search(r"\b(dynamodb|firestore|cosmos|nosql|database)\b", lower):
        return "database"
    if keys & compute_keys or cluster_type in (
        ClusterType.PERFORMANCE,
        ClusterType.MEMORY,
        ClusterType.AI_ML,
    ):
        return "compute"
    if re.search(r"\b(api|backend|server|microservice|web\s*app)\b", lower):
        return "compute"
    if re.search(r"\b(static|website|landing|portfolio)\b", lower):
        return "static_web"
    if cluster_type == ClusterType.GENERAL:
        return "general"
    return "general"


INTENT_META: Dict[str, Dict[str, str]] = {
    "storage": {
        "label": "Object storage setup",
        "intro": "A few details about your bucket or file storage",
    },
    "static_web": {
        "label": "Static site hosting",
        "intro": "Help us size hosting for your website assets",
    },
    "database": {
        "label": "Database setup",
        "intro": "A few details about your data store",
    },
    "compute": {
        "label": "Application / server setup",
        "intro": "Help us right-size compute for your workload",
    },
    "general": {
        "label": "Workload details",
        "intro": "A few details to sharpen the recommendation",
    },
}


def _question_bank(intent: str, csp: str) -> List[Dict[str, Any]]:
    if intent == "storage":
        return [
            {
                "id": "storage_region",
                "question": "Which region should this bucket live in?",
                "options": _region_options(csp),
                "hint": "Pick a region close to your users to reduce latency and data transfer cost.",
                "detected_by": REGION_PATTERNS,
            },
            {
                "id": "storage_volume",
                "question": "How much data do you expect to store?",
                "options": [
                    "Under 5 GB (personal / small project)",
                    "5–50 GB (team files or app uploads)",
                    "50 GB – 1 TB (media or backups)",
                    "Over 1 TB (large archive)",
                    "Not sure yet",
                ],
                "hint": "Rough size is enough — we use it for cost estimates and tiering.",
                "detected_by": VOLUME_PATTERNS,
            },
            {
                "id": "storage_access",
                "question": "How will this storage be used?",
                "options": [
                    "Private — only my app or team",
                    "Static website or public assets",
                    "Backups and archives",
                    "User uploads (photos, documents)",
                ],
                "hint": "Access pattern affects encryption, public access blocks, and IAM.",
                "detected_by": re.compile(
                    r"\b(private|public|backup|archive|upload|website|static)\b",
                    re.I,
                ),
            },
            {
                "id": "storage_environment",
                "question": "Is this for production or testing?",
                "options": [
                    "Production — needs reliability",
                    "Staging / QA",
                    "Development or personal sandbox",
                ],
                "hint": "Production buckets typically need versioning and stricter policies.",
                "detected_by": ENV_PATTERNS,
            },
        ]
    if intent == "static_web":
        return [
            {
                "id": "storage_region",
                "question": "Where should visitors load your site from?",
                "options": _region_options(csp),
                "hint": "Choose a region near your audience.",
                "detected_by": REGION_PATTERNS,
            },
            {
                "id": "static_traffic",
                "question": "How much traffic do you expect?",
                "options": [
                    "Personal site or portfolio (low)",
                    "Small business / hundreds of visitors per day",
                    "Thousands of visitors per day",
                    "Not sure",
                ],
                "hint": "Traffic guides CDN and caching recommendations.",
                "detected_by": TRAFFIC_PATTERNS,
            },
            {
                "id": "static_cdn",
                "question": "Do you need a CDN in front of storage?",
                "options": [
                    "No — direct bucket access is fine",
                    "Yes — faster global delivery",
                    "Not sure",
                ],
                "hint": "CDNs help when visitors are spread across regions.",
                "detected_by": re.compile(r"\b(cdn|cloudfront|cache|caching)\b", re.I),
            },
        ]
    if intent == "database":
        return [
            {
                "id": "db_model",
                "question": "What kind of database workload is this?",
                "options": [
                    "Mostly reads (catalog, config, cache)",
                    "Mostly writes (events, logs, IoT)",
                    "Balanced reads and writes",
                    "Key-value / session store",
                ],
                "hint": "Workload shape affects capacity and table design.",
                "detected_by": re.compile(r"\b(read|write|session|log|event)\b", re.I),
            },
            {
                "id": "db_volume",
                "question": "How much data will the database hold?",
                "options": [
                    "Under 1 GB",
                    "1 GB – 100 GB",
                    "100 GB – 1 TB",
                    "Over 1 TB",
                ],
                "hint": "Size helps pick provisioned vs on-demand capacity.",
                "detected_by": VOLUME_PATTERNS,
            },
            {
                "id": "db_backup",
                "question": "Do you need point-in-time backups?",
                "options": [
                    "Yes — production data",
                    "Nice to have",
                    "No — disposable dev data",
                ],
                "hint": "Backups matter for production databases.",
                "detected_by": re.compile(r"\b(backup|restore|pitr|snapshot)\b", re.I),
            },
            {
                "id": "storage_region",
                "question": "Which region should the database run in?",
                "options": _region_options(csp),
                "hint": "Co-locate the database with your application region.",
                "detected_by": REGION_PATTERNS,
            },
        ]
    if intent == "compute":
        return [
            {
                "id": "compute_traffic",
                "question": "What traffic or load do you expect?",
                "options": [
                    "Low — dev or internal tool",
                    "Moderate — small production API",
                    "High — many concurrent users",
                    "Batch / periodic jobs only",
                ],
                "hint": "Load drives instance size and autoscaling.",
                "detected_by": TRAFFIC_PATTERNS,
            },
            {
                "id": "compute_region",
                "question": "Which region should the server run in?",
                "options": _region_options(csp),
                "hint": "Run compute close to users and dependent services.",
                "detected_by": REGION_PATTERNS,
            },
            {
                "id": "compute_environment",
                "question": "What environment is this for?",
                "options": [
                    "Production (high availability)",
                    "Staging / testing",
                    "Development only",
                ],
                "hint": "Production workloads get monitoring and stricter defaults.",
                "detected_by": ENV_PATTERNS,
            },
        ]
    # general fallback — still more concrete than old generic slots
    scale_detector = re.compile(
        f"{VOLUME_PATTERNS.pattern}|{TRAFFIC_PATTERNS.pattern}",
        re.I,
    )
    return [
        {
            "id": "compute_traffic",
            "question": "What are you building, at a high level?",
            "options": [
                "File or object storage",
                "Web or API application",
                "Database or data store",
                "Something else / mixed",
            ],
            "hint": "This helps route you to the right modules.",
        },
        {
            "id": "storage_volume",
            "question": "Any sense of scale (data size or users)?",
            "options": [
                "Very small — hobby / learning",
                "Small team or startup",
                "Medium production workload",
                "Not sure yet",
            ],
            "hint": "Even a rough scale improves recommendations.",
            "detected_by": scale_detector,
        },
    ]


def _already_known(text: str, spec: Dict[str, Any], answers: Dict[str, str]) -> bool:
    qid = spec["id"]
    if answers.get(qid, "").strip():
        return True
    detector = spec.get("detected_by")
    if detector and detector.search(text or ""):
        return True
    return False


def build_contextual_follow_up_questions(
    effective_description: str,
    *,
    cluster_type: Optional[ClusterType] = None,
    module_keys: Optional[List[str]] = None,
    csp: str = "AWS",
    follow_up_answers: Optional[Dict[str, str]] = None,
    max_questions: int = 3,
) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Return follow-up questions tailored to the inferred intent.
    Also returns intent metadata for the UI.
    """
    answers = follow_up_answers or {}
    intent = _classify_intent(effective_description, cluster_type, module_keys)
    meta = INTENT_META.get(intent, INTENT_META["general"])
    bank = _question_bank(intent, csp)

    questions: List[Dict[str, Any]] = []
    for spec in bank:
        if _already_known(effective_description, spec, answers):
            continue
        questions.append(
            {
                "id": spec["id"],
                "question": spec["question"],
                "options": spec["options"],
                "hint": spec.get("hint", ""),
                "signal_label": answer_label(spec["id"]),
                "intent": intent,
            }
        )
        if len(questions) >= max_questions:
            break

    return questions, {"kind": intent, **meta}
