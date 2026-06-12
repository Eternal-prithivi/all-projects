import React from "react";
import { clusterBadgeClass } from "../../constants/vmClusters.js";

export default function ClusterSelector({
  clusters = [],
  selectedCluster,
  onSelect,
  className = "",
}) {
  if (!clusters.length) return null;

  return (
    <div
      className={`vm-segmented-control ${className}`.trim()}
      role="tablist"
      aria-label="VM clusters"
    >
      {clusters.map((cluster) => {
        const slug = cluster.cluster_type;
        const isActive = selectedCluster === slug;
        return (
          <button
            key={slug}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`vm-segmented-control__item ${
              isActive ? "vm-segmented-control__item--active" : ""
            }`}
            onClick={() => onSelect(slug)}
          >
            <span
              className={`vm-segmented-control__dot vm-segmented-control__dot--${clusterBadgeClass(slug, clusters)}`}
              aria-hidden="true"
            />
            {cluster.label || slug}
          </button>
        );
      })}
    </div>
  );
}
