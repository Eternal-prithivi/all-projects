import React from 'react';
import '../styles/org-resource-meta.css';

/**
 * Subtitle for org-owned resources on VM, storage, and provision cards.
 */
export default function OrgResourceMeta({ orgName, createdBy, currentUsername }) {
  if (!orgName && !createdBy) return null;

  const createdLabel =
    createdBy &&
    (createdBy === currentUsername ? 'Created by you' : `Created by ${createdBy}`);

  return (
    <p className="org-resource-meta">
      {orgName && <span>Organization: {orgName}</span>}
      {orgName && createdLabel && <span className="org-resource-meta__sep"> · </span>}
      {createdLabel && <span>{createdLabel}</span>}
    </p>
  );
}
