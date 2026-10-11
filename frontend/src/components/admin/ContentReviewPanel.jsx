import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';

const CONFIRMATION_ACTIONS = new Set(['APPROVED', 'BLOCKED', 'REJECT', 'FLAG', 'FLAGGED_FOR_REVIEW']);

export const ContentReviewPanel = ({ itemId, contentType, onClose, onReviewed }) => {
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const dialogRef = useRef(null);

  useEffect(() => {
    const previousFocus = document.activeElement;
    const firstButton = dialogRef.current?.querySelector('button:not(:disabled)');
    (firstButton || dialogRef.current)?.focus();
    return () => previousFocus?.focus?.();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await api.getAdminContent(itemId, contentType);
        if (!cancelled) setPost(data);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load content');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [itemId, contentType]);

  const runAction = async (action) => {
    const normalized = action === 'REJECT' ? 'BLOCKED' : action;
    let confirmAction = false;
    if (CONFIRMATION_ACTIONS.has(action) || CONFIRMATION_ACTIONS.has(normalized)) {
      const actionLabel = normalized === 'APPROVED'
        ? 'approve and publish'
        : normalized === 'BLOCKED'
          ? 'reject and block'
          : 'flag for manual review';
      const ok = window.confirm(`Confirm ${actionLabel} for this content?`);
      if (!ok) return;
      confirmAction = true;
    }

    setActionLoading(true);
    setError('');
    try {
      await api.reviewPost(itemId, action, contentType, confirmAction);
      if (onReviewed) onReviewed();
      if (onClose) onClose();
    } catch (err) {
      setError(err.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="content-review-title"
      aria-describedby="content-review-summary"
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose?.();
        if (e.key === 'Tab') {
          const focusable = e.currentTarget.querySelectorAll('button:not(:disabled), textarea, input, [tabindex="0"]');
          if (!focusable.length) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }}
    >
      <div ref={dialogRef} tabIndex={-1} className="card modal-content" style={{ maxWidth: '640px', width: '100%', margin: '2rem auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 id="content-review-title" style={{ fontSize: '1.1rem', color: '#f8fafc' }}>
            Content review
          </h2>
          <button type="button" className="btn btn-secondary" onClick={onClose} aria-label="Close review panel">
            Close
          </button>
        </div>

        <p id="content-review-summary" className="sr-only">Inspect the selected {contentType} and record a moderation decision.</p>

        {loading && <p style={{ color: '#94a3b8' }}>Loading content…</p>}
        {error && <p style={{ color: '#f87171' }} role="alert">{error}</p>}

        {post && (
          <div>
            <dl style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: '0.5rem', fontSize: '0.9rem' }}>
              <dt style={{ color: '#94a3b8' }}>Content type</dt>
              <dd>{contentType}</dd>

              <dt style={{ color: '#94a3b8' }}>Content</dt>
              <dd style={{ color: '#e2e8f0', whiteSpace: 'pre-wrap' }}>{post.content}</dd>

              <dt style={{ color: '#94a3b8' }}>Prediction</dt>
              <dd>{post.ai_prediction?.label}</dd>

              <dt style={{ color: '#94a3b8' }}>Confidence</dt>
              <dd>
                {post.ai_prediction?.confidence != null
                  ? `${Math.round(post.ai_prediction.confidence * 100)}% (${post.ai_prediction.confidence_level || '—'})`
                  : '—'}
              </dd>

              <dt style={{ color: '#94a3b8' }}>Model explanation</dt>
              <dd>
                {post.ai_prediction?.explanation ? (
                  <>
                    <span>{post.ai_prediction.explanation.method || 'Model attribution'}</span>
                    {post.ai_prediction.explanation.top_words?.length > 0 && (
                      <ul>
                        {post.ai_prediction.explanation.top_words.map((item, index) => (
                          <li key={`${item.word}-${index}`}>{item.word}: {item.matched_rule || 'Keyword rule'}</li>
                        ))}
                      </ul>
                    )}
                  </>
                ) : '—'}
              </dd>

              <dt style={{ color: '#94a3b8' }}>Moderation explanation</dt>
              <dd>{post.moderation_explanation || '—'}</dd>

              <dt style={{ color: '#94a3b8' }}>Recommendation</dt>
              <dd>{post.moderation_recommendation || '—'}</dd>

              <dt style={{ color: '#94a3b8' }}>Final status</dt>
              <dd>{post.moderation_status}</dd>

              <dt style={{ color: '#94a3b8' }}>Timestamp</dt>
              <dd>{new Date(post.created_at).toLocaleString()}</dd>

              <dt style={{ color: '#94a3b8' }}>Inference time</dt>
              <dd>{post.ai_prediction?.inference_timestamp ? new Date(post.ai_prediction.inference_timestamp).toLocaleString() : '—'}</dd>

              <dt style={{ color: '#94a3b8' }}>Model version</dt>
              <dd>
                {post.ai_prediction?.model_name || '—'} v{post.ai_prediction?.model_version || '—'}
              </dd>
            </dl>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" className="btn btn-success" disabled={actionLoading} onClick={() => runAction('APPROVED')}>
                Approve
              </button>
              <button type="button" className="btn btn-danger" disabled={actionLoading} onClick={() => runAction('REJECT')}>
                Reject
              </button>
              <button type="button" className="btn btn-secondary" disabled={actionLoading} onClick={() => runAction('FLAG')}>
                Flag
              </button>
              <button type="button" className="btn btn-secondary" disabled={actionLoading} onClick={() => runAction('MARK_REVIEWED')}>
                Mark reviewed
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
