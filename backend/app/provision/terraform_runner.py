# =============================================================================
# MODULE: provision/terraform_runner.py
# PURPOSE: Wraps Terraform CLI subprocess calls — plan, apply, destroy, init
# USED BY: routes_provision.py (all deploy endpoints), tasks.py (drift check)
# DEPENDS ON: Terraform CLI installed on server, BYOC credentials for AWS auth
# DO NOT:
#   - Run terraform commands without injecting BYOC credentials as env vars
#   - Remove -no-color flag — SSE streaming parses plain text output
#   - Remove -input=false — prevents terraform from waiting for stdin
# =============================================================================
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


def get_terraform_root() -> Path:
    """
    Resolve backend/terraform for local dev and Docker (Render).

    Local:  backend/app/provision/ → backend/terraform
    Docker: /app/app/provision/    → /app/terraform (also set via COPY in Dockerfile)
    """
    if custom := os.getenv("TERRAFORM_ROOT"):
        return Path(custom)

    here = Path(__file__).resolve()
    for base in (here.parent.parent.parent, here.parent.parent.parent.parent):
        candidate = base / "terraform"
        if candidate.is_dir():
            return candidate

    return here.parent.parent.parent / "terraform"


# Path to the Terraform modules/configs inside Zenith's backend
TERRAFORM_ROOT = get_terraform_root()


def check_terraform_installed() -> bool:
    """Check if the terraform CLI is available on PATH."""
    return shutil.which("terraform") is not None


