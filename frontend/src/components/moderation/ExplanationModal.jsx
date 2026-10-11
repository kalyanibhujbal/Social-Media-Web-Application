import React, { useEffect, useRef } from 'react';
import { Sparkles, X, Info, CircleHelp } from 'lucide-react';

const formatPercent = (value) => `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;

export const ExplanationModal = ({ post, onClose }) => {
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const prediction = post?.ai_prediction;
  const explanation = prediction?.explanation;
  const probabilities = prediction?.probabilities && typeof prediction.probabilities === 'object' ? prediction.probabilities : null;
  const topWords = Array.isArray(explanation?.top_words) ? explanation.top_words : [];

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
          <div><span className="field-label">AI prediction</span><strong>{prediction?.label || prediction?.predicted_class || 'Not available'}</strong></div>
          <div><span className="field-label">Confidence</span><strong>{typeof prediction?.confidence === 'number' ? `${formatPercent(prediction.confidence)}${prediction.confidence_level ? ` · ${prediction.confidence_level.toLowerCase()}` : ''}` : 'Not returned'}</strong></div>
          <div><span className="field-label">Content status</span><strong>{post.moderation_status?.replaceAll('_', ' ') || 'Not returned'}</strong></div>
        </div>

        {prediction?.confidence_level === 'LOW' && <div className="notice-card notice-card-warning"><Info size={17} aria-hidden="true" /> AI confidence is low. Treat this prediction cautiously; a human review may be appropriate.</div>}

        <section className="explanation-block">
          <h3>Content reviewed</h3>
          <blockquote>{post.content || 'Content was not included in this response.'}</blockquote>
        </section>

        {probabilities ? <section className="explanation-block">
          <h3>Class scores returned by the model</h3>
          <div className="probability-list">{Object.entries(probabilities).map(([category, rawValue]) => {
            const value = Number(rawValue);
            if (!Number.isFinite(value)) return null;
            const percent = Math.max(0, Math.min(value, 1)) * 100;
            return <div className="probability-row" key={category}>
              <div><span>{category}</span><strong>{formatPercent(value)}</strong></div>
              <div className="probability-track" aria-hidden="true"><span style={{ width: `${percent}%` }} /></div>
            </div>;
          })}</div>
        </section> : <section className="explanation-block"><h3>Class scores</h3><p className="muted-note">The backend did not return per-class scores for this content.</p></section>}

        <section className="explanation-block">
          <h3>Rule indicators</h3>
          {explanation?.method && <p className="muted-note">Method returned: {explanation.method}</p>}
          {topWords.length ? <div className="rule-indicator-list">{topWords.map((item, index) => <span className="rule-indicator" key={`${item.word}-${index}`}><strong>{item.word}</strong><span>{item.matched_rule || 'Keyword rule'}</span></span>)}</div> : <p className="muted-note">No rule indicators were returned for this content.</p>}
          <p className="explanation-caveat"><Info size={16} aria-hidden="true" /> These are rule-based keyword indicators, not a causal explanation of the model’s decision.</p>
        </section>

        <section className="model-metadata">
          <div><span>Model</span><strong>{prediction?.model_name || 'Not returned'}</strong></div>
          <div><span>Version</span><strong>{prediction?.model_version || 'Not returned'}</strong></div>
          <div><span>Analyzed</span><strong>{prediction?.inference_timestamp ? new Date(prediction.inference_timestamp).toLocaleString() : 'Not returned'}</strong></div>
        </section>
        <p className="modal-disclaimer"><CircleHelp size={16} aria-hidden="true" /> Automated results can be wrong or incomplete. They are not legal determinations. Use the appeal option to request human review where available.</p>
      </section>
    </div>
  );
};
