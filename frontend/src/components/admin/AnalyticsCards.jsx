import React from 'react';

export const AnalyticsCards = ({ analytics }) => {
  if (!analytics) return null;

  const evalData = analytics.model_evaluation || {};
  const metrics = evalData.metrics;
  const hasEval = Boolean(metrics && evalData.evaluation_status === 'COMPLETED');

  return (
    <div>
      <div
        style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}
        role="group"
        aria-label="Moderation statistics from database"
      >
        <MetricCard label="Total moderation items" value={analytics.total_moderation_items} />
        <MetricCard label="Posts" value={analytics.total_posts} />
        <MetricCard label="Comments" value={analytics.total_comments} />
        <MetricCard label="Approved" value={analytics.approved_count} accent="#34d399" />
        <MetricCard label="Flagged" value={analytics.flagged_count} accent="#c084fc" />
        <MetricCard label="Pending manual review" value={analytics.pending_manual_reviews ?? analytics.flagged_count} accent="#c084fc" />
        <MetricCard label="Blocked" value={analytics.blocked_count} accent="#f87171" />
        <MetricCard label="Admin overrides" value={analytics.override_count} />
      </div>

      <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1.05rem', color: '#f8fafc', marginBottom: '1rem' }}>Classification summary</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
          <MetricCard label="Hate speech" value={analytics.hate_speech_count} accent="#f87171" />
          <MetricCard label="Offensive" value={analytics.offensive_count} accent="#fbbf24" />
          <MetricCard label="Normal" value={analytics.normal_count} accent="#34d399" />
        </div>
        <p className="sr-only" role="status">
          Classification counts: hate {analytics.hate_speech_count}, offensive {analytics.offensive_count}, normal {analytics.normal_count}.
        </p>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem', border: '1px solid #3b82f6', padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1.05rem', color: '#f8fafc', marginBottom: '1rem' }}>Model performance</h2>

        {hasEval ? (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
              <MetricCard label="Accuracy" value={`${Math.round(metrics.accuracy * 100)}%`} accent="#34d399" />
              <MetricCard label="Precision (macro)" value={`${Math.round(metrics.macro_precision * 100)}%`} accent="#60a5fa" />
              <MetricCard label="Recall (macro)" value={`${Math.round(metrics.macro_recall * 100)}%`} accent="#c084fc" />
              <MetricCard label="F1 (macro)" value={`${Math.round(metrics.macro_f1_score * 100)}%`} accent="#fbbf24" />
            </div>

            {evalData.confusion_matrix && (
              <div>
                <h3 style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '0.5rem' }}>Confusion matrix</h3>
                <div className="table-responsive" role="region" aria-label="Model confusion matrix" tabIndex={0}>
                  <table className="table" aria-label="Confusion matrix for model evaluation">
                    <caption className="sr-only">Rows are actual classes, columns are predicted classes.</caption>
                    <thead>
                      <tr>
                        <th scope="col">Actual \ Predicted</th>
                        <th scope="col">Hate speech</th>
                        <th scope="col">Offensive</th>
                        <th scope="col">Normal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evalData.confusion_matrix.labels.map((rowLabel, rIdx) => (
                        <tr key={rowLabel}>
                          <th scope="row" style={{ fontWeight: 'bold', color: '#f8fafc' }}>{rowLabel}</th>
                          {evalData.confusion_matrix.matrix[rIdx].map((val, cIdx) => (
                            <td
                              key={cIdx}
                              style={{
                                background: rIdx === cIdx ? 'rgba(16, 185, 129, 0.15)' : '#0f172a',
                                fontWeight: rIdx === cIdx ? 'bold' : 'normal',
                              }}
                            >
                              {val}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p style={{ color: '#94a3b8', fontStyle: 'italic', padding: '1rem', background: '#0f172a', borderRadius: '6px' }} role="status">
            Model evaluation data not available.
          </p>
        )}
      </div>

      <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1.05rem', color: '#f8fafc', marginBottom: '0.75rem' }}>Active moderation model</h2>
        <dl style={{ display: 'grid', gridTemplateColumns: 'minmax(130px, 200px) 1fr', gap: '0.5rem' }}>
          <dt>Inference backend</dt>
          <dd>{analytics.model_information?.inference_backend || 'Unavailable'}</dd>
          <dt>Model name</dt>
          <dd>{analytics.model_information?.model_name || 'Not loaded'}</dd>
          <dt>Model version</dt>
          <dd>{analytics.model_information?.model_version || '—'}</dd>
        </dl>
      </div>
    </div>
  );
};

function MetricCard({ label, value, accent }) {
  return (
    <div className="card" style={{ padding: '1rem' }}>
      <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{label}</div>
      <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: accent || '#f8fafc' }}>{value}</div>
    </div>
  );
}
