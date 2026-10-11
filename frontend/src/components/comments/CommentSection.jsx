import React, { useCallback, useContext, useEffect, useState } from 'react';
import { api } from '../../services/api';
import { AuthContext } from '../../context/AuthContext';
import { Avatar } from '../common/Avatar';
import { MessageSquare, Send, ShieldCheck, AlertCircle, Heart, Trash2 } from 'lucide-react';

const formatTime = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
};

export const CommentSection = ({ postId }) => {
  const { user } = useContext(AuthContext);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const fetchComments = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setComments(await api.listComments(postId));
    } catch {
      setError('Comments could not be loaded. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => { fetchComments(); }, [fetchComments]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!newComment.trim() || submitting) return;
    setSubmitting(true);
    setError('');
    setNotice('');
    try {
      const result = await api.createComment(postId, newComment.trim());
      setNewComment('');
      if (result.moderation_status === 'APPROVED') {
        setNotice('Your comment was published.');
        await fetchComments();
      } else if (result.moderation_status === 'FLAGGED_FOR_REVIEW') {
        setNotice('Your comment was submitted for human review and is not visible yet.');
      } else {
        setNotice('Your comment was not published. See its moderation result in your dashboard.');
      }
    } catch (err) {
      const message = err.message || '';
      setError(message === 'Failed to fetch' ? 'OpenVibe could not reach the server. Check your connection and try again.' : message || 'Your comment could not be submitted. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleLike = async (comment) => {
    if (!user) return;
    setError('');
    try {
      const result = comment.liked_by_me ? await api.unlikeComment(comment.id) : await api.likeComment(comment.id);
      setComments((items) => items.map((item) => item.id === comment.id ? { ...item, liked_by_me: result.liked, like_count: result.like_count } : item));
    } catch (err) { setError(err.message || 'Your reaction could not be saved.'); }
  };

  const removeComment = async (comment) => {
    if (!window.confirm('Delete your comment? This cannot be undone.')) return;
    try {
      await api.deleteComment(comment.id);
      setComments((items) => items.filter((item) => item.id !== comment.id));
      setNotice('Your comment was deleted.');
      setError('');
    } catch (err) { setError(err.message || 'Your comment could not be deleted.'); }
  };

  return (
    <section className="comment-section" aria-label="Comments">
      <h3><MessageSquare size={16} aria-hidden="true" /> Comments <span className="count-pill">{loading ? '…' : comments.length}</span></h3>
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={16} /> {error}<button type="button" className="text-link-button" onClick={fetchComments}>Retry</button></div>}
      {notice && <div className="notice-card notice-card-success" role="status"><ShieldCheck size={16} /> {notice}</div>}

      {user ? <form className="comment-form" onSubmit={handleSubmit}>
        <Avatar name={user.username} size="sm" />
        <label className="sr-only" htmlFor={`comment-${postId}`}>Write a comment</label>
        <input id={`comment-${postId}`} type="text" className="form-input" value={newComment} onChange={(event) => setNewComment(event.target.value)} placeholder="Add a thoughtful comment…" maxLength={1000} required />
        <button type="submit" className="btn btn-primary btn-sm" disabled={submitting || !newComment.trim()}><Send size={15} aria-hidden="true" /> {submitting ? 'Checking…' : 'Comment'}</button>
      </form> : <p className="comment-signin">Sign in to leave a comment. Comments are checked before they appear.</p>}

      {loading && <div className="comment-loading" role="status">Loading comments…</div>}
      {!loading && !error && comments.length === 0 && <p className="comment-empty">No comments yet. Start the conversation.</p>}
      {!loading && comments.map((comment) => <article className="comment-item" key={comment.id}>
        <Avatar name={comment.author_full_name || comment.author_username || 'OpenVibe member'} size="sm" />
        <div className="comment-bubble"><div className="comment-meta"><strong>{comment.author_full_name || comment.author_username || 'OpenVibe member'}</strong><time dateTime={comment.created_at}>{formatTime(comment.created_at)}</time></div><p>{comment.content}</p><button className={`comment-like ${comment.liked_by_me ? 'active' : ''}`} type="button" disabled={!user} title={!user ? 'Sign in to like comments' : undefined} aria-pressed={comment.liked_by_me} onClick={() => toggleLike(comment)}><Heart size={14} /> Like{comment.like_count > 0 ? ` · ${comment.like_count}` : ''}</button>{user?.id === comment.author_id && <button className="comment-like comment-delete" type="button" onClick={() => removeComment(comment)}><Trash2 size={14} /> Delete</button>}</div>
      </article>)}
    </section>
  );
};
