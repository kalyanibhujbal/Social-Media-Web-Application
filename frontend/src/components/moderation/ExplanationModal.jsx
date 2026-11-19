import React, { useEffect, useRef } from 'react';
import { Sparkles, X, Info } from 'lucide-react';

const formatPercent = (value) => `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;

export const ExplanationModal = ({ post, onClose }) => {
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const prediction = post?.ai_prediction;
  const explanation = prediction?.explanation;
  const probabilityEntries = prediction?.probabilities && typeof prediction.probabilities === 'object'
    ? Object.entries(prediction.probabilities).filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
    : [];
  const topWords = Array.isArray(explanation?.top_words) ? explanation.top_words : [];
  const metadata = [
    ['Model', prediction?.model_name],
    ['Version', prediction?.model_version],
    ['Analyzed', prediction?.inference_timestamp ? new Date(prediction.inference_timestamp).toLocaleString() : ''],
  ].filter(([, value]) => value);

  useEffect(() => {
    const previousFocus = document.activeElement;
    closeRef.current?.focus();
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = [...dialogRef.current.querySelectorAll('button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')];
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      previousFocus?.focus?.();
    };
  }, [onClose]);

  if (!post) return null;

  return (
    <div className="modal-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal-content explanation-modal" role="dialog" aria-modal="true" aria-labelledby="explanation-title" ref={dialogRef} tabIndex={-1}>
        <header className="modal-header">
          <div><span className="eyebrow">MODERATION DETAILS</span><h2 className="modal-title" id="explanation-title"><Sparkles size={20} aria-hidden="true" /> Why was this flagged?</h2></div>
          <button ref={closeRef} type="button" onClick={onClose} className="modal-close" aria-label="Close moderation details"><X size={19} /></button>
        </header>

        <div className="explanation-summary">
          {(prediction?.label || prediction?.predicted_class) && <div><span className="field-label">Prediction</span><strong>{prediction.label || prediction.predicted_class}</strong></div>}
          {typeof prediction?.confidence === 'number' && <div><span className="field-label">Confidence</span><strong>{`${formatPercent(prediction.confidence)}${prediction.confidence_level ? ` · ${prediction.confidence_level.toLowerCase()}` : ''}`}</strong></div>}
          {post.moderation_status && <div><span className="field-label">Content status</span><strong>{post.moderation_status.replaceAll('_', ' ')}</strong></div>}
        </div>

        {prediction?.confidence_level === 'LOW' && <div className="notice-card notice-card-warning"><Info size={17} aria-hidden="true" /> AI confidence is low. Treat this prediction cautiously; a human review may be appropriate.</div>}

        {post.content?.trim() && <section className="explanation-block">
          <h3>Content reviewed</h3>
          <blockquote>{post.content}</blockquote>
        </section>}

        {probabilityEntries.length > 0 && <section className="explanation-block">
          <h3>Class scores returned by the model</h3>
          <div className="probability-list">{probabilityEntries.map(([category, rawValue]) => {
            const value = Number(rawValue);
            const percent = Math.max(0, Math.min(value, 1)) * 100;
            return <div className="probability-row" key={category}>
              <div><span>{category}</span><strong>{formatPercent(value)}</strong></div>
              <div className="probability-track" aria-hidden="true"><span style={{ width: `${percent}%` }} /></div>
            </div>;
          })}</div>
        </section>}

        {topWords.length > 0 && <section className="explanation-block">
          <h3>Rule indicators</h3>
          {explanation?.method && <p className="muted-note">Method returned: {explanation.method}</p>}
          <div className="rule-indicator-list">{topWords.map((item, index) => <span className="rule-indicator" key={`${item.word}-${index}`}><strong>{item.word}</strong><span>{item.matched_rule || 'Keyword rule'}</span></span>)}</div>
          <p className="explanation-caveat"><Info size={16} aria-hidden="true" /> These are rule-based keyword indicators, not a causal explanation of the model’s decision.</p>
        </section>}

        {metadata.length > 0 && <section className="model-metadata">
          {metadata.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
        </section>}
      </section>
    </div>
  );
};
