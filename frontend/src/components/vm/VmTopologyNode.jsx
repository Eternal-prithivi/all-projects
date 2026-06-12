import React from "react";

const SERVER_ICON = (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M4 1h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm1 2v2h2V3H5zm3 0v2h2V3H8zm-4 6h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm1 2v2h2v-2H5zm3 0v2h2v-2H8zm-4 6h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm1 2v2h2v-2H5zm3 0v2h2v-2H8z" />
  </svg>
);

export default function VmTopologyNode({ vm, tierLabel, onClick }) {
  const status = (vm?.status || "unknown").toLowerCase();

  return (
    <button
      type="button"
      className={`topology-square__vm vm-server ${status}`}
      onClick={() => onClick?.(vm?.vm_name)}
      title={vm?.vm_name}
      aria-label={`${tierLabel || vm?.vm_name} — ${vm?.status || "unknown"}`}
    >
      <div className="server-icon">{SERVER_ICON}</div>
      {tierLabel && <div className="topology-square__tier">{tierLabel}</div>}
      <div className="vm-name-label">{vm?.vm_name}</div>
      <div className="vm-status-indicator">{vm?.status || "unknown"}</div>
    </button>
  );
}
