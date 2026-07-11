"""Azure Linux VM SDK module."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceNotFoundError

from app.provision.provision_config_options import (
    AZURE_IDENTITY_PRESETS,
    azure_custom_data,
    azure_image_reference,
    normalize_azure_identity_preset,
    normalize_azure_os,
    plan_azure_identity_preset_summary,
)
from app.provision.sdk_clients import azure_compute_client, azure_credential_and_subscription, azure_network_client
from app.provision.sdk_modules.azure_rbac import assign_storage_blob_role
from app.provision.sdk_modules.azure_resource_group import azure_effective_location, ensure_resource_group
from app.provision.sdk_modules.azure_vm_sizes import (
    azure_vm_sizes_for_deploy,
    format_no_vm_capacity_error,
)
from app.provision.sdk_modules.common import (
    azure_tags,
    disk_gb,
    is_azure_sku_capacity_error,
    is_azure_vm_architecture_error,
)
from app.provision.sdk_modules.context import SdkDeployContext
from app.vm.azure_cleanup import (
    cleanup_vm_attached_resources,
    collect_managed_disk_ids,
    os_disk_profile,
)
from app.vm.ssh_manager import generate_ssh_keypair

VNET_NAME = "zenith-vnet"
SUBNET_NAME = "zenith-subnet"

# Basic SKU public IPs are blocked (quota 0) on many free/student subscriptions.
AZURE_PUBLIC_IP_SKU = "Standard"


def azure_public_ip_params(location: str) -> dict[str, Any]:
    return {
        "location": location,
        "sku": {"name": AZURE_PUBLIC_IP_SKU},
        "public_ip_allocation_method": "Static",
        "public_ip_address_version": "IPv4",
    }


def plan_azure_vm(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    name = config.get("instance_name") or "zenith-linux-vm"
    size = config.get("vm_size") or "Standard_B1s"
    os_key = normalize_azure_os(config.get("azure_os"))
    preset = plan_azure_identity_preset_summary(config.get("azure_identity_preset", "storage_blob_read"))
    lines = [
        f"  + azurerm_public_ip.{name}-pip ({AZURE_PUBLIC_IP_SKU} SKU)",
        f"  + azurerm_network_interface.{name}-nic",
        f"  + azurerm_linux_virtual_machine.{name} ({size}, {os_key})",
        f"  + system-assigned managed identity ({preset})",
    ]
    if (config.get("azure_startup_script") or "").strip():
        lines.append("  + os_profile.custom_data (startup script)")
    return {"lines": lines, "error": None, "resources": [f"vm:{name}"]}


def apply_azure_vm(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    ok, steps, err = ensure_resource_group(config, cloud_env, ctx)
    if not ok:
        return {"success": False, "steps": steps, "error": err}
    if not ctx.vnet_name and not ctx.subnet_name:
        return {"success": False, "steps": steps, "error": "Azure VM requires VNet (enable vnet)."}

    rg = ctx.azure_resource_group
    location = azure_effective_location(config, ctx)
    name = (config.get("instance_name") or "zenith-linux-vm").strip()
    vm_size = config.get("vm_size") or "Standard_B1s"
    disk = disk_gb(config)
    network_client, _, _ = azure_network_client(cloud_env)
    compute_client, _, _ = azure_compute_client(cloud_env)
    vnet = ctx.vnet_name or VNET_NAME
    subnet = ctx.subnet_name or SUBNET_NAME

    identity_preset = normalize_azure_identity_preset(config.get("azure_identity_preset"))
    preset_meta = AZURE_IDENTITY_PRESETS[identity_preset]
    custom_data = azure_custom_data(config.get("azure_startup_script"), config.get("azure_os"))
    image_ref = azure_image_reference(config.get("azure_os"))

    try:
        pip_name = f"{name}-pip"
        nic_name = f"{name}-nic"
        vm_resource = None
        try:
            vm_resource = compute_client.virtual_machines.get(rg, name)
            steps.append(f"✓ VM '{name}' already exists")
        except ResourceNotFoundError:
            try:
                pip = network_client.public_ip_addresses.get(rg, pip_name)
                steps.append(f"✓ Public IP '{pip_name}' already exists")
            except ResourceNotFoundError:
                pip = network_client.public_ip_addresses.begin_create_or_update(
                    rg,
                    pip_name,
                    azure_public_ip_params(location),
                ).result()
                steps.append(f"✓ Public IP '{pip_name}' ({AZURE_PUBLIC_IP_SKU})")

            subnet_ref = network_client.subnets.get(rg, vnet, subnet)
            try:
                nic = network_client.network_interfaces.get(rg, nic_name)
                steps.append(f"✓ NIC '{nic_name}' already exists")
            except ResourceNotFoundError:
                nic = network_client.network_interfaces.begin_create_or_update(
                    rg,
                    nic_name,
                    {
                        "location": location,
                        "ip_configurations": [
                            {
                                "name": "internal",
                                "subnet": {"id": subnet_ref.id},
                                "private_ip_allocation_method": "Dynamic",
                                "public_ip_address": {"id": pip.id},
                            }
                        ],
                    },
                ).result()
                steps.append(f"✓ NIC '{nic_name}'")

            private_key, public_key = generate_ssh_keypair()
            ctx.ssh_private_key_pem = private_key

            os_profile: dict[str, Any] = {
                "computer_name": name.replace("-", "")[:15] or "zenithvm",
                "admin_username": "zenithadmin",
                "linux_configuration": {
                    "disable_password_authentication": True,
                    "ssh": {
                        "public_keys": [
                            {
                                "path": "/home/zenithadmin/.ssh/authorized_keys",
                                "key_data": public_key,
                            }
                        ]
                    },
                },
            }
            if custom_data:
                os_profile["custom_data"] = custom_data

            vm_params: dict[str, Any] = {
                "location": location,
                "tags": azure_tags(config.get("tags")),
                "identity": {"type": "SystemAssigned"},
                "hardware_profile": {"vm_size": vm_size},
                "storage_profile": {
                    "image_reference": image_ref,
                    "os_disk": os_disk_profile(disk, "Standard_LRS", name),
                },
                "os_profile": os_profile,
                "network_profile": {
                    "network_interfaces": [{"id": nic.id, "properties": {"primary": True}}]
                },
            }
            launched_size: str | None = None
            sizes_to_try = azure_vm_sizes_for_deploy(compute_client, location, vm_size)
            if len(sizes_to_try) > len({vm_size}):
                steps.append(
                    f"Checking {len(sizes_to_try)} x64 VM sizes available in {location}…"
                )
            for candidate_size in sizes_to_try:
                vm_params["hardware_profile"]["vm_size"] = candidate_size
                try:
                    vm_resource = compute_client.virtual_machines.begin_create_or_update(
                        rg, name, vm_params
                    ).result()
                    launched_size = candidate_size
                    break
                except Exception as exc:
                    if is_azure_sku_capacity_error(exc):
                        steps.append(
                            f"⚠ {candidate_size} unavailable in {location} (capacity)"
                        )
                        last_capacity_error = exc
                        continue
                    if is_azure_vm_architecture_error(exc):
                        steps.append(
                            f"⚠ {candidate_size} skipped (Arm64-only; OS image is x64)"
                        )
                        continue
                    raise
            else:
                cleanup_vm_attached_resources(
                    compute_client,
                    network_client,
                    rg,
                    name,
                    delete_vm_if_present=True,
                )
                return {
                    "success": False,
                    "steps": steps,
                    "error": format_no_vm_capacity_error(location, sizes_to_try),
                }

            ctx.launched_vm_size = launched_size or vm_size
            os_label = normalize_azure_os(config.get("azure_os"))
            size_note = launched_size or vm_size
            if launched_size and launched_size != vm_size:
                size_note = f"{launched_size} (requested {vm_size})"
            steps.append(f"✓ Linux VM '{name}' ({size_note}, {disk}GB, {os_label})")
            if custom_data:
                steps.append("✓ Startup script attached (custom_data)")
            steps.append(f"✓ System-assigned managed identity ({preset_meta['label']})")

        if vm_resource is None:
            vm_resource = compute_client.virtual_machines.get(rg, name)
        principal_id = ""
        if vm_resource.identity and vm_resource.identity.principal_id:
            principal_id = vm_resource.identity.principal_id
            ctx.azure_vm_principal_id = principal_id

        storage_account = (ctx.azure_storage_account or config.get("storage_account_name") or "").strip()
        role_id = (preset_meta.get("role_id") or "").strip()
        if (
            principal_id
            and role_id
            and identity_preset in ("storage_blob_read", "storage_blob_contributor")
            and storage_account
        ):
            credential, subscription_id = azure_credential_and_subscription(cloud_env)
            assign_storage_blob_role(
                credential,
                subscription_id,
                rg,
                storage_account,
                role_id,
                principal_id,
                steps,
                preset_meta["role_name"],
            )
        elif identity_preset in ("storage_blob_read", "storage_blob_contributor") and not storage_account:
            steps.append("⚠ Storage RBAC skipped — enable Azure Storage or set storage account name.")

        ctx.vm_name = name
        ctx.nic_name = nic_name
        ctx.public_ip_name = pip_name
        try:
            pip = network_client.public_ip_addresses.get(rg, pip_name)
            ctx.vm_public_ip = pip.ip_address or ""
        except Exception:
            ctx.vm_public_ip = ""
        ip_note = f" ({ctx.vm_public_ip})" if ctx.vm_public_ip else ""
        if steps and ip_note and "already" not in steps[-1]:
            steps[-1] = steps[-1] + ip_note
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        cleanup_vm_attached_resources(
            compute_client,
            network_client,
            rg,
            name,
            delete_vm_if_present=True,
        )
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_azure_vm(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    name = ctx.vm_name or config.get("instance_name") or "zenith-linux-vm"
    compute_client, _, _ = azure_compute_client(cloud_env)
    network_client, _, _ = azure_network_client(cloud_env)
    steps: list[str] = []
    try:
        vm = None
        disk_ids: list[str] = []
        try:
            vm = compute_client.virtual_machines.get(rg, name)
            disk_ids = collect_managed_disk_ids(vm)
        except ResourceNotFoundError:
            pass

        if vm:
            compute_client.virtual_machines.begin_delete(
                rg,
                name,
                force_deletion=True,
            ).result()
            steps.append(f"✓ Deleted VM '{name}'")

        cleanup = cleanup_vm_attached_resources(
            compute_client,
            network_client,
            rg,
            name,
            extra_disk_ids=disk_ids,
        )
        if cleanup.get("nic_deleted"):
            steps.append(f"✓ Deleted NIC '{name}-nic'")
        if cleanup.get("pip_deleted"):
            steps.append(f"✓ Deleted public IP '{name}-pip'")
        if cleanup.get("disks_deleted"):
            steps.append(f"✓ Deleted managed disk(s) for '{name}'")

        return {"success": True, "steps": steps or ["Azure VM: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_azure_vm_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    name = ctx.vm_name or config.get("instance_name") or "zenith-linux-vm"
    compute_client, _, _ = azure_compute_client(cloud_env)
    try:
        compute_client.virtual_machines.get(rg, name)
        return 0, []
    except ResourceNotFoundError:
        return 1, [f"~ Azure VM '{name}' missing"]
    except Exception as exc:
        return 1, [f"~ Azure VM check failed: {exc}"]
