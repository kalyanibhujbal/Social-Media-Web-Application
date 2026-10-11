import React, { useState } from 'react';
import { AlertCircle, Save } from 'lucide-react';

export const UserManagementTable = ({ users, currentUserId, onUpdate }) => {
  const [changes, setChanges] = useState({});
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');

  if (!users.length) return <p className="muted-note" role="status">No user accounts in the system yet.</p>;

  const save = async (user) => {
    const change = changes[user.id] || {};
    const updates = {};
    if (change.role && change.role !== user.role) updates.role = change.role;
    if (typeof change.is_active === 'boolean' && change.is_active !== user.is_active) updates.is_active = change.is_active;
    if (!Object.keys(updates).length) return;
    if (updates.role === 'ADMIN' && user.role !== 'ADMIN' && !window.confirm(`Grant administrator access to @${user.username}?`)) return;
    if (updates.is_active === false && !window.confirm(`Deactivate @${user.username}'s account?`)) return;
    setBusyId(user.id);
    setError('');
    try {
      const updated = await onUpdate(user.id, updates);
      setChanges((current) => ({ ...current, [user.id]: { role: updated.role, is_active: updated.is_active } }));
    } catch (err) { setError(err.message || 'Account access could not be changed.'); }
    finally { setBusyId(''); }
  };

  return <>
    {error && <p className="notice-card notice-card-error" role="alert"><AlertCircle size={15} />{error}</p>}
    <div className="table-responsive" role="region" aria-label="User accounts table" tabIndex={0}>
      <table className="table" aria-label="User accounts summary">
        <caption className="sr-only">Minimal user management list without email addresses or credentials.</caption>
        <thead><tr><th scope="col">Username</th><th scope="col">Role</th><th scope="col">Active</th><th scope="col">Joined</th><th scope="col">Update access</th></tr></thead>
        <tbody>{users.map((user) => {
          const change = changes[user.id] || {};
          const role = change.role ?? user.role;
          const isActive = change.is_active ?? user.is_active;
          const modified = role !== user.role || isActive !== user.is_active;
          const self = user.id === currentUserId;
          return <tr key={user.id}>
            <td>@{user.username}</td>
            <td><label className="sr-only" htmlFor={`role-${user.id}`}>Role for @{user.username}</label><select id={`role-${user.id}`} className="form-select compact-select" value={role} disabled={self} onChange={(event) => setChanges((current) => ({ ...current, [user.id]: { ...current[user.id], role: event.target.value } }))}><option value="USER">USER</option><option value="MODERATOR">MODERATOR</option><option value="ADMIN">ADMIN</option></select></td>
            <td><label className="sr-only" htmlFor={`active-${user.id}`}>Account status for @{user.username}</label><select id={`active-${user.id}`} className="form-select compact-select" value={isActive ? 'active' : 'inactive'} disabled={self} onChange={(event) => setChanges((current) => ({ ...current, [user.id]: { ...current[user.id], is_active: event.target.value === 'active' } }))}><option value="active">Active</option><option value="inactive">Inactive</option></select></td>
            <td>{user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</td>
            <td><button type="button" className="btn btn-secondary btn-sm" disabled={!modified || busyId === user.id || self} onClick={() => save(user)}><Save size={14} />{busyId === user.id ? 'Saving…' : 'Save'}</button></td>
          </tr>;
        })}</tbody>
      </table>
    </div>
  </>;
};
