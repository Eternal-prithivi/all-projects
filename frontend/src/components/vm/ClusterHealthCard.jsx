import React from "react";

export default function ClusterHealthCard({ health, clusterLabel, getCPUColor }) {
  if (!health) {
    return (
      <div className="vm-health-card vm-health-card--empty">
        <p>No telemetry for {clusterLabel || "this cluster"} yet.</p>
      </div>
    );
  }

  return (
    <div className="vm-health-card">
      <div className="vm-health-card__metrics">
        <div className="vm-stat-tile">
          <span className="vm-stat-tile__label">Running instances</span>
          <span className="vm-stat-tile__value">
            {health.running_vms}
            <span className="vm-stat-tile__suffix">/ {health.total_vms}</span>
          </span>
        </div>
        <div className="vm-stat-tile">
          <span className="vm-stat-tile__label">Active users</span>
          <span className="vm-stat-tile__value">{health.total_active_users}</span>
        </div>
        <div className="vm-stat-tile">
          <span className="vm-stat-tile__label">Average CPU</span>
          <span
            className="vm-stat-tile__value"
            style={{ color: getCPUColor(health.average_cpu_usage) }}
          >
            {health.average_cpu_usage.toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="vm-health-table-wrap">
        <table className="vm-health-table data-card-table">
          <thead>
            <tr>
              <th scope="col">Instance</th>
              <th scope="col">Status</th>
              <th scope="col">CPU</th>
              <th scope="col">Users</th>
            </tr>
          </thead>
          <tbody>
            {(health.vms || []).map((vm) => (
              <tr key={vm.vm_name}>
                <td className="vm-health-table__name" data-label="Instance">{vm.vm_name}</td>
                <td data-label="Status">
                  <span className={`vm-status-pill ${(vm.status || "").toLowerCase()}`}>
                    {vm.status}
                  </span>
                </td>
                <td data-label="CPU">{vm.cpu_usage.toFixed(1)}%</td>
                <td data-label="Users">{vm.active_users}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
