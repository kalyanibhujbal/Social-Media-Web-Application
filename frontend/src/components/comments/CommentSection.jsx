import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import { AuthContext } from '../../context/AuthContext';
import { Avatar } from '../common/Avatar';
import { MessageSquare, Send, ShieldCheck, AlertCircle, Heart, Trash2 } from 'lucide-react';

const formatTime = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
};

const buildCommentTree = (comments) => {
  const nodes = new Map(comments.map((comment) => [comment.id, { ...comment, replies: [] }]));
  const roots = [];
  nodes.forEach((comment) => {
    const parent = comment.parent_comment_id ? nodes.get(comment.parent_comment_id) : null;
    if (parent) parent.replies.push(comment);
    else roots.push(comment);
  });
  return roots;
};

export const CommentSection = ({ postId }) => {
  const { user } = useContext(AuthContext);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [replyContent, setReplyContent] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
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

  const commentTree = useMemo(() => buildCommentTree(comments), [comments]);

  const handleSubmit = async (event, parentCommentId = null) => {
    event.preventDefault();
    const content = (parentCommentId ? replyContent : newComment).trim();
    if (!content || submitting) return;
    setSubmitting(true);
    setError('');
    setNotice('');
    try {
      const result = await api.createComment(postId, content, parentCommentId);
      if (parentCommentId) setReplyContent('');
      else setNewComment('');
      if (result.moderation_status === 'APPROVED') {
        setNotice('Your comment was published.');
        setReplyingTo(null);
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
      await fetchComments();
      setNotice('Your comment was deleted.');
      setError('');
    } catch (err) { setError(err.message || 'Your comment could not be deleted.'); }
  };

  const renderComment = (comment, depth = 0) => (
    <div className="comment-thread" key={comment.id} style={{ marginLeft: `${Math.min(depth * 18, 54)}px` }}>
      <article className="comment-item">
        <Avatar name={comment.author_full_name || comment.author_username || 'OpenVibe member'} src={comment.author_avatar_url} size="sm" />
        <div className="comment-bubble">
          <div className="comment-meta"><strong>{comment.author_full_name || comment.author_username || 'OpenVibe member'}</strong><time dateTime={comment.created_at}>{formatTime(comment.created_at)}</time></div>
          <p>{comment.content}</p>
          <button className={`comment-like ${comment.liked_by_me ? 'active' : ''}`} type="button" disabled={!user} title={!user ? 'Sign in to like comments' : undefined} aria-pressed={comment.liked_by_me} onClick={() => toggleLike(comment)}><Heart size={14} /> Like{comment.like_count > 0 ? ` · ${comment.like_count}` : ''}</button>
          <button className="comment-like" type="button" disabled={!user} title={!user ? 'Sign in to reply' : undefined} onClick={() => { setReplyingTo(comment.id); setReplyContent(''); }}><MessageSquare size={14} /> Reply</button>
          {user?.id === comment.author_id && <button className="comment-like comment-delete" type="button" onClick={() => removeComment(comment)}><Trash2 size={14} /> Delete</button>}
        </div>
      </article>
      {replyingTo === comment.id && user && <form className="comment-form comment-reply-form" onSubmit={(event) => handleSubmit(event, comment.id)}>
        <Avatar name={user.full_name || user.username} size="sm" />
        <label className="sr-only" htmlFor={`reply-${postId}-${comment.id}`}>Reply to {comment.author_full_name || comment.author_username}</label>
        <input id={`reply-${postId}-${comment.id}`} type="text" className="form-input" value={replyContent} onChange={(event) => setReplyContent(event.target.value)} placeholder={`Reply to ${comment.author_full_name || comment.author_username}…`} maxLength={1000} required />
        <button type="submit" className="btn btn-primary btn-sm" disabled={submitting || !replyContent.trim()}><Send size={14} /> Reply</button>
        <button type="button" className="btn btn-quiet btn-sm" onClick={() => setReplyingTo(null)}>Cancel</button>
      </form>}
      {comment.replies.length > 0 && <div className="comment-replies">{comment.replies.map((reply) => renderComment(reply, depth + 1))}</div>}
    </div>
  );

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
      {!loading && commentTree.map((comment) => renderComment(comment))}
    </section>
  );
};
