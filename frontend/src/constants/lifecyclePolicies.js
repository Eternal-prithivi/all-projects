export const LIFECYCLE_POLICIES = [
  {
    id: "auto",
    label: "Auto-optimize (recommended)",
    description:
      "Zenith notifies you before moving unused files to cheaper storage. Moves after your notice period.",
  },
  {
    id: "keep_hot",
    label: "Keep fast access",
    description: "No automatic demotion. Best for active projects and frequently used data.",
  },
  {
    id: "aggressive",
    label: "Archive aggressively",
    description: "Shorter inactivity windows before demotion. Maximizes savings on archival data.",
  },
  {
    id: "manual",
    label: "Suggest only",
    description: "No automatic moves. Zenith sends savings suggestions you can act on manually.",
  },
];

export const lifecyclePolicyLabel = (id) =>
  LIFECYCLE_POLICIES.find((p) => p.id === id)?.label || id;
