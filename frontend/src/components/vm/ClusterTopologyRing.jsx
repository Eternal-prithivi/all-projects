import React, { useMemo } from "react";
import VmTopologyNode from "./VmTopologyNode.jsx";

/** Clockwise from top-left: vm-1 → vm-2 → vm-3 → vm-4 → vm-1 */
const CORNER_ORDER = ["tl", "tr", "br", "bl"];

function ConnectionWire({ orientation = "vertical", active = false }) {
  return (
    <div
      className={`connection-wire connection-wire--${orientation} ${
        active ? "active" : "inactive"
      }`}
      aria-hidden="true"
    />
  );
}

function mergeNodes(vms, slotTiers) {
  const slots =
    slotTiers.length >= 4
      ? slotTiers
      : Array.from({ length: 4 }, (_, i) => slotTiers[i] || null);

  return CORNER_ORDER.map((corner, index) => {
    const slot = slots[index];
    const vmName = slot?.vm_name;
    const health = vmName
      ? vms.find((v) => v.vm_name === vmName)
      : vms[index];
    return {
      vm_name: vmName || health?.vm_name || `slot-${index + 1}`,
      status: health?.status || "NOT_PROVISIONED",
      tierLabel: slot?.tier_label || slot?.tier || null,
      corner,
    };
  });
}

export default function ClusterTopologyRing({
  clusterLabel,
  vms = [],
  runningVms = 0,
  onVmClick,
  slotTiers = [],
}) {
  const nodes = useMemo(() => mergeNodes(vms, slotTiers), [vms, slotTiers]);
  const edgeActive = runningVms > 0;
  const [topLeft, topRight, bottomRight, bottomLeft] = nodes;

  return (
    <div className="topology-square-wrap">
      {clusterLabel && <div className="cluster-label">{clusterLabel}</div>}
      <div
        className="topology-square"
        role="list"
        aria-label={`${clusterLabel} cluster topology`}
      >
        <div className="topology-square__cell topology-square__cell--tl" role="listitem">
          <VmTopologyNode vm={topLeft} tierLabel={topLeft.tierLabel} onClick={onVmClick} />
        </div>
        <div className="topology-square__cell topology-square__cell--wire-top">
          <ConnectionWire orientation="horizontal" active={edgeActive} />
        </div>
        <div className="topology-square__cell topology-square__cell--tr" role="listitem">
          <VmTopologyNode vm={topRight} tierLabel={topRight.tierLabel} onClick={onVmClick} />
        </div>

        <div className="topology-square__cell topology-square__cell--wire-left">
          <ConnectionWire orientation="vertical" active={edgeActive} />
        </div>
        <div className="topology-square__cell topology-square__cell--hub" aria-hidden="true">
          <div className="topology-square__hub">
            <span className="topology-square__hub-label">Ring</span>
          </div>
        </div>
        <div className="topology-square__cell topology-square__cell--wire-right">
          <ConnectionWire orientation="vertical" active={edgeActive} />
        </div>

        <div className="topology-square__cell topology-square__cell--bl" role="listitem">
          <VmTopologyNode vm={bottomLeft} tierLabel={bottomLeft.tierLabel} onClick={onVmClick} />
        </div>
        <div className="topology-square__cell topology-square__cell--wire-bottom">
          <ConnectionWire orientation="horizontal" active={edgeActive} />
        </div>
        <div className="topology-square__cell topology-square__cell--br" role="listitem">
          <VmTopologyNode vm={bottomRight} tierLabel={bottomRight.tierLabel} onClick={onVmClick} />
        </div>
      </div>
    </div>
  );
}
