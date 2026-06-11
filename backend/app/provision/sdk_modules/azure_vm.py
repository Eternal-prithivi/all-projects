"""Azure Linux VM SDK module."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceNotFoundError

from app.provision.sdk_clients import azure_compute_client, azure_network_client
from app.provision.sdk_modules.azure_resource_group import ensure_resource_group
from app.provision.sdk_modules.common import azure_tags, disk_gb
from app.provision.sdk_modules.context import SdkDeployContext
from app.vm.ssh_manager import generate_ssh_keypair

VNET_NAME = "zenith-vnet"
SUBNET_NAME = "zenith-subnet"


def plan_azure_vm(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    name = config.get("instance_name") or "zenith-linux-vm"
    size = config.get("vm_size") or "Standard_B1s"
    lines = [
        f"  + azurerm_public_ip.{name}-pip",
        f"  + azurerm_network_interface.{name}-nic",
        f"  + azurerm_linux_virtual_machine.{name} ({size})",
    ]
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
    location = config.get("azure_location") or "eastus"
    name = (config.get("instance_name") or "zenith-linux-vm").strip()
    vm_size = config.get("vm_size") or "Standard_B1s"
    disk = disk_gb(config)
    network_client, _, _ = azure_network_client(cloud_env)
    compute_client, _, _ = azure_compute_client(cloud_env)
    vnet = ctx.vnet_name or VNET_NAME
    subnet = ctx.subnet_name or SUBNET_NAME

    try:
        pip_name = f"{name}-pip"
        nic_name = f"{name}-nic"
        try:
            compute_client.virtual_machines.get(rg, name)
            steps.append(f"✓ VM '{name}' already exists")
        except ResourceNotFoundError:
            pip_poller = network_client.public_ip_addresses.begin_create_or_update(
                rg,
                pip_name,
                {
                    "location": location,
                    "sku": {"name": "Basic"},
                    "public_ip_allocation_method": "Static",
                },
            )
            pip = pip_poller.result()

            subnet_ref = network_client.subnets.get(rg, vnet, subnet)
            nic_poller = network_client.network_interfaces.begin_create_or_update(
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
            )
            nic = nic_poller.result()

            private_key, public_key = generate_ssh_keypair()
            ctx.ssh_private_key_pem = private_key

            vm_params = {
                "location": location,
                "tags": azure_tags(config.get("tags")),
                "hardware_profile": {"vm_size": vm_size},
                "storage_profile": {
                    "image_reference": {
                        "publisher": "Canonical",
                        "offer": "0001-com-ubuntu-server-jammy",
                        "sku": "22_04-lts",
                        "version": "latest",
                    },
                    "os_disk": {
                        "create_option": "FromImage",
                        "disk_size_gb": disk,
                        "managed_disk": {"storage_account_type": "Standard_LRS"},
                    },
                },
                "os_profile": {
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
                },
                "network_profile": {
                    "network_interfaces": [{"id": nic.id, "properties": {"primary": True}}]
                },
            }
            compute_client.virtual_machines.begin_create_or_update(rg, name, vm_params).result()
            steps.append(f"✓ Linux VM '{name}' ({vm_size}, {disk}GB)")

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
        try:
            compute_client.virtual_machines.begin_delete(rg, name).result()
            steps.append(f"✓ Deleted VM '{name}'")
        except ResourceNotFoundError:
            pass
        for res_name in (ctx.nic_name, ctx.public_ip_name):
            if not res_name:
                continue
            try:
                if "nic" in res_name:
                    network_client.network_interfaces.begin_delete(rg, res_name).result()
                else:
                    network_client.public_ip_addresses.begin_delete(rg, res_name).result()
                steps.append(f"✓ Deleted '{res_name}'")
            except ResourceNotFoundError:
                pass
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
