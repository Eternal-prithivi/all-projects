/** Fallback cluster metadata when /api/vm/clusters is unavailable. */

export const VM_CLUSTER_SLUGS = [
  "general",
  "storage",
  "memory",
  "performance",
  "ai_ml",
  "database",
  "network",
];

export const VM_CLUSTER_FALLBACK = [
  { cluster_type: "general", label: "General", badge_class: "general" },
  { cluster_type: "storage", label: "Storage", badge_class: "storage" },
  { cluster_type: "memory", label: "Memory", badge_class: "memory" },
  { cluster_type: "performance", label: "Performance", badge_class: "performance" },
  { cluster_type: "ai_ml", label: "AI/ML", badge_class: "ai_ml" },
  { cluster_type: "database", label: "Database", badge_class: "database" },
  { cluster_type: "network", label: "Network", badge_class: "network" },
];

export function formatClusterLabel(slug) {
  const meta = VM_CLUSTER_FALLBACK.find((c) => c.cluster_type === slug);
  if (meta) return meta.label;
  return String(slug || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function clusterBadgeClass(slug, catalog = VM_CLUSTER_FALLBACK) {
  const meta = catalog.find((c) => c.cluster_type === slug);
  return meta?.badge_class || String(slug || "general").toLowerCase();
}
