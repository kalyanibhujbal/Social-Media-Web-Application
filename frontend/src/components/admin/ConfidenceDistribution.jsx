import React from 'react';

export const ConfidenceDistribution = ({ buckets }) => {
  if (!buckets || buckets.every((b) => b.count === 0)) {
    return (
      <p style={{ color: '#94a3b8' }} role="status">
        No confidence distribution data yet.
      </p>
    );
  }

  const total = buckets.reduce((sum, b) => sum + b.count, 0) || 1;
  const summaryText = buckets.map((b) => `${b.label}: ${b.count}`).join('; ');

  return (
    <div role="img" aria-label={`Confidence distribution. ${summaryText}`}>
      <p className="sr-only">{summaryText}</p>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {buckets.map((bucket) => {
          const pct = Math.round((bucket.count / total) * 100);
          return (
            <li key={bucket.label} style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                <span>{bucket.label}</span>
                <span>
                  {bucket.count} ({pct}%)
                </span>
              </div>
              <div
                style={{
                  height: '8px',
                  background: '#0f172a',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  border: '1px solid #334155',
                }}
                aria-hidden="true"
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: '100%',
                    background: '#3b82f6',
                    minWidth: bucket.count > 0 ? '4px' : 0,
                  }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