def get_terraform_version() -> Optional[str]:
    """Return the installed terraform version string, or None if not installed."""
    try:
        result = subprocess.run(
            ["terraform", "version", "-json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("terraform_version", "unknown")
    except Exception:
        pass
    return None


class TerraformRunner:
    """
    Manages Terraform operations for a single user deployment.

    Each deployment gets its own workspace directory (copy of TERRAFORM_ROOT)
    so multiple users' deployments don't collide.
    """

    def __init__(
        self,
        workspace_dir: str,
        aws_credentials: Optional[dict] = None,
        *,
        cloud_env: Optional[dict] = None,
    ):
        """
        Args:
            workspace_dir: Absolute path to the workspace for this deployment.
            aws_credentials: Legacy AWS-only env dict (alias for cloud_env).
            cloud_env: Full BYOC env (AWS, GCP GOOGLE_*, Azure ARM_*).
        """
        self.workspace_dir = Path(workspace_dir)
        merged = dict(cloud_env or aws_credentials or {})
        self.aws_credentials = merged
        self.cloud_env = merged

    def _get_env(self) -> dict[str, str]:
        """Build environment variables for terraform subprocess."""
        env = os.environ.copy()
        cache = os.getenv("TF_PLUGIN_CACHE_DIR")
        if cache:
            env["TF_PLUGIN_CACHE_DIR"] = cache
        for key, value in self.cloud_env.items():
            if value is not None and str(value).strip():
                env[key] = str(value)
        return env

    def init(self) -> dict[str, Any]:
        """Run terraform init in the workspace."""
        try:
            result = subprocess.run(
                ["terraform", "init", "-input=false", "-no-color"],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.workspace_dir),
                env=self._get_env(),
            )
            ok = result.returncode == 0
            combined = ((result.stdout or "") + (result.stderr or "")).strip()
            return {
                "success": ok,
                "output": result.stdout,
                "error": combined if not ok else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Terraform init timed out (300s)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def plan(self) -> dict[str, Any]:
        """Run terraform plan and return the result."""
        # Render free tier + cross-region AWS can exceed 4 minutes; skip refresh to speed plan.
        plan_timeout_s = 480
        plan_cmd = [
            "terraform", "plan",
            "-input=false", "-no-color",
            "-parallelism=1",
            "-refresh=false",
        ]
        try:
            result = subprocess.run(
                plan_cmd,
                capture_output=True, text=True, timeout=plan_timeout_s,
                cwd=str(self.workspace_dir),
                env=self._get_env(),
            )
            # Terraform: 0 = no changes, 1 = error, 2 = changes present (still success)
            ok = result.returncode in (0, 2)
            combined = (result.stdout or "") + (result.stderr or "")
            return {
                "success": ok,
                "output": result.stdout,
                "error": combined.strip() if not ok else None,
                "has_changes": result.returncode == 2 or "No changes." not in result.stdout,
            }
        except subprocess.TimeoutExpired as exc:
            partial = ((exc.stdout or "") + (exc.stderr or "")).strip()
            if len(partial) > 3000:
                partial = "…\n" + partial[-3000:]
            msg = (
                f"Terraform plan timed out ({plan_timeout_s}s). "
                "AWS may be slow from Render, or BYOC credentials may lack permissions. "
                "Try again in a few minutes."
            )
            if partial:
                msg = f"{msg}\n\nPartial terraform output:\n{partial}"
            return {"success": False, "output": partial, "error": msg}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def plan_stream(self) -> AsyncGenerator[str, None]:
        """Run terraform plan and stream output as SSE events."""
        async for line in self._stream_command(
            ["terraform", "plan", "-input=false", "-no-color"]
        ):
            yield line

    def apply(self) -> dict[str, Any]:
        """Run terraform apply (auto-approve) and return the result."""
        try:
            result = subprocess.run(
                ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
                capture_output=True, text=True, timeout=600,
                cwd=str(self.workspace_dir),
                env=self._get_env(),
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Terraform apply timed out (600s)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def apply_stream(self) -> AsyncGenerator[str, None]:
        """Run terraform apply and stream output as SSE events."""
        async for line in self._stream_command(
            ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"]
        ):
            yield line

    def destroy(self) -> dict[str, Any]:
        """Run terraform destroy (auto-approve) and return the result."""
        try:
            result = subprocess.run(
                ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"],
                capture_output=True, text=True, timeout=600,
                cwd=str(self.workspace_dir),
                env=self._get_env(),
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Terraform destroy timed out (600s)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def destroy_stream(self) -> AsyncGenerator[str, None]:
        """Run terraform destroy and stream output as SSE events."""
        async for line in self._stream_command(
            ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"]
        ):
            yield line

    def get_state_resources(self) -> list[str]:
        """Parse terraform.tfstate and return list of managed resource names."""
        state_path = self.workspace_dir / "terraform.tfstate"
        if not state_path.exists():
            return []
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            resources = []
            for res in state.get("resources", []):
                if res.get("mode") == "managed":
                    name = f"{res.get('module', '')}.{res['type']}.{res['name']}".lstrip(".")
                    resources.append(name)
            return resources
        except Exception:
            return []

    async def _stream_command(self, command: list[str]) -> AsyncGenerator[str, None]:
        """Execute a command and yield SSE-formatted lines."""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(self.workspace_dir),
            env=self._get_env(),
        )

        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            yield f"data: {json.dumps({'line': text})}\n\n"

        return_code = await process.wait()
        yield f"data: {json.dumps({'done': True, 'exit_code': return_code})}\n\n"


def create_workspace(deployment_id: str, csp: str = "AWS") -> str:
    """
    Create a new workspace directory for a deployment by copying the provider root.

    Returns the absolute path to the new workspace.
    """
    from app.provision.terraform_roots import get_terraform_root

    source_root = get_terraform_root(csp)
    workspaces_dir = source_root.parent / "terraform_workspaces"
    workspaces_dir.mkdir(exist_ok=True)

    workspace_path = workspaces_dir / deployment_id
    if workspace_path.exists():
        return str(workspace_path)

    shutil.copytree(
        str(source_root),
        str(workspace_path),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".terraform"),
    )

    # Per-deployment local state (BYOC keys must not need access to platform S3 state bucket)
    _write_local_backend_config(workspace_path)

    # Reuse provider plugins baked into the image at Docker build (faster init on Render)
    _bootstrap_workspace_providers(workspace_path)

    logger.info(f"Created terraform workspace: {workspace_path}")
    return str(workspace_path)


def _bootstrap_workspace_providers(workspace_path: Path) -> None:
    """Copy pre-downloaded .terraform providers from the template tree when available."""
    from app.provision.terraform_roots import get_terraform_root

    src = get_terraform_root("AWS") / ".terraform"
    dest = workspace_path / ".terraform"
    if not src.is_dir():
        return
    try:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        logger.info("Bootstrapped terraform providers into workspace %s", workspace_path)
    except OSError as exc:
        logger.warning("Could not copy .terraform providers: %s", exc)


def _write_local_backend_config(workspace_path: Path) -> None:
    """Replace shared S3 backend with local state for this deployment workspace."""
    backend_tf = workspace_path / "backend.tf"
    backend_tf.write_text(
        "# Generated by Zenith — isolated state for this deployment (Render / BYOC)\n"
        'terraform {\n'
        '  backend "local" {\n'
        '    path = "terraform.tfstate"\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )


def write_tfvars(workspace_dir: str, config: dict[str, Any]) -> str:
    """
    Write a terraform.tfvars file into the workspace from a config dict.

    Returns the path to the written file.
    """
    from app.cloud.providers import normalize_provider
    from app.provision.config_normalize import normalize_provision_config

    try:
        normalize_provision_config(config)
    except ValueError:
        pass

    provider = normalize_provider(config.get("csp") or "AWS")
    if provider == "GCP":
        return _write_gcp_tfvars(workspace_dir, config)
    if provider == "Azure":
        return _write_azure_tfvars(workspace_dir, config)

    bucket_name = (config.get("bucket_name") or "").strip()
    lines: list[str] = [
        f'aws_region = "{config.get("aws_region", "ap-south-1")}"',
        "",
        f'enable_vpc        = {str(config.get("enable_vpc", False)).lower()}',
        f'enable_ec2        = {str(config.get("enable_ec2", False)).lower()}',
        f'enable_s3         = {str(config.get("enable_s3", False)).lower()}',
        f'enable_iam        = {str(config.get("enable_iam", False)).lower()}',
        f'enable_cloudwatch = {str(config.get("enable_cloudwatch", False)).lower()}',
        f'enable_dynamodb   = {str(config.get("enable_dynamodb", False)).lower()}',
        f'enable_billing    = {str(config.get("enable_billing", False)).lower()}',
        "",
        f'vpc_cidr      = "{config.get("vpc_cidr", "10.0.0.0/16")}"',
        f'instance_type = "{config.get("instance_type", "t2.micro")}"',
        f'instance_name = "{config.get("instance_name", "main-instance")}"',
        f'ami_id        = "{config.get("ami_id", "")}"',
        f'bucket_name   = "{bucket_name}"',
        f'dynamodb_table_name = "{config.get("dynamodb_table_name", "")}"',
        f'role_name     = "{config.get("role_name", "app-role")}"',
        f'alarm_email   = "{config.get("alarm_email", "")}"',
        "",
        f'budget_limit = "{config.get("budget_limit", "1")}"',
        f'budget_email = "{config.get("budget_email", "")}"',
        "",
        "tags = {",
    ]
    for key, value in config.get("tags", {}).items():
        lines.append(f'  {key} = "{value}"')
    lines.append("}")
    lines.append("")
    lines.append(f'dynamodb_hash_key = "{config.get("dynamodb_hash_key", "id")}"')
    lines.append(f'dynamodb_hash_key_type = "{config.get("dynamodb_hash_key_type", "S")}"')
    lines.append(f'dynamodb_read_capacity = {config.get("dynamodb_read_capacity", 5)}')
    lines.append(f'dynamodb_write_capacity = {config.get("dynamodb_write_capacity", 5)}')
    lines.append(f'dynamodb_enable_pitr = {str(config.get("dynamodb_enable_pitr", False)).lower()}')
    lines.append("")

    tfvars_path = Path(workspace_dir) / "terraform.tfvars"
    tfvars_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote terraform.tfvars to {tfvars_path}")
    return str(tfvars_path)


def _write_gcp_tfvars(workspace_dir: str, config: dict[str, Any]) -> str:
    bucket_name = (config.get("bucket_name") or "").strip()
    lines = [
        f'gcp_project = "{config.get("gcp_project", "")}"',
        f'gcp_region  = "{config.get("gcp_region", "us-central1")}"',
        "",
        f'enable_gcs  = {str(config.get("enable_gcs", False)).lower()}',
        f'bucket_name = "{bucket_name}"',
        "",
        "tags = {",
    ]
    for key, value in config.get("tags", {}).items():
        lines.append(f'  {key} = "{value}"')
    lines.append("}")
    lines.append("")
    tfvars_path = Path(workspace_dir) / "terraform.tfvars"
    tfvars_path.write_text("\n".join(lines), encoding="utf-8")
    return str(tfvars_path)


def _write_azure_tfvars(workspace_dir: str, config: dict[str, Any]) -> str:
    lines = [
        f'azure_location = "{config.get("azure_location", "eastus")}"',
        f'resource_group_name = "{config.get("resource_group_name", "zenith-rg")}"',
        f'storage_account_name = "{config.get("storage_account_name", "")}"',
        f'container_name = "{config.get("container_name", "zenith-static")}"',
        "",
        f'enable_azure_storage = {str(config.get("enable_azure_storage", False)).lower()}',
        "",
        "tags = {",
    ]
    for key, value in config.get("tags", {}).items():
        lines.append(f'  {key} = "{value}"')
    lines.append("}")
    lines.append("")
    tfvars_path = Path(workspace_dir) / "terraform.tfvars"
    tfvars_path.write_text("\n".join(lines), encoding="utf-8")
    return str(tfvars_path)
