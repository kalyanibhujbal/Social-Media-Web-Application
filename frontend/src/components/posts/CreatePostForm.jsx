import React, { useContext, useState } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { api } from '../../services/api';
import { Avatar } from '../common/Avatar';
import { Image, Video, CalendarDays, FileText, Send, Sparkles, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';

const unavailablePostTypes = [
  { label: 'Photo', Icon: Image },
  { label: 'Video', Icon: Video },
  { label: 'Event', Icon: CalendarDays },
  { label: 'Article', Icon: FileText },
];

export const CreatePostForm = ({ onPostCreated }) => {
  const { user } = useContext(AuthContext);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastResult, setLastResult] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!content.trim() || loading) return;

    setLoading(true);
    setError('');
    setLastResult(null);
    try {
      const post = await api.createPost(content.trim());
      setContent('');
      setLastResult(post);
      onPostCreated?.(post);
    } catch (err) {
      const message = err.message || '';
      setError(message === 'Failed to fetch' || message.includes('NetworkError')
        ? 'OpenVibe could not reach the server. Check your connection and try again.'
        : message || 'Your post could not be submitted. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const prediction = lastResult?.ai_prediction;
  const status = lastResult?.moderation_status;
  const published = status === 'APPROVED';
  const submittedForReview = status === 'FLAGGED_FOR_REVIEW';

  return (
    <section className="card create-post-card" aria-label="Create a post">
      <form onSubmit={handleSubmit}>
        <div className="composer-main">
          <Avatar name={user?.full_name || user?.username || 'OpenVibe member'} size="lg" />
          <div className="composer-field-wrap">
            <label htmlFor="post-content" className="sr-only">Your post</label>
            <textarea
              id="post-content"
              className="form-textarea composer-textarea"
              rows="3"
              placeholder={`What would you like to share, ${user?.full_name?.split(' ')[0] || user?.username || 'there'}?`}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              maxLength={2000}
              required
            />
            <div className="composer-meta">
              <span><Sparkles size={14} aria-hidden="true" /> Text posts are screened before publication</span>
              <span>{content.length} / 2,000</span>
            </div>
          </div>
        </div>

        {loading && <div className="notice-card notice-card-info composer-feedback" role="status"><span className="spinner" /> Analyzing content and submitting your post…</div>}
        {error && <div className="notice-card notice-card-error composer-feedback" role="alert"><AlertCircle size={17} aria-hidden="true" /> {error}</div>}
        {lastResult && <div className={`notice-card ${published ? 'notice-card-success' : 'notice-card-warning'} composer-feedback`} role="status">
          {published ? <CheckCircle2 size={18} aria-hidden="true" /> : <ShieldAlert size={18} aria-hidden="true" />}
          <div>
            <strong>{published ? 'Your post is live.' : submittedForReview ? 'Your post is waiting for human review.' : 'Your post was not published.'}</strong>
            <p>{prediction?.label && <>AI prediction: <b>{prediction.label}</b>{typeof prediction.confidence === 'number' && <> · {Math.round(prediction.confidence * 100)}% confidence ({prediction.confidence_level || 'unrated'})</>}.</>} {submittedForReview && 'A moderator will review it. AI predictions can be inaccurate.'}</p>
          </div>
        </div>}

        <div className="composer-toolbar">
          <div className="composer-tools" aria-label="Additional post formats">
            {unavailablePostTypes.map(({ label, Icon }) => <button type="button" className="composer-tool" key={label} disabled title="This backend currently supports text posts only">
              <Icon size={17} aria-hidden="true" /><span>{label}</span>
            </button>)}
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading || !content.trim()}>
            <Send size={16} aria-hidden="true" /> {loading ? 'Analyzing…' : 'Publish post'}
          </button>
        </div>
      </form>
    </section>
  );
};
