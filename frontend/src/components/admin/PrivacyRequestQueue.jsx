import React, { useState } from 'react';
import { api } from '../../services/api';

export const PrivacyRequestQueue = ({ requests, onChanged }) => {
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [responses, setResponses] = useState({});
  const update = async (item, status) => {
    if ((responses[item.id] || '').trim().length < 2) {
      setError('Add a short outcome before updating this request.');
      return;
    }
    setBusyId(item.id);
    setError('');
    try {
      await api.updateAdminPrivacyRequest(item.id, status, responses[item.id].trim());
      await onChanged();
    } catch (err) {
      setError(err.message || 'Could not update request.');
    } finally {
      setBusyId('');
    }
  };

  if (!requests.length) return <p role="status">No privacy requests submitted.</p>;
  return (
    <div className="table-responsive" role="region" aria-label="Privacy requests" tabIndex={0}>
      {error && <p role="alert">{error}</p>}
      <table className="table">
        <caption className="sr-only">Privacy and grievance requests. Account references are pseudonymous IDs.</caption>
        <thead><tr>
          <th scope="col">Submitted</th><th scope="col">Type</th><th scope="col">Account reference</th>
          <th scope="col">Details</th><th scope="col">Status</th><th scope="col">Actions</th>
        </tr></thead>
        <tbody>{requests.map((item) => (
          <tr key={item.id}>
            <td>{item.created_at}</td><td>{item.request_type.replaceAll('_', ' ')}</td>
            <td><code>{item.requester_reference}</code></td>
            <td className="privacy-request-details">{item.description || 'No details provided'}</td>
            <td>{item.status}{item.response && <p>{item.response}</p>}</td>
            <td>{item.status === 'OPEN' ? (
              <div className="privacy-request-actions">
                <label htmlFor={`privacy-response-${item.id}`}>Outcome for requester</label>
                <textarea id={`privacy-response-${item.id}`} rows={2} maxLength={1000} value={responses[item.id] || ''} onChange={(event) => setResponses({ ...responses, [item.id]: event.target.value })} />
                <button type="button" className="btn btn-primary" disabled={busyId === item.id} onClick={() => update(item, 'RESOLVED')}>Mark resolved</button>
                <button type="button" className="btn btn-secondary" disabled={busyId === item.id} onClick={() => update(item, 'DECLINED')}>Decline</button>
              </div>
            ) : item.resolved_at || '—'}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
};
