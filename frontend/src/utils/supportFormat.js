export function statusLabel(status) {
  return (status || '').replace(/_/g, ' ');
}

export function formatDateTime(value) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

export function formatRelativeTime(value) {
  if (!value) return '';
  const date = new Date(value);
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

export function canReplyToTicket(ticket) {
  if (!ticket) return false;
  return ticket.status !== 'closed' && ticket.status !== 'resolved';
}
