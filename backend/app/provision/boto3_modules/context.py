from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeployContext:
    """Resource IDs passed between modules during apply/destroy."""

    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    public_subnet_ids: list[str] = field(default_factory=list)
    launch_availability_zone: Optional[str] = None
    launched_instance_type: Optional[str] = None
    ec2_os: Optional[str] = None
    iam_role_preset: Optional[str] = None
    instance_id: Optional[str] = None
    security_group_id: Optional[str] = None
    role_arn: Optional[str] = None
    instance_profile_name: Optional[str] = None
    sns_topic_arn: Optional[str] = None
    bucket_name: Optional[str] = None
    dynamodb_table: Optional[str] = None
    budget_name: Optional[str] = None
    public_ip: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.public_subnet_ids:
            out["public_subnet_ids"] = ",".join(self.public_subnet_ids)
        for key, val in (
            ("vpc_id", self.vpc_id),
            ("subnet_id", self.subnet_id),
            ("launch_availability_zone", self.launch_availability_zone),
            ("launched_instance_type", self.launched_instance_type),
            ("ec2_os", self.ec2_os),
            ("iam_role_preset", self.iam_role_preset),
            ("instance_id", self.instance_id),
            ("security_group_id", self.security_group_id),
            ("role_arn", self.role_arn),
            ("instance_profile_name", self.instance_profile_name),
            ("sns_topic_arn", self.sns_topic_arn),
            ("bucket_name", self.bucket_name),
            ("dynamodb_table", self.dynamodb_table),
            ("budget_name", self.budget_name),
            ("public_ip", self.public_ip),
        ):
            if val:
                out[key] = val
        return out

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> DeployContext:
        if not data:
            return cls()
        raw_subnets = data.get("public_subnet_ids") or ""
        public_subnet_ids = [s for s in raw_subnets.split(",") if s] if raw_subnets else []
        return cls(
            vpc_id=data.get("vpc_id"),
            subnet_id=data.get("subnet_id"),
            public_subnet_ids=public_subnet_ids,
            launch_availability_zone=data.get("launch_availability_zone"),
            launched_instance_type=data.get("launched_instance_type"),
            ec2_os=data.get("ec2_os"),
            iam_role_preset=data.get("iam_role_preset"),
            instance_id=data.get("instance_id"),
            security_group_id=data.get("security_group_id"),
            role_arn=data.get("role_arn"),
            instance_profile_name=data.get("instance_profile_name"),
            sns_topic_arn=data.get("sns_topic_arn"),
            bucket_name=data.get("bucket_name"),
            dynamodb_table=data.get("dynamodb_table"),
            budget_name=data.get("budget_name"),
            public_ip=data.get("public_ip"),
        )
