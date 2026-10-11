import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { AnalyticsCards } from '../components/admin/AnalyticsCards';
import { ReviewQueueTable } from '../components/admin/ReviewQueueTable';
import { AuditLogTable } from '../components/admin/AuditLogTable';
import { ConfidenceDistribution } from '../components/admin/ConfidenceDistribution';
import { UserManagementTable } from '../components/admin/UserManagementTable';
import { AdminModerationHistory } from '../components/admin/AdminModerationHistory';
import { PrivacyRequestQueue } from '../components/admin/PrivacyRequestQueue';

export const AdminDashboard = () => {
  const { user } = useContext(AuthContext);
  const [queue, setQueue] = useState([]);
  const [logs, setLogs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [modHistory, setModHistory] = useState([]);
  const [users, setUsers] = useState([]);
  const [privacyRequests, setPrivacyRequests] = useState([]);
  const [report, setReport] = useState(null);
  const [reportError, setReportError] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  const isAdmin = user?.role === 'ADMIN';
  const canModerate = isAdmin || user?.role === 'MODERATOR';

  const loadAdminData = async () => {
    setLoading(true);
    setLoadError('');
    try {
      if (user?.role === 'MODERATOR') {
        const [qData, hData] = await Promise.all([api.getReviewQueue(), api.getModerationHistory()]);
        setQueue(qData);
        setModHistory(hData);
        return;
      }
      const [qData, lData, aData, hData, uData, pData] = await Promise.all([
        api.getReviewQueue(),
        api.getAuditLogs(),
        api.getAnalytics(),
        api.getModerationHistory(),
        api.getAdminUsers(),
        api.getAdminPrivacyRequests(),
      ]);
      setQueue(qData);
      setLogs(lData);
      setAnalytics(aData);
      setModHistory(hData);
      setUsers(uData);
      setPrivacyRequests(pData);
    } catch (err) {
      setLoadError(err.message || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setReportError('');
    try {
      const data = await api.generateReport();
      setReport(data);
    } catch (err) {
      setReportError(err.message || 'Report generation failed');
    }
  };

  const downloadReport = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `moderation-report-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    if (canModerate) loadAdminData();
  }, [user]);

  if (!canModerate) {
    return (
      <main id="main-content" className="container" style={{ paddingTop: '3rem', textAlign: 'center' }}>
        <div className="card" style={{ maxWidth: '500px', margin: '0 auto', border: '1px solid #ef4444' }}>
          <h2 style={{ color: '#f87171', marginBottom: '0.5rem' }}>403 Forbidden</h2>
          <p style={{ color: '#94a3b8' }}>Administrative credentials required.</p>
        </div>
      </main>
    );
  }

  const noData = analytics && analytics.total_posts === 0 && analytics.total_comments === 0;

  const tabs = [
    ['overview', 'Overview'],
    ['review', 'Content review'],
    ['history', 'Moderation history'],
    ['users', 'Users'],
    ['privacy-requests', 'Privacy requests'],
    ['audit', 'Audit'],
    ['reports', 'Reports'],
  ];

  return (
    <main id="main-content" className="container" style={{ paddingTop: '2rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', color: '#f8fafc' }}>{isAdmin ? 'Admin moderation portal' : 'Moderator review workspace'}</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            {isAdmin ? 'Analytics, review queue, audit trail, and reports from live system data' : 'Review flagged posts and comments assigned to the moderation queue.'}
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={loadAdminData}>
          Refresh portal
        </button>
      </header>

      <nav aria-label="Moderation sections" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.25rem' }}>
        {tabs.filter(([id]) => isAdmin || id === 'review' || id === 'history').map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn ${(activeTab === 'overview' && !isAdmin ? 'review' : activeTab) === id ? 'btn-primary' : 'btn-secondary'}`}
            aria-pressed={(activeTab === 'overview' && !isAdmin ? 'review' : activeTab) === id}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {loadError && <p style={{ color: '#f87171' }} role="alert">{loadError}</p>}
      {loading && <p style={{ color: '#94a3b8' }} role="status">Loading moderation records…</p>}

      {!loading && isAdmin && noData && (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', marginBottom: '1.5rem' }} role="status">
          No moderation data available yet.
        </div>
      )}

      {!loading && isAdmin && activeTab === 'overview' && analytics && !noData && (
        <>
          <AnalyticsCards analytics={analytics} />
          <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '1rem' }}>Confidence distribution</h2>
            <ConfidenceDistribution buckets={analytics.confidence_distribution} />
          </div>
        </>
      )}

      {!loading && (!isAdmin && activeTab === 'overview' || activeTab === 'review') && (
        <ReviewQueueTable queue={queue} onReviewed={loadAdminData} />
      )}

      {!loading && (!isAdmin && activeTab === 'overview' || activeTab === 'history') && (
        <div className="card" style={{ padding: '1rem' }}>
          <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc' }}>Moderation history</h2>
          <AdminModerationHistory history={modHistory} />
        </div>
      )}

      {!loading && isAdmin && activeTab === 'users' && (
        <div className="card" style={{ padding: '1rem' }}>
          <h2 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: '#f8fafc' }}>User management</h2>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1rem' }}>
            Minimal account view — email and credentials are not shown.
          </p>
          <UserManagementTable users={users} currentUserId={user.id} onUpdate={async (userId, updates) => {
            const updated = await api.updateAdminUserAccess(userId, updates);
            setUsers((items) => items.map((item) => item.id === userId ? updated : item));
            return updated;
          }} />
        </div>
      )}

      {!loading && activeTab === 'audit' && <AuditLogTable logs={logs} />}

      {!loading && activeTab === 'privacy-requests' && (
        <section className="card" style={{ padding: '1rem' }}>
          <h2 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: '#f8fafc' }}>Privacy & grievance requests</h2>
          <p style={{ color: '#94a3b8', marginBottom: '1rem' }}>Only authorized administrators can access request details. Avoid copying sensitive information into other records.</p>
          <PrivacyRequestQueue requests={privacyRequests} onChanged={loadAdminData} />
        </section>
      )}

      {!loading && activeTab === 'reports' && (
        <div className="card" style={{ padding: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', color: '#f8fafc', marginBottom: '1rem' }}>System reports</h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Reports are generated from current database totals and evaluation files only — no fabricated metrics.
          </p>
          <button type="button" className="btn btn-secondary" onClick={handleGenerateReport}>
            Generate system report
          </button>
          {reportError && <p role="alert" style={{ color: '#f87171', marginTop: '0.75rem' }}>{reportError}</p>}
          {report && (
            <div style={{ marginTop: '1rem' }}>
              <h3 style={{ fontSize: '0.95rem', color: '#34d399', marginBottom: '0.5rem' }}>{report.report_title}</h3>
              <p role="status" style={{ color: '#cbd5e1', marginBottom: '0.75rem' }}>Report generated from current database records.</p>
              <button type="button" className="btn btn-secondary" onClick={downloadReport} style={{ marginBottom: '0.75rem' }}>
                Download JSON report
              </button>
              <pre
                style={{ background: '#0f172a', padding: '1rem', borderRadius: '6px', fontSize: '0.8rem', color: '#34d399', overflowX: 'auto' }}
                aria-label="Generated report JSON"
              >
                {JSON.stringify(report, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </main>
  );
};
