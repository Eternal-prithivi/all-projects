export const SECURITY_ENCRYPTION_OPTIONS = [
  { value: "ask", label: "Ask me each time" },
  { value: "server-side", label: "Cloud-managed (default)" },
  { value: "client-side", label: "Browser encryption" },
];

export function securityEncryptionLabel(value) {
  return SECURITY_ENCRYPTION_OPTIONS.find((o) => o.value === value)?.label || value;
}

export const VAULT_STATUS_LABELS = {
  active: "Active",
  archived: "Archived",
  all: "All files",
};
