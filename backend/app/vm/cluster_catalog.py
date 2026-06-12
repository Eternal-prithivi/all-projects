"""
Single source of truth for VM cluster pools: 7 clusters × 4 tiered slots × 3 CSPs.

Slot naming: {cluster}-{tier}-vm-{n} (GCP), {cluster}-{tier}-aws-vm-{n}, {cluster}-{tier}-azure-vm-{n}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from app.cloud.providers import normalize_provider
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.vm.models import ClusterType

logger = setup_logger(__name__)

_AZURE_MIN_DISK_GB = 30

# tier -> (gcp_machine, gcp_disk, aws_instance, aws_disk, azure_size, azure_disk)
_TIER_MATRIX: Dict[str, Tuple[str, int, str, int, str, int]] = {
    "micro": ("e2-micro", 10, "t3.micro", 12, "Standard_B1s", 30),
    "small": ("e2-small", 20, "t3.small", 20, "Standard_B2s", 30),
    "medium": ("e2-medium", 30, "t3.medium", 30, "Standard_D2s_v3", 30),
    "standard": ("e2-standard-2", 40, "t3.large", 40, "Standard_D4s_v3", 40),
    "large": ("e2-standard-4", 60, "m5.large", 60, "Standard_D4s_v3", 60),
    "xlarge": ("e2-standard-8", 80, "m5.xlarge", 80, "Standard_D8s_v3", 80),
    "highmem": ("n2-highmem-4", 40, "r5.2xlarge", 40, "Standard_E8s_v3", 40),
    "compute": ("c2-standard-4", 40, "c5.xlarge", 40, "Standard_F4s_v2", 40),
    "accelerator": ("n1-standard-4", 50, "g4dn.xlarge", 50, "Standard_NC4as_T4_v3", 50),
    "iops": ("n2-standard-8", 128, "m5d.2xlarge", 128, "Standard_D8s_v3", 128),
    "network": ("n2-standard-4", 30, "m5n.xlarge", 30, "Standard_D8s_v3", 30),
}

# Optional per-slot kwargs passed to _slot (overrides + disk classes)
_SlotKwargs = Dict[str, Any]
# (tier, label) or (tier, label, slot_kwargs)
_TierDef = Union[Tuple[str, str], Tuple[str, str, _SlotKwargs]]


@dataclass(frozen=True)
class CspSlotSpec:
    machine_type: str
    disk_gb: int
    image: str
    display_machine: str = ""
    disk_type: str = ""
    disk_iops: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "machine_type": self.machine_type,
            "disk_gb": self.disk_gb,
            "image": self.image,
            "display_machine": self.display_machine or self.machine_type,
        }
        if self.disk_type:
            out["disk_type"] = self.disk_type
        if self.disk_iops is not None:
            out["disk_iops"] = self.disk_iops
        return out


@dataclass(frozen=True)
class ProvisionSpec:
    """Resolved launch parameters for a pool slot."""

    machine_type: str
    disk_gb: int
    source_image: str
    disk_type: str = ""
    disk_iops: Optional[int] = None

    @classmethod
    def from_csp_spec(cls, spec: CspSlotSpec) -> ProvisionSpec:
        return cls(
            machine_type=spec.machine_type,
            disk_gb=spec.disk_gb,
            source_image=spec.image,
            disk_type=spec.disk_type,
            disk_iops=spec.disk_iops,
        )


@dataclass(frozen=True)
class SlotDefinition:
    slot_index: int
    tier: str
    tier_label: str
    gcp_id: str
    aws_id: str
    azure_id: str
    gcp: CspSlotSpec
    aws: CspSlotSpec
    azure: CspSlotSpec

    def vm_id(self, csp: str) -> str:
        provider = normalize_provider(csp)
        if provider == "AWS":
            return self.aws_id
        if provider == "Azure":
            return self.azure_id
        return self.gcp_id

    def spec_for(self, csp: str) -> CspSlotSpec:
        provider = normalize_provider(csp)
        if provider == "AWS":
            return self.aws
        if provider == "Azure":
            return self.azure
        return self.gcp

    def display_name(self, cluster_label: str) -> str:
        return f"{cluster_label} · {self.tier_label}"

    def to_metadata_dict(self, csp: str) -> Dict[str, Any]:
        spec = self.spec_for(csp)
        return {
            "slot_index": self.slot_index,
            "vm_name": self.vm_id(csp),
            "tier": self.tier,
            "tier_label": self.tier_label,
            "display_name": self.display_name(""),
            "intended_spec": spec.to_dict(),
        }


@dataclass(frozen=True)
class ClusterDefinition:
    cluster_type: ClusterType
    label: str
    description: str
    badge_class: str
    topology: str = "ring"
    max_vms: int = 4
    slots: Tuple[SlotDefinition, ...] = field(default_factory=tuple)

    def slot_ids(self, csp: str) -> List[str]:
        return [s.vm_id(csp) for s in self.slots]

    def slot_by_id(self, vm_name: str, csp: str) -> Optional[SlotDefinition]:
        canonical = resolve_vm_alias(vm_name, csp)
        for slot in self.slots:
            if slot.vm_id(csp) == canonical:
                return slot
        return None


def _tier_spec(
    tier: str,
    *,
    gcp_image: str = "debian-cloud/debian-12",
    aws_image: str = "ubuntu_22_04",
    azure_image: str = "debian_12",
    gcp_override: Optional[Tuple[str, int]] = None,
    aws_override: Optional[Tuple[str, int]] = None,
    azure_override: Optional[Tuple[str, int]] = None,
    gcp_disk_type: str = "",
    aws_disk_type: str = "",
    azure_disk_type: str = "",
    aws_disk_iops: Optional[int] = None,
) -> Tuple[CspSlotSpec, CspSlotSpec, CspSlotSpec]:
    base = _TIER_MATRIX[tier]
    gcp_m, gcp_d, aws_m, aws_d, az_m, az_d = base
    if gcp_override:
        gcp_m, gcp_d = gcp_override
    if aws_override:
        aws_m, aws_d = aws_override
    if azure_override:
        az_m, az_d = azure_override
    az_d = max(az_d, _AZURE_MIN_DISK_GB)
    return (
        CspSlotSpec(gcp_m, gcp_d, gcp_image, disk_type=gcp_disk_type),
        CspSlotSpec(
            aws_m,
            aws_d,
            aws_image,
            disk_type=aws_disk_type,
            disk_iops=aws_disk_iops,
        ),
        CspSlotSpec(az_m, az_d, azure_image, disk_type=azure_disk_type),
    )


def _cluster_slug(cluster_type: ClusterType) -> str:
    if cluster_type == ClusterType.AI_ML:
        return "ai-ml"
    return cluster_type.value


def _slot(
    cluster_type: ClusterType,
    tier: str,
    tier_label: str,
    index: int,
    *,
    gcp_image: str = "debian-cloud/debian-12",
    aws_image: str = "ubuntu_22_04",
    azure_image: str = "debian_12",
    gcp_override: Optional[Tuple[str, int]] = None,
    aws_override: Optional[Tuple[str, int]] = None,
    azure_override: Optional[Tuple[str, int]] = None,
    gcp_disk_type: str = "",
    aws_disk_type: str = "",
    azure_disk_type: str = "",
    aws_disk_iops: Optional[int] = None,
) -> SlotDefinition:
    gcp, aws, azure = _tier_spec(
        tier,
        gcp_image=gcp_image,
        aws_image=aws_image,
        azure_image=azure_image,
        gcp_override=gcp_override,
        aws_override=aws_override,
        azure_override=azure_override,
        gcp_disk_type=gcp_disk_type,
        aws_disk_type=aws_disk_type,
        azure_disk_type=azure_disk_type,
        aws_disk_iops=aws_disk_iops,
    )
    cluster = _cluster_slug(cluster_type)
    return SlotDefinition(
        slot_index=index,
        tier=tier,
        tier_label=tier_label,
        gcp_id=f"{cluster}-{tier}-vm-{index}",
        aws_id=f"{cluster}-{tier}-aws-vm-{index}",
        azure_id=f"{cluster}-{tier}-azure-vm-{index}",
        gcp=gcp,
        aws=aws,
        azure=azure,
    )


def _cluster(
    cluster_type: ClusterType,
    label: str,
    description: str,
    badge_class: str,
    tier_defs: List[_TierDef],
) -> ClusterDefinition:
    slots: List[SlotDefinition] = []
    for i, item in enumerate(tier_defs):
        if len(item) == 2:
            tier, tier_label = item
            slot_kwargs: _SlotKwargs = {}
        else:
            tier, tier_label, slot_kwargs = item
        slots.append(_slot(cluster_type, tier, tier_label, i + 1, **slot_kwargs))
    return ClusterDefinition(
        cluster_type=cluster_type,
        label=label,
        description=description,
        badge_class=badge_class,
        slots=tuple(slots),
    )


CLUSTER_DEFINITIONS: Tuple[ClusterDefinition, ...] = (
    _cluster(
        ClusterType.GENERAL,
        "General",
        "Burstable web apps and light APIs",
        "general",
        [("micro", "Micro"), ("small", "Small"), ("medium", "Medium"), ("standard", "Standard")],
    ),
    _cluster(
        ClusterType.STORAGE,
        "Storage",
        "Object-heavy ETL and file pipelines",
        "storage",
        [
            ("small", "Small", {"gcp_override": ("e2-small", 50), "aws_override": ("t3.small", 50)}),
            (
                "medium",
                "Medium",
                {
                    "gcp_override": ("e2-standard-2", 80),
                    "aws_override": ("m5.large", 80),
                    "azure_override": ("Standard_D4s_v3", 80),
                    "gcp_disk_type": "pd-balanced",
                    "aws_disk_type": "gp3",
                },
            ),
            (
                "large",
                "Large",
                {
                    "gcp_override": ("e2-standard-4", 128),
                    "aws_override": ("m5.xlarge", 128),
                    "azure_override": ("Standard_D8s_v3", 128),
                    "gcp_disk_type": "pd-balanced",
                    "aws_disk_type": "gp3",
                },
            ),
            (
                "xlarge",
                "X-Large",
                {
                    "gcp_override": ("n2-standard-4", 256),
                    "aws_override": ("m5.2xlarge", 256),
                    "azure_override": ("Standard_D8s_v3", 256),
                    "gcp_disk_type": "pd-ssd",
                    "aws_disk_type": "io2",
                    "azure_disk_type": "Premium_LRS",
                    "aws_disk_iops": 3000,
                },
            ),
        ],
    ),
    _cluster(
        ClusterType.MEMORY,
        "Memory",
        "In-memory caches and RAM-heavy workloads",
        "memory",
        [
            ("medium", "Medium"),
            (
                "large",
                "Large",
                {
                    "gcp_override": ("n2-highmem-2", 60),
                    "aws_override": ("r5.large", 60),
                    "azure_override": ("Standard_E4s_v3", 60),
                },
            ),
            (
                "xlarge",
                "X-Large",
                {
                    "gcp_override": ("n2-highmem-4", 80),
                    "aws_override": ("r5.xlarge", 80),
                    "azure_override": ("Standard_E8s_v3", 80),
                },
            ),
            (
                "highmem",
                "High-Mem",
                {
                    "gcp_override": ("n2-highmem-8", 96),
                    "aws_override": ("r5.2xlarge", 96),
                    "azure_override": ("Standard_E16s_v3", 96),
                },
            ),
        ],
    ),
    _cluster(
        ClusterType.PERFORMANCE,
        "Performance",
        "CPU-bound compute and batch jobs",
        "performance",
        [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            (
                "compute",
                "Compute",
                {
                    "gcp_override": ("c2-standard-4", 60),
                    "aws_override": ("c5.xlarge", 60),
                    "azure_override": ("Standard_F4s_v2", 60),
                },
            ),
        ],
    ),
    _cluster(
        ClusterType.AI_ML,
        "AI/ML",
        "Training and inference workloads",
        "ai_ml",
        [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            (
                "accelerator",
                "Accelerator",
                {
                    "gcp_override": ("n1-standard-4", 60),
                    "aws_override": ("g4dn.xlarge", 60),
                    "azure_override": ("Standard_NC4as_T4_v3", 60),
                },
            ),
        ],
    ),
    _cluster(
        ClusterType.DATABASE,
        "Database",
        "PostgreSQL, MySQL, and OLTP databases",
        "database",
        [
            (
                "small",
                "Small",
                {
                    "gcp_override": ("n2-standard-2", 40),
                    "aws_override": ("m5.large", 40),
                    "azure_override": ("Standard_D4s_v3", 40),
                },
            ),
            (
                "medium",
                "Medium",
                {
                    "gcp_override": ("n2-standard-4", 60),
                    "aws_override": ("m5.xlarge", 60),
                    "azure_override": ("Standard_D4s_v3", 60),
                    "gcp_disk_type": "pd-balanced",
                    "aws_disk_type": "gp3",
                },
            ),
            (
                "large",
                "Large",
                {
                    "gcp_override": ("n2-standard-8", 80),
                    "aws_override": ("m5.2xlarge", 80),
                    "azure_override": ("Standard_D8s_v3", 80),
                    "gcp_disk_type": "pd-balanced",
                    "aws_disk_type": "gp3",
                },
            ),
            (
                "iops",
                "IOPS",
                {
                    "gcp_override": ("n2-standard-16", 128),
                    "gcp_disk_type": "pd-ssd",
                    "aws_disk_type": "io2",
                    "azure_disk_type": "Premium_LRS",
                    "aws_disk_iops": 5000,
                },
            ),
        ],
    ),
    _cluster(
        ClusterType.NETWORK,
        "Network",
        "Proxies, gateways, and streaming ingress",
        "network",
        [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            (
                "network",
                "Network",
                {
                    "aws_override": ("m5n.xlarge", 80),
                    "gcp_override": ("n2-standard-4", 80),
                    "azure_override": ("Standard_D8s_v3", 80),
                },
            ),
        ],
    ),
)

_CLUSTER_BY_TYPE: Dict[ClusterType, ClusterDefinition] = {
    d.cluster_type: d for d in CLUSTER_DEFINITIONS
}

# Legacy slot names from pre-expansion pools (2 VMs per cluster)
_LEGACY_ALIASES: Dict[str, str] = {}
for _def in CLUSTER_DEFINITIONS:
    _slug = _cluster_slug(_def.cluster_type)
    _LEGACY_ALIASES[f"{_slug}-vm-1"] = _def.slots[0].gcp_id
    _LEGACY_ALIASES[f"{_slug}-vm-2"] = _def.slots[1].gcp_id
    _LEGACY_ALIASES[f"{_slug}-aws-vm-1"] = _def.slots[0].aws_id
    _LEGACY_ALIASES[f"{_slug}-aws-vm-2"] = _def.slots[1].aws_id
    _LEGACY_ALIASES[f"{_slug}-azure-vm-1"] = _def.slots[0].azure_id
    _LEGACY_ALIASES[f"{_slug}-azure-vm-2"] = _def.slots[1].azure_id


def cluster_types() -> List[ClusterType]:
    return [d.cluster_type for d in CLUSTER_DEFINITIONS]


def get_cluster_definition(cluster_type: ClusterType) -> ClusterDefinition:
    return _CLUSTER_BY_TYPE[cluster_type]


def cluster_vms(csp: str, cluster_type: ClusterType) -> List[str]:
    return get_cluster_definition(cluster_type).slot_ids(csp)


def cluster_max_vms(cluster_type: ClusterType) -> int:
    override = getattr(settings, "CLUSTER_MAX_VMS_DEFAULT", None)
    if override is not None:
        return int(override)
    return get_cluster_definition(cluster_type).max_vms


def cluster_create_spec(
    csp: str,
    cluster_type: ClusterType,
    slot_id: Optional[str] = None,
) -> ProvisionSpec:
    """Return launch parameters for a pool slot."""
    definition = get_cluster_definition(cluster_type)
    slot: Optional[SlotDefinition] = None
    if slot_id:
        slot = definition.slot_by_id(slot_id, csp)
        if slot is None:
            slot = find_slot_by_vm_name(slot_id, csp)
    if slot is None and definition.slots:
        slot = definition.slots[0]
    if slot is None:
        raise ValueError(f"No slots configured for cluster {cluster_type.value}")
    return ProvisionSpec.from_csp_spec(slot.spec_for(csp))


def find_slot_by_vm_name(vm_name: str, csp: str) -> Optional[SlotDefinition]:
    canonical = resolve_vm_alias(vm_name, csp)
    for definition in CLUSTER_DEFINITIONS:
        slot = definition.slot_by_id(canonical, csp)
        if slot:
            return slot
    return None


def resolve_vm_alias(vm_name: str, csp: str) -> str:
    name = (vm_name or "").strip()
    if name in _LEGACY_ALIASES:
        logger.debug("Resolving legacy VM alias %s -> %s", name, _LEGACY_ALIASES[name])
        return _LEGACY_ALIASES[name]
    return name


def infer_cluster_from_vm_name(vm_name: str) -> ClusterType:
    canonical = resolve_vm_alias(vm_name, "GCP")
    for definition in CLUSTER_DEFINITIONS:
        slug = _cluster_slug(definition.cluster_type)
        if canonical.startswith(f"{slug}-"):
            return definition.cluster_type
        if definition.cluster_type == ClusterType.AI_ML and (
            canonical.startswith("ai-ml-") or canonical.startswith("ai_ml-")
        ):
            return ClusterType.AI_ML
    if "general" in canonical:
        return ClusterType.GENERAL
    if "storage" in canonical:
        return ClusterType.STORAGE
    if "memory" in canonical:
        return ClusterType.MEMORY
    if "performance" in canonical:
        return ClusterType.PERFORMANCE
    if "ai-ml" in canonical or "ai_ml" in canonical:
        return ClusterType.AI_ML
    if "database" in canonical:
        return ClusterType.DATABASE
    if "network" in canonical:
        return ClusterType.NETWORK
    return ClusterType.GENERAL


def all_pool_vm_names(csp: str) -> List[str]:
    names: List[str] = []
    for definition in CLUSTER_DEFINITIONS:
        names.extend(definition.slot_ids(csp))
    return names


def clusters_metadata(csp: str) -> List[Dict[str, Any]]:
    """UI metadata for GET /api/vm/clusters."""
    out: List[Dict[str, Any]] = []
    for definition in CLUSTER_DEFINITIONS:
        slots_meta = []
        for slot in definition.slots:
            spec = slot.spec_for(csp)
            slots_meta.append(
                {
                    "slot_index": slot.slot_index,
                    "vm_name": slot.vm_id(csp),
                    "tier": slot.tier,
                    "tier_label": slot.tier_label,
                    "display_name": f"{definition.label} · {slot.tier_label}",
                    "intended_spec": spec.to_dict(),
                }
            )
        out.append(
            {
                "cluster_type": definition.cluster_type.value,
                "label": definition.label,
                "description": definition.description,
                "badge_class": definition.badge_class,
                "topology": definition.topology,
                "max_vms": cluster_max_vms(definition.cluster_type),
                "slots": slots_meta,
            }
        )
    return out


# Backward-compatible dict for code that imported CLUSTER_VMS from manager
def legacy_cluster_vms_dict() -> Dict[ClusterType, List[str]]:
    return {d.cluster_type: d.slot_ids("GCP") for d in CLUSTER_DEFINITIONS}
