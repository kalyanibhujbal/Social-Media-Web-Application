import React from 'react';

export const AdminModerationHistory = ({ history }) => {
  if (!history.length) {
    return <p style={{ color: '#94a3b8' }} role="status">No moderation history recorded yet.</p>;
  }

  return (
    <div className="table-responsive" role="region" aria-label="System moderation history table" tabIndex={0}>
      <table className="table" aria-label="System moderation history">
        <caption className="sr-only">Moderation classifications, decisions, and human review timestamps.</caption>
        <thead>
          <tr>
            <th scope="col">Timestamp</th>
            <th scope="col">Content type</th>
            <th scope="col">Content ID</th>
            <th scope="col">AI label</th>
            <th scope="col">Confidence</th>
            <th scope="col">Action</th>
            <th scope="col">Human review</th>
          </tr>
        </thead>
        <tbody>
          {history.map((row, idx) => (
            <tr key={`${row.content_type}-${row.content_id}-${row.timestamp}-${idx}`}>
              <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                {row.timestamp ? new Date(row.timestamp).toLocaleString() : '—'}
              </td>
              <td>{row.content_type || 'post'}</td>
              <td style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}>{row.content_id?.slice(0, 8)}…</td>
              <td>{row.ai_label}</td>
              <td>{row.confidence != null ? `${Math.round(row.confidence * 100)}%` : '—'}</td>
              <td>{row.action_taken}</td>
              <td style={{ fontSize: '0.85rem' }}>
                {row.human_review?.review_action || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
