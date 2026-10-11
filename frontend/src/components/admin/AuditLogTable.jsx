import React from 'react';

export const AuditLogTable = ({ logs }) => {
  if (!logs.length) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }} role="status">
        No audit entries recorded yet.
      </div>
    );
  }

  return (
    <div className="card">
      <h2 style={{ marginBottom: '1rem', color: '#f8fafc', fontSize: '1.1rem' }}>
        System audit trail
      </h2>

      <div className="table-responsive" role="region" aria-label="System audit log table" tabIndex={0}>
        <table className="table" aria-label="System Audit Logs">
          <caption className="sr-only">Administrative actions with timestamps, actor IDs, event types, and affected resource IDs.</caption>
          <thead>
          <tr>
            <th scope="col">Timestamp</th>
            <th scope="col">Actor ID</th>
            <th scope="col">Actor role</th>
            <th scope="col">Event type</th>
            <th scope="col">Resource ID</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id}>
                <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}>{log.actor_id?.slice(0, 8) || '—'}</td>
                <td>
                  <span className="badge" style={{ background: '#3b82f6', color: 'white' }}>{log.actor_role}</span>
                </td>
                <td style={{ fontWeight: '600', color: '#f8fafc' }}>{log.event_type}</td>
                <td style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}>{log.resource_id?.slice(0, 8) || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
