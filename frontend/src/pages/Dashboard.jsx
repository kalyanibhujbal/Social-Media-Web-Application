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
    <main id="main-content" className="container page-shell dashboard-page">
      <header className="card dashboard-header">
        <div>
          <span className="eyebrow">YOUR OPENVIBE ACCOUNT</span>
          <h1>My activity &amp; moderation</h1>
          <p>
            Signed in as <strong>@{user.username}</strong>
          </p>
        </div>

        {stats && (
          <div className="dashboard-stat-list" role="group" aria-label="Moderation summary counts">
            <StatChip label="Published" value={stats.approved_posts} tone="success" />
            <StatChip label="Pending review" value={stats.pending_review_posts} tone="flagged" />
            <StatChip label="Blocked" value={stats.blocked_posts} tone="danger" />
            <StatChip label="My comments" value={stats.total_comments} tone="neutral" />
          </div>
        )}
      </header>

      <CreatePostForm onPostCreated={fetchDashboard} />

      <nav aria-label="Dashboard sections" className="dashboard-sections">
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
        <button type="button" className="btn btn-secondary dashboard-refresh" onClick={fetchDashboard}>
          Refresh
        </button>
      </nav>

      {loading && <p className="dashboard-loading" role="status">Loading your activity…</p>}
      {error && <div className="notice-card notice-card-error" role="alert">{error}</div>}

      {!loading && !hasModerationData && (
        <div className="card dashboard-empty" role="status">
          <p>No activity to show yet.</p>
          <p>Create a post above to get started.</p>
        </div>
      )}

      {!loading && dashboard && activeSection === 'posts' && myPosts.length > 0 && (
        <section aria-label="My posts">
          {myPosts.map((post) => (
            <div key={post.id}>
              <PostCard post={post} />
              {(post.moderation_status === 'BLOCKED' || post.moderation_status === 'FLAGGED_FOR_REVIEW') && (
                <div className="dashboard-appeal-action">
                  <button type="button" className="btn btn-secondary" onClick={() => handleAppeal(post.id)}>
                    Request review (appeal)
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {!loading && dashboard && activeSection === 'comments' && (
        <section aria-label="My comments" className="card dashboard-section-card">
          <h2>My comments</h2>
          <UserCommentList comments={myComments} />
        </section>
      )}

      {!loading && dashboard && activeSection === 'pending' && (
        <section aria-label="Pending review items" className="card dashboard-section-card">
          <h2>Pending review</h2>
          <PendingReviewList items={dashboard.pending_items || []} />
        </section>
      )}

      {!loading && dashboard && activeSection === 'history' && (
        <section aria-label="Moderation history" className="card dashboard-section-card">
          <h2>Moderation history</h2>
          {dashboard.moderation_history?.length ? (
            <ModerationHistoryTable history={dashboard.moderation_history} />
          ) : (
            <p className="dashboard-loading" role="status">No moderation history available yet.</p>
          )}
        </section>
      )}
    </main>
  );
};

function StatChip({ label, value, tone }) {
  return (
    <div className={`dashboard-stat dashboard-stat-${tone}`}>
      <span>{label}</span>
      <strong aria-label={`${label}: ${value}`}>
        {value}
      </strong>
    </div>
  );
}
