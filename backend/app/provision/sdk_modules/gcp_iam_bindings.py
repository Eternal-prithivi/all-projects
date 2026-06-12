"""Grant GCP IAM roles for provisioned service accounts."""

from __future__ import annotations

from typing import Any

from google.auth.transport.requests import AuthorizedSession


def _member_for_sa(email: str) -> str:
    return email if email.startswith("serviceAccount:") else f"serviceAccount:{email}"


def bind_gcs_bucket_roles(
    storage_client: Any,
    bucket_name: str,
    sa_email: str,
    roles: list[str],
    steps: list[str],
) -> None:
    if not bucket_name or not roles:
        return
    bucket = storage_client.bucket(bucket_name)
    policy = bucket.get_iam_policy(requested_policy_version=3)
    member = _member_for_sa(sa_email)
    for role in roles:
        binding = next((b for b in policy.bindings if b.get("role") == role), None)
        if binding is None:
            policy.bindings.append({"role": role, "members": {member}})
        else:
            binding.setdefault("members", set()).add(member)
        steps.append(f"✓ Bucket IAM: {role} for {sa_email}")
    bucket.set_iam_policy(policy)


def bind_gcp_project_roles(
    credentials: Any,
    project_id: str,
    sa_email: str,
    roles: list[str],
    steps: list[str],
) -> None:
    if not project_id or not roles:
        return
    session = AuthorizedSession(credentials)
    member = _member_for_sa(sa_email)
    get_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:getIamPolicy"
    policy = session.post(get_url, json={}).json()
    bindings = policy.setdefault("bindings", [])
    for role in roles:
        binding = next((b for b in bindings if b.get("role") == role), None)
        if binding is None:
            bindings.append({"role": role, "members": [member]})
        elif member not in binding.setdefault("members", []):
            binding["members"].append(member)
        steps.append(f"✓ Project IAM: {role} for {sa_email}")
    set_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:setIamPolicy"
    response = session.post(set_url, json={"policy": policy})
    if response.status_code >= 400:
        raise RuntimeError(f"Project IAM update failed: {response.text}")
