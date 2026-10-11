import React from 'react';
import { ModerationBadge } from '../moderation/ModerationBadge';

export const UserCommentList = ({ comments }) => {
  if (!comments.length) {
    return (
      <p style={{ color: '#94a3b8' }} role="status">
        You have not submitted any comments yet.
      </p>
    );
  }

  return (
    <div className="table-responsive" role="region" aria-label="My comments table" tabIndex={0}>
      <table className="table" aria-label="My comments moderation status">
        <caption className="sr-only">Your comments and their moderation classifications and statuses.</caption>
        <thead>
          <tr>
            <th scope="col">Comment</th>
            <th scope="col">Prediction</th>
            <th scope="col">Confidence</th>
            <th scope="col">Status</th>
            <th scope="col">Submitted</th>
          </tr>
        </thead>
        <tbody>
          {comments.map((comment) => (
            <tr key={comment.id}>
              <td style={{ maxWidth: '280px' }}>{comment.content}</td>
              <td>{comment.ai_prediction?.label || '—'}</td>
              <td>
                {comment.ai_prediction?.confidence != null
                  ? `${Math.round(comment.ai_prediction.confidence * 100)}%`
                  : '—'}
              </td>
              <td>
                <ModerationBadge prediction={comment.ai_prediction} status={comment.moderation_status} />
              </td>
              <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                {new Date(comment.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
