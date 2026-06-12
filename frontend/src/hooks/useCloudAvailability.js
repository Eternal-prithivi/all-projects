import {
  useCloudAvailabilityContext,
  CloudAvailabilityProvider,
} from "../context/CloudAvailabilityContext.jsx";

export { CloudAvailabilityProvider };

/**
 * Canonical display labels for CSP selectors (AWS | GCP | Azure).
 */
export const CSP_LABELS = {
  AWS: "AWS",
  GCP: "Google Cloud",
  Azure: "Azure",
};

/** Lowercase keys for Cost API routes */
export const CSP_TO_COST_KEY = {
  AWS: "aws",
  GCP: "gcp",
  Azure: "azure",
};

export const COST_KEY_TO_CSP = {
  aws: "AWS",
  gcp: "GCP",
  azure: "Azure",
};

/**
 * Build select options for CloudProviderToolbar.
 */
export function buildCloudProviderOptions(providers = [], opts = {}) {
  const { includeAll = true, allLabel = "All connected" } = opts;
  const list = Array.isArray(providers) ? providers : [];
  const options = [];
  if (includeAll && list.length > 1) {
    options.push({ value: "ALL", label: allLabel });
  }
  for (const p of list) {
    options.push({ value: p, label: CSP_LABELS[p] || p });
  }
  return options;
}

/**
 * Pick a valid provider when the current selection is no longer allowed.
 */
export function coerceCloudProvider(current, providers, { allowAll = true } = {}) {
  const list = providers || [];
  if (!list.length) return null;
  if (list.length === 1) return list[0];
  if (allowAll && current === "ALL") return "ALL";
  if (list.includes(current)) return current;
  return list[0];
}

/** Shared cloud availability — one fetch per dashboard session (cached). */
export function useCloudAvailability() {
  return useCloudAvailabilityContext();
}

export { default as CloudProviderToolbar } from "../components/CloudProviderSelect.jsx";
