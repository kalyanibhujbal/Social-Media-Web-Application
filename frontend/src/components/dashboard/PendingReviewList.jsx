import React from 'react';

export const PendingReviewList = ({ items }) => {
  if (!items.length) {
    return (
      <p style={{ color: '#94a3b8' }} role="status">
        No items pending manual review.
      </p>
    );
  }

  return (
    <ul className="pending-review-list" aria-label="Items pending review">
      {items.map((item) => (
        <li key={`${item.type}-${item.id}`} className="card" style={{ padding: '1rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
            <span className="badge badge-flagged" aria-label={`Type: ${item.type}`}>
              {item.type === 'post' ? 'Post' : 'Comment'}
            </span>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              {item.prediction_label} · {item.confidence != null ? `${Math.round(item.confidence * 100)}%` : '—'}
            </span>
          </div>
          <p style={{ marginTop: '0.5rem', color: '#e2e8f0' }}>{item.content_preview}</p>
          <p style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
            Status: <strong>{item.moderation_status}</strong>
          </p>
        </li>
      ))}
    </ul>
  );
};
