import React, { useState } from 'react';
import { api } from '../../services/api';
import { Sparkles, ShieldCheck, AlertCircle, Info, Clock } from 'lucide-react';

export const ModerationSandbox = () => {
  const [inputText, setInputText] = useState('Having a great day learning about artificial intelligence and transformers.');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAnalyze = async (event) => {
    event.preventDefault();
    if (!inputText.trim() || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await api.analyzeText(inputText.trim()));
    } catch (err) {
      const message = err.message || '';
      setError(message === 'Failed to fetch' ? 'The moderation service is not reachable. Check the connection and try again.' : message || 'Analysis could not be completed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const prediction = result?.prediction;

  return (
    <section className="card sandbox-card" aria-labelledby="sandbox-heading">
      <div className="sandbox-heading"><span className="sidebar-icon"><Sparkles size={17} aria-hidden="true" /></span><div><span className="eyebrow">INTERACTIVE DEMO</span><h2 id="sandbox-heading">Try the moderation service</h2></div></div>
      <p className="sandbox-intro">Analyze text without publishing it. The sandbox response is not stored by the analysis endpoint.</p>
      <form onSubmit={handleAnalyze}>
        <label className="sr-only" htmlFor="sandbox-text">Text to analyze</label>
        <textarea id="sandbox-text" className="form-textarea" rows="3" maxLength={2000} value={inputText} onChange={(event) => setInputText(event.target.value)} placeholder="Write a sentence to analyze…" required />
        <div className="sandbox-actions"><span>{inputText.length} / 2,000</span><button type="submit" className="btn btn-primary btn-sm" disabled={loading || !inputText.trim()}>{loading ? <><span className="spinner" /> Analyzing…</> : <><Sparkles size={15} /> Analyze text</>}</button></div>
      </form>
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} /> {error}</div>}
      {prediction && <div className="sandbox-result" aria-live="polite">
        <div className="sandbox-result-top"><div><span className="field-label">Detected language</span><strong>{result.detected_language || 'Not returned'}</strong></div><div><span className="field-label">Prediction</span><strong>{prediction.label || prediction.predicted_class || 'Not returned'}</strong></div><div><span className="field-label">Confidence</span><strong>{typeof prediction.confidence === 'number' ? `${Math.round(prediction.confidence * 100)}%${prediction.confidence_level ? ` · ${prediction.confidence_level.toLowerCase()}` : ''}` : 'Not returned'}</strong></div><div><span className="field-label">Recommended action</span><strong>{result.action_recommendation?.replaceAll('_', ' ') || 'Not returned'}</strong></div></div>
        {result.language_supported === false && <div className="notice-card notice-card-warning"><Info size={16} />{result.language_notice || 'The configured moderation model is not verified for this language. Human review may be required.'}</div>}
        {prediction.confidence_level === 'LOW' && <div className="notice-card notice-card-warning"><Clock size={16} /> AI confidence is low. A human should review this result carefully.</div>}
        {prediction.explanation?.top_words?.length > 0 && <div className="rule-indicator-list">{prediction.explanation.top_words.map((item, index) => <span className="rule-indicator" key={`${item.word}-${index}`}><strong>{item.word}</strong><span>{item.matched_rule || 'Keyword rule'}</span></span>)}</div>}
        <p className="sandbox-caveat"><ShieldCheck size={15} /> Automated predictions are experimental and can be inaccurate. {prediction.explanation?.top_words?.length > 0 && 'Rule highlights are indicators, not proof of model causality.'}</p>
      </div>}
      <p className="sandbox-footnote"><Info size={14} /> Analysis uses the configured backend and model availability; it is not a validated safety classifier.</p>
    </section>
  );
};
