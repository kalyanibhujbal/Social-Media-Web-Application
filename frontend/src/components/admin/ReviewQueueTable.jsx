import React, { useState } from 'react';
import { api } from '../../services/api';
import { ContentReviewPanel } from './ContentReviewPanel';

const CONFIRMATION_ACTIONS = new Set(['APPROVED', 'BLOCKED', 'REJECT', 'FLAG', 'FLAGGED_FOR_REVIEW']);

export const ReviewQueueTable = ({ queue, onReviewed }) => {
  const [loadingId, setLoadingId] = useState(null);
  const [inspectItem, setInspectItem] = useState(null);
  const [error, setError] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const handleAction = async (item, action) => {
    const apiAction = action === 'REJECT' ? 'BLOCKED' : action;
    let confirmAction = false;
    if (CONFIRMATION_ACTIONS.has(action) || apiAction === 'BLOCKED' || apiAction === 'FLAGGED_FOR_REVIEW') {
      const actionLabel = apiAction === 'APPROVED'
        ? 'approve and publish'
        : apiAction === 'BLOCKED'
          ? 'reject and block'
          : 'flag for manual review';
      const ok = window.confirm(`Confirm ${actionLabel} for this content?`);
      if (!ok) return;
      confirmAction = true;
    }

    const itemKey = `${item.content_type}-${item.id}`;
    setLoadingId(itemKey);
    setError('');
    try {
      await api.reviewPost(item.id, action, item.content_type, confirmAction);
      if (onReviewed) onReviewed();
    } catch (err) {
      setError(err.message || 'Action failed');
    } finally {
      setLoadingId(null);
    }
  };

  const filteredQueue = queue.filter((item) =>
    (typeFilter === 'all' || item.content_type === typeFilter) &&
    (statusFilter === 'all' || item.moderation_status === statusFilter)
  );

  if (queue.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', color: '#94a3b8', padding: '2rem' }} role="status">
        Review queue is empty. No flagged or blocked content requires manual intervention.
      </div>
    );
  }

  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: '1rem', color: '#f8fafc', fontSize: '1.1rem' }}>
          Manual review queue ({filteredQueue.length} of {queue.length})
        </h2>
        {error && <p role="alert" style={{ color: '#f87171', marginBottom: '1rem' }}>{error}</p>}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <label>
            Content type
            <select className="form-input" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option value="all">All content</option>
              <option value="post">Posts</option>
              <option value="comment">Comments</option>
            </select>
          </label>
          <label>
            Moderation status
            <select className="form-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All statuses</option>
              <option value="FLAGGED_FOR_REVIEW">Flagged for review</option>
              <option value="BLOCKED">Blocked</option>
            </select>
          </label>
        </div>

        {filteredQueue.length === 0 ? (
          <p role="status" style={{ color: '#94a3b8' }}>No items match these filters.</p>
        ) : (

        <div className="table-responsive" role="region" aria-label="Review queue table" tabIndex={0}>
          <table className="table" aria-label="Moderation review queue">
            <caption className="sr-only">Posts and comments awaiting or receiving manual moderation review.</caption>
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">Content</th>
                <th scope="col">AI prediction</th>
                <th scope="col">Recommendation</th>
                <th scope="col">Status</th>
                <th scope="col">Created</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredQueue.map((item) => {
                const itemKey = `${item.content_type}-${item.id}`;
                return <tr key={itemKey}>
                  <td>{item.content_type}</td>
                  <td style={{ maxWidth: '240px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.content}
                  </td>
                  <td>
                    <span
                      className={`status-text-${(item.ai_prediction?.label || 'unknown').toLowerCase().replace(/\s+/g, '-')}`}
                      style={{ fontWeight: 'bold' }}
                    >
                      {item.ai_prediction?.label || 'Unknown'}
                      {item.ai_prediction?.confidence != null && ` (${Math.round(item.ai_prediction.confidence * 100)}%)`}
                    </span>
                  </td>
                  <td>{item.moderation_recommendation || '—'}</td>
                  <td>
                    <span className="badge badge-flagged" aria-label={`Status ${item.moderation_status}`}>
                      {item.moderation_status}
                    </span>
                  </td>
                  <td>{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setInspectItem({ id: item.id, content_type: item.content_type })}
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        Inspect
                      </button>
                      <button
                        type="button"
                        className="btn btn-success"
                        onClick={() => handleAction(item, 'APPROVED')}
                        disabled={loadingId === itemKey}
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger"
                        onClick={() => handleAction(item, 'REJECT')}
                        disabled={loadingId === itemKey}
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleAction(item, 'FLAG')}
                        disabled={loadingId === itemKey}
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        Flag
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleAction(item, 'MARK_REVIEWED')}
                        disabled={loadingId === itemKey}
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        Mark reviewed
                      </button>
                    </div>
                  </td>
                </tr>;
              })}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {inspectItem && (
        <ContentReviewPanel
          itemId={inspectItem.id}
          contentType={inspectItem.content_type}
          onClose={() => setInspectItem(null)}
          onReviewed={() => {
            setInspectItem(null);
            if (onReviewed) onReviewed();
          }}
        />
      )}
    </>
  );
};
