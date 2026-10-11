import React, { useState, useEffect, useContext, useCallback } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { CreatePostForm } from '../components/posts/CreatePostForm';
import { PostCard } from '../components/posts/PostCard';
import { UserCommentList } from '../components/dashboard/UserCommentList';
import { PendingReviewList } from '../components/dashboard/PendingReviewList';
import { ModerationHistoryTable } from '../components/dashboard/ModerationHistoryTable';

export const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState('posts');

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getUserDashboard();
      setDashboard(data);
    } catch (err) {
      setError('Failed to load your dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchDashboard();
    }
  }, [user, fetchDashboard]);

  const handleAppeal = async (postId) => {
    const reason = window.prompt('Brief reason for appeal (min 5 characters):');
    if (!reason || reason.length < 5) return;
    try {
      await api.appealPost(postId, reason);
      fetchDashboard();
    } catch (err) {
      alert(err.message || 'Appeal failed');
    }
  };

  if (!user) {
    return (
      <main id="main-content" className="container" style={{ paddingTop: '3rem', textAlign: 'center' }}>
        <p style={{ color: '#f87171' }}>Please log in to access your user dashboard.</p>
      </main>
    );
  }

  const stats = dashboard?.stats;
  const myPosts = dashboard?.posts || [];
  const myComments = dashboard?.comments || [];
  const hasModerationData =
    (stats?.total_posts || 0) + (stats?.total_comments || 0) > 0;

  return (
    <main id="main-content" className="container" style={{ paddingTop: '2rem' }}>
      <header className="card" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', color: '#f8fafc' }}>My moderation dashboard</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Signed in as <strong style={{ color: '#f8fafc' }}>@{user.username}</strong>
          </p>
        </div>

        {stats && (
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }} role="group" aria-label="Moderation summary counts">
            <StatChip label="Published" value={stats.approved_posts} tone="success" />
            <StatChip label="Pending review" value={stats.pending_review_posts} tone="flagged" />
            <StatChip label="Blocked" value={stats.blocked_posts} tone="danger" />
            <StatChip label="My comments" value={stats.total_comments} tone="neutral" />
          </div>
        )}
      </header>

      <CreatePostForm onPostCreated={fetchDashboard} />

      <nav aria-label="Dashboard sections" style={{ margin: '1.5rem 0', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {[
          ['posts', 'My posts'],
          ['comments', 'My comments'],
          ['pending', 'Pending review'],
          ['history', 'Moderation history'],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn ${activeSection === id ? 'btn-primary' : 'btn-secondary'}`}
            aria-pressed={activeSection === id}
            onClick={() => setActiveSection(id)}
          >
            {label}
          </button>
        ))}
        <button type="button" className="btn btn-secondary" onClick={fetchDashboard} style={{ marginLeft: 'auto' }}>
          Refresh
        </button>
      </nav>

      {loading && <p style={{ color: '#94a3b8' }} role="status">Loading your moderation data…</p>}
      {error && <p style={{ color: '#f87171' }} role="alert">{error}</p>}

      {!loading && !hasModerationData && (
        <div className="card" style={{ textAlign: 'center', color: '#94a3b8', padding: '2.5rem' }} role="status">
          <p style={{ fontSize: '1.1rem' }}>No moderation data available yet.</p>
          <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Create a post above to begin.</p>
        </div>
      )}

      {!loading && dashboard && activeSection === 'posts' && myPosts.length > 0 && (
        <section aria-label="My posts">
          {myPosts.map((post) => (
            <div key={post.id}>
              <PostCard post={post} />
              {(post.moderation_status === 'BLOCKED' || post.moderation_status === 'FLAGGED_FOR_REVIEW') && (
                <div style={{ marginTop: '-0.5rem', marginBottom: '1rem', paddingLeft: '0.5rem' }}>
                  <button type="button" className="btn btn-secondary" style={{ fontSize: '0.8rem' }} onClick={() => handleAppeal(post.id)}>
                    Request review (appeal)
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {!loading && dashboard && activeSection === 'comments' && (
        <section aria-label="My comments" className="card" style={{ padding: '1rem' }}>
          <h2 style={{ fontSize: '1.15rem', marginBottom: '1rem', color: '#f8fafc' }}>My comments</h2>
          <UserCommentList comments={myComments} />
        </section>
      )}

      {!loading && dashboard && activeSection === 'pending' && (
        <section aria-label="Pending review items" className="card" style={{ padding: '1rem' }}>
          <h2 style={{ fontSize: '1.15rem', marginBottom: '1rem', color: '#f8fafc' }}>Pending review</h2>
          <PendingReviewList items={dashboard.pending_items || []} />
        </section>
      )}

      {!loading && dashboard && activeSection === 'history' && (
        <section aria-label="Moderation history" className="card" style={{ padding: '1rem' }}>
          <h2 style={{ fontSize: '1.15rem', marginBottom: '1rem', color: '#f8fafc' }}>Moderation history</h2>
          {dashboard.moderation_history?.length ? (
            <ModerationHistoryTable history={dashboard.moderation_history} />
          ) : (
            <p style={{ color: '#94a3b8' }} role="status">No moderation history available yet.</p>
          )}
        </section>
      )}
    </main>
  );
};

function StatChip({ label, value, tone }) {
  const colors = {
    success: '#34d399',
    flagged: '#c084fc',
    danger: '#f87171',
    neutral: '#f8fafc',
  };
  return (
    <div style={{ background: '#0f172a', padding: '0.5rem 1rem', borderRadius: '8px', textAlign: 'center', border: '1px solid #334155', minWidth: '88px' }}>
      <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{label}</div>
      <div style={{ fontWeight: 'bold', color: colors[tone] || colors.neutral }} aria-label={`${label}: ${value}`}>
        {value}
      </div>
    </div>
  );
}
