import React from 'react';
import { formatRelativeTime } from '../../utils/supportFormat.js';

export default function SupportMessageBubble({ message, pending = false }) {
  const type = message.author_type || 'customer';
  return (
    <div
      className={`support-bubble support-bubble--${type} ${pending ? 'support-bubble--pending' : ''}`}
    >
      <div className="support-bubble-meta">
        {message.author_name}
        {!pending && message.created_at && (
          <> · {formatRelativeTime(message.created_at)}</>
        )}
        {pending && <> · sending…</>}
      </div>
      <div className="support-bubble-body">{message.body}</div>
    </div>
  );
}
