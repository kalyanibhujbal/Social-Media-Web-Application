import React, { useContext, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { Settings, Download, Trash2 } from 'lucide-react';

export const AccountSettings = () => {
  const { user, logout, updateProfile } = useContext(AuthContext);
  const [dataExport, setDataExport] = useState(null);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [username, setUsername] = useState(user?.username || '');
  const [email, setEmail] = useState(user?.email || '');
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [headline, setHeadline] = useState(user?.headline || '');
  const [location, setLocation] = useState(user?.location || '');
  const [about, setAbout] = useState(user?.about || '');
  const [skills, setSkills] = useState((user?.skills || []).join(', '));
  const [isPrivate, setIsPrivate] = useState(Boolean(user?.is_private));
  const [currentPassword, setCurrentPassword] = useState('');
  const [loading, setLoading] = useState(false);

  if (!user) {
    return (
      <main id="main-content" className="container" style={{ paddingTop: '3rem', textAlign: 'center' }}>
        <p style={{ color: '#f87171' }}>Please log in to manage your account and privacy settings.</p>
      </main>
    );
  }

  const handleExportData = async () => {
    setLoading(true);
    try {
      const data = await api.exportData();
      setDataExport(data);
    } catch (err) {
      alert(err.message || 'Export failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (window.confirm('Permanently delete your account, posts, comments, and related moderation records? This cannot be undone.')) {
      try {
        await api.deleteAccount();
        logout();
      } catch (err) {
        alert(err.message || 'Deletion failed.');
      }
    }
  };

  const handleProfileUpdate = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setMsg('');
    try {
      await updateProfile({ username, email, currentPassword, fullName, headline, location, about, skills: skills.split(',').map((item) => item.trim()).filter(Boolean), isPrivate });
      setCurrentPassword('');
      setMsg('Account information updated.');
    } catch (err) {
      setError(err.message || 'Could not update account information.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main id="main-content" className="container" style={{ paddingTop: '2.5rem', maxWidth: '800px' }}>
      <div className="card">
        <h2 style={{ fontSize: '1.5rem', color: '#f8fafc', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Settings size={23} /> Account & Privacy Settings
        </h2>

        <div style={{ marginBottom: '1.5rem', background: '#0f172a', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
          <h3 style={{ fontSize: '1rem', color: '#f8fafc', marginBottom: '0.5rem' }}>User Profile Identity</h3>
          <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Name: <strong style={{ color: '#f8fafc' }}>{user.full_name || 'Not set'}</strong></p>
          <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Username: <strong style={{ color: '#f8fafc' }}>@{user.username}</strong></p>
          <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Email: <strong style={{ color: '#f8fafc' }}>{user.email}</strong></p>
        </div>

        <form onSubmit={handleProfileUpdate} style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', color: '#f8fafc', marginBottom: '0.75rem' }}>Correct account information</h3>
          <div className="form-group">
            <label htmlFor="settings-full-name" className="form-label">Full name</label>
            <input id="settings-full-name" className="form-input" value={fullName} onChange={(event) => setFullName(event.target.value)} maxLength={80} />
          </div>
          <div className="form-group">
            <label htmlFor="settings-username" className="form-label">Username</label>
            <input id="settings-username" className="form-input" value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} maxLength={30} required />
          </div>
          <div className="form-group">
            <label htmlFor="settings-email" className="form-label">Email</label>
            <input id="settings-email" type="email" className="form-input" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <div className="form-group">
            <label htmlFor="settings-headline" className="form-label">Professional headline</label>
            <input id="settings-headline" className="form-input" value={headline} onChange={(event) => setHeadline(event.target.value)} maxLength={120} placeholder="A short line about your work" />
          </div>
          <div className="form-group">
            <label htmlFor="settings-location" className="form-label">Location</label>
            <input id="settings-location" className="form-input" value={location} onChange={(event) => setLocation(event.target.value)} maxLength={120} placeholder="City or region (optional)" />
          </div>
          <div className="form-group">
            <label htmlFor="settings-about" className="form-label">About</label>
            <textarea id="settings-about" className="form-textarea" value={about} onChange={(event) => setAbout(event.target.value)} maxLength={1000} rows={4} />
          </div>
          <div className="form-group">
            <label htmlFor="settings-skills" className="form-label">Skills <span className="muted-note">(comma-separated, up to 20)</span></label>
            <input id="settings-skills" className="form-input" value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="React, Python, NLP" />
          </div>
          <fieldset className="form-group privacy-setting-card">
            <legend className="form-label">Account visibility</legend>
            <label htmlFor="settings-private-account" className="privacy-setting-option">
              <input id="settings-private-account" type="checkbox" checked={isPrivate} onChange={(event) => setIsPrivate(event.target.checked)} />
              <span><strong>Private account</strong><small>{isPrivate ? 'Only approved followers can view your posts and full profile details. New follows require your approval.' : 'Your profile and approved posts are visible to everyone. New followers are added immediately.'}</small></span>
            </label>
            <p className="form-help">Changes are saved with the profile form below and require your current password.</p>
          </fieldset>
          <div className="form-group">
            <label htmlFor="settings-password" className="form-label">Current password (to confirm changes)</label>
            <input id="settings-password" type="password" className="form-input" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} minLength={8} maxLength={100} required />
          </div>
          {error && <p role="alert" style={{ color: '#f87171' }}>{error}</p>}
          {msg && <p role="status" style={{ color: '#34d399' }}>{msg}</p>}
          <button type="submit" className="btn btn-secondary" disabled={loading}>Save profile</button>
        </form>

        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', color: '#f8fafc', marginBottom: '0.5rem' }}>Privacy & Data Requests</h3>
          <p style={{ color: '#94a3b8', marginBottom: '0.75rem' }}>Optional analytics and model training are not used. You can change browser storage choices in the footer's Consent Preferences page.</p>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={handleExportData} disabled={loading}>
              {loading ? 'Exporting...' : <><Download size={16} /> Export My Data Package</>}
            </button>
            <button className="btn btn-danger" onClick={handleDeleteAccount}>
              <><Trash2 size={16} /> Delete My Account & Content</>
            </button>
          </div>
        </div>

        {dataExport && (
          <div style={{ marginTop: '1rem' }}>
            <h4 style={{ color: '#34d399', fontSize: '0.9rem', marginBottom: '0.4rem' }}>Exported Personal Data Package (JSON):</h4>
            <pre style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', overflowX: 'auto', fontSize: '0.8rem', color: '#34d399', border: '1px solid #334155' }}>
              {JSON.stringify(dataExport, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </main>
  );
};
