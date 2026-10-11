import React from 'react';

export const ModerationHistoryTable = ({ history }) => {
  if (!history.length) {
    return null;
  }

  return (
    <div className="table-responsive" role="region" aria-label="My moderation history table" tabIndex={0}>
      <table className="table" aria-label="My moderation history">
        <caption className="sr-only">Your moderation predictions, confidence, recommendations, and final statuses.</caption>
        <thead>
          <tr>
            <th scope="col">When</th>
            <th scope="col">Type</th>
            <th scope="col">Category</th>
            <th scope="col">Confidence</th>
            <th scope="col">Recommendation</th>
            <th scope="col">Final status</th>
            <th scope="col">Human review</th>
          </tr>
        </thead>
        <tbody>
          {history.map((entry, idx) => (
            <tr key={`${entry.content_type}-${entry.content_id}-${entry.timestamp}-${idx}`}>
              <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '—'}
              </td>
              <td>{entry.content_type}</td>
              <td>{entry.ai_label}</td>
              <td>{entry.confidence != null ? `${Math.round(entry.confidence * 100)}%` : '—'}</td>
              <td>{entry.recommendation || '—'}</td>
              <td>
                <span className="badge badge-flagged" aria-label={`Status ${entry.action_taken}`}>
                  {entry.action_taken}
                </span>
              </td>
              <td style={{ fontSize: '0.85rem' }}>
                {entry.human_review?.reviewed_at
                  ? `${entry.human_review.review_action || 'Reviewed'}`
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
