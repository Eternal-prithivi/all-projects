import React from "react";
import ZenithModal from "../ui/ZenithModal.jsx";
import VmCostPreview from "./VmCostPreview.jsx";
import { IconHardDrive } from "../dashboard/Icons.jsx";

function getCPUColor(cpuUsage) {
  if (cpuUsage > 70) return "var(--danger)";
  if (cpuUsage > 50) return "var(--warning)";
  return "var(--success)";
}

export default function VmConfigModal({ open, config, onClose }) {
  if (!config) return null;

  const title = config.display_name
    ? `${config.display_name} (${config.vm_name})`
    : `VM configuration: ${config.vm_name}`;

  return (
    <ZenithModal
      open={open}
      onClose={onClose}
      title={title}
      titleId="vm-config-modal-title"
      large
      footer={
        <button className="btn-cancel" type="button" onClick={onClose}>
          Close
        </button>
      }
    >
      <div className="vm-config-details">
        <div className="config-section">
          <h4>Basic Information</h4>
          <div className="config-grid">
            <div className="config-item">
              <span className="config-label">VM Name:</span>
              <span className="config-value">{config.vm_name}</span>
            </div>
            <div className="config-item">
              <span className="config-label">Status:</span>
              <span className={`cluster-badge ${(config.status || "").toLowerCase()}`}>
                {config.status}
              </span>
            </div>
            <div className="config-item">
              <span className="config-label">Cluster:</span>
              <span className={`cluster-badge ${(config.cluster_type || "").toLowerCase()}`}>
                {config.cluster_type}
              </span>
            </div>
            {config.tier_label && (
              <div className="config-item">
                <span className="config-label">Tier:</span>
                <span className="config-value">{config.tier_label}</span>
              </div>
            )}
            <div className="config-item">
              <span className="config-label">CSP:</span>
              <span className="config-value">{config.csp}</span>
            </div>
            <div className="config-item">
              <span className="config-label">Region / Zone:</span>
              <span className="config-value">{config.region || config.zone || "N/A"}</span>
            </div>
          </div>
        </div>

        <div className="config-section">
          <h4>Compute Resources</h4>
          <div className="config-grid">
            <div className="config-item">
              <span className="config-label">Machine Type:</span>
              <span className="config-value">{config.machine_type}</span>
            </div>
            <div className="config-item">
              <span className="config-label">CPU Cores:</span>
              <span className="config-value">{config.cpu_cores ?? config.vcpu ?? "—"} vCPUs</span>
            </div>
            <div className="config-item">
              <span className="config-label">Memory:</span>
              <span className="config-value">{config.memory_gb ?? "—"} GB</span>
            </div>
            <div className="config-item">
              <span className="config-label">Active Users:</span>
              <span className="config-value">{config.active_users ?? 0}</span>
            </div>
          </div>
        </div>

        <div className="config-section">
          <h4>Storage Configuration</h4>
          <div className="config-grid">
            <div className="config-item">
              <span className="config-label">Total Disk:</span>
              <span className="config-value">{config.total_disk_gb ?? "—"} GB</span>
            </div>
            <div className="config-item">
              <span className="config-label">Number of Disks:</span>
              <span className="config-value">{config.disks?.length || 0}</span>
            </div>
          </div>
          {config.disks?.map((disk, index) => (
            <div key={index} className="disk-detail">
              <span className="disk-icon">
                <IconHardDrive aria-hidden="true" />
              </span>
              <span className="disk-name">{disk.name}</span>
              <span className="disk-size">{disk.size_gb} GB</span>
              <span className="disk-type">{disk.type}</span>
            </div>
          ))}
        </div>

        {config.networks?.length > 0 && (
          <div className="config-section">
            <h4>Network Configuration</h4>
            {config.networks.map((network, index) => (
              <div key={index} className="network-detail">
                <div className="config-item">
                  <span className="config-label">Network:</span>
                  <span className="config-value">{network.network}</span>
                </div>
                <div className="config-item">
                  <span className="config-label">Internal IP:</span>
                  <span className="config-value">{network.internal_ip}</span>
                </div>
                {network.external_ip && (
                  <div className="config-item">
                    <span className="config-label">External IP:</span>
                    <span className="config-value">{network.external_ip}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {config.current_metrics && (
          <div className="config-section">
            <h4>Current Metrics</h4>
            <div className="config-grid">
              <div className="config-item">
                <span className="config-label">CPU Usage:</span>
                <span
                  className="config-value"
                  style={{ color: getCPUColor(config.current_metrics.cpu_usage) }}
                >
                  {config.current_metrics.cpu_usage.toFixed(1)}%
                </span>
              </div>
              <div className="config-item">
                <span className="config-label">Memory Usage:</span>
                <span className="config-value">
                  {config.current_metrics.memory_usage.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {config.intended_spec && config.status === "NOT_PROVISIONED" && (
          <div className="config-section config-section--catalog">
            <h4>Intended Configuration (catalog)</h4>
            <p className="vm-request-field-hint">
              This slot is not provisioned yet. Values below reflect the catalog spec for this tier.
            </p>
            <div className="config-grid">
              <div className="config-item">
                <span className="config-label">Machine:</span>
                <span className="config-value">
                  {config.intended_spec.machine_type}
                </span>
              </div>
              <div className="config-item">
                <span className="config-label">Disk:</span>
                <span className="config-value">{config.intended_spec.disk_gb} GB</span>
              </div>
            </div>
            {config.cost_estimate && (
              <VmCostPreview estimate={config.cost_estimate} compact />
            )}
          </div>
        )}

        {config.cost_estimate && config.status !== "NOT_PROVISIONED" && (
          <div className="config-section">
            <h4>Estimated running cost</h4>
            <VmCostPreview estimate={config.cost_estimate} compact />
          </div>
        )}
      </div>
    </ZenithModal>
  );
}
