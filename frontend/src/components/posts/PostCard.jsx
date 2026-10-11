import React, { useContext, useState } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { api } from '../../services/api';
import { ModerationBadge } from '../moderation/ModerationBadge';
import { ExplanationModal } from '../moderation/ExplanationModal';
import { CommentSection } from '../comments/CommentSection';
import { Avatar } from '../common/Avatar';
import { ThumbsUp, MessageSquare, Share2, Bookmark, CircleHelp, AlertCircle, ShieldCheck } from 'lucide-react';

const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
};

export const PostCard = ({ post, onSavedStateChange }) => {
  const { user } = useContext(AuthContext);
  const [showExplanation, setShowExplanation] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [appealReason, setAppealReason] = useState('');
  const [appealMsg, setAppealMsg] = useState('');
  const [appealError, setAppealError] = useState('');
  const [appealBusy, setAppealBusy] = useState(false);
  const [showAppealForm, setShowAppealForm] = useState(false);
  const [liked, setLiked] = useState(Boolean(post.liked_by_me));
  const [likeCount, setLikeCount] = useState(post.like_count || 0);
  const [saved, setSaved] = useState(Boolean(post.saved_by_me));
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [shareNotice, setShareNotice] = useState('');

  const prediction = post.ai_prediction;
  const isOwner = user && user.id === post.author_id;
  const explanationAvailable = Boolean(prediction?.explanation || prediction?.probabilities || prediction?.model_name);

  const submitAppeal = async (event) => {
    event.preventDefault();
    if (appealReason.trim().length < 5 || appealBusy) return;
    setAppealBusy(true);
    setAppealError('');
    setAppealMsg('');
    try {
      await api.appealPost(post.id, appealReason.trim());
      setAppealMsg('Your request was sent to the moderation review queue.');
      setShowAppealForm(false);
    } catch (error) {
      setAppealError(error.message || 'Your review request could not be submitted. Please try again.');
    } finally {
      setAppealBusy(false);
    }
  };

  const toggleLike = async () => {
    if (!user || actionBusy) return;
    setActionBusy(true);
    setActionError('');
    try {
      const result = liked ? await api.unlikePost(post.id) : await api.likePost(post.id);
      setLiked(result.liked);
      setLikeCount(result.like_count);
    } catch (error) { setActionError(error.message || 'Your reaction could not be saved.'); }
    finally { setActionBusy(false); }
  };

  const toggleSave = async () => {
    if (!user || actionBusy) return;
    setActionBusy(true);
    setActionError('');
    try {
      if (saved) await api.unsavePost(post.id); else await api.savePost(post.id);
      setSaved(!saved);
      onSavedStateChange?.(post.id, !saved);
    } catch (error) { setActionError(error.message || 'Your saved posts could not be updated.'); }
    finally { setActionBusy(false); }
  };

  const sharePost = async () => {
    setActionError('');
    setShareNotice('');
    const url = `${window.location.origin}${window.location.pathname}#post-${post.id}`;
    try {
      if (navigator.share) await navigator.share({ title: `OpenVibe post by ${post.author_username}`, url });
      else if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(url); setShareNotice('Post link copied.'); }
      else setActionError('Link sharing is not available in this browser.');
    } catch (error) {
      if (error.name !== 'AbortError') setActionError('The post link could not be shared.');
    }
  };

  return (
    <article id={`post-${post.id}`} className="post-card" aria-label={`Post by ${post.author_full_name || post.author_username}`}>
      <header className="post-header">
        <div className="post-author">
          <Avatar name={post.author_full_name || post.author_username || 'OpenVibe member'} size="lg" />
          <div>
            <div className="post-author-name">{post.author_full_name || post.author_username || 'OpenVibe member'}</div>
            <div className="post-author-headline">{post.author_full_name ? `@${post.author_username}` : 'OpenVibe community member'}</div>
            <div className="post-timestamp"><time dateTime={post.created_at}>{formatDate(post.created_at)}</time>{post.language && <> · {post.language.toUpperCase()}</>}{post.language_supported === false && <span className="language-review-note" title={post.language_notice || 'The configured model is not verified for this language.'}> · language routed for review</span>}</div>
          </div>
        </div>
        <ModerationBadge prediction={prediction} status={post.moderation_status} />
      </header>

      <p className="post-content">{post.content}</p>

      <section className="post-moderation-box" aria-label="Moderation information">
        <div className="post-moderation-summary">
          <ShieldCheck size={16} aria-hidden="true" />
          <div><strong>{post.moderation_status?.replaceAll('_', ' ') || 'Moderation status unavailable'}</strong>
            {post.moderation_explanation && <p>{post.moderation_explanation}</p>}
          </div>
        </div>
        <div className="post-moderation-actions">
          {explanationAvailable ? <button type="button" className="btn btn-quiet btn-sm" onClick={() => setShowExplanation(true)}>
            <CircleHelp size={15} aria-hidden="true" /> View explanation
          </button> : <span className="muted-note">No explanation details were returned for this post.</span>}
          {isOwner && post.moderation_status !== 'APPROVED' && <button type="button" className="btn btn-outline btn-sm" onClick={() => setShowAppealForm((shown) => !shown)}>Request human review</button>}
        </div>
      </section>

      {appealMsg && <div className="notice-card notice-card-success" role="status"><ShieldCheck size={16} /> {appealMsg}</div>}
      {appealError && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={16} /> {appealError}</div>}
      {actionError && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={16} /> {actionError}</div>}
      {shareNotice && <div className="notice-card notice-card-success" role="status">{shareNotice}</div>}
      {showAppealForm && <form onSubmit={submitAppeal} className="appeal-form">
        <label className="form-label" htmlFor={`appeal-${post.id}`}>Why should a moderator review this post?</label>
        <textarea id={`appeal-${post.id}`} className="form-textarea" rows="3" maxLength={1000} minLength={5} value={appealReason} onChange={(event) => setAppealReason(event.target.value)} required />
        <div className="appeal-form-actions"><button type="button" className="btn btn-quiet btn-sm" onClick={() => setShowAppealForm(false)}>Cancel</button><button type="submit" className="btn btn-primary btn-sm" disabled={appealBusy || appealReason.trim().length < 5}>{appealBusy ? 'Sending…' : 'Submit request'}</button></div>
      </form>}

      <div className="post-actions" aria-label="Post actions">
        <button className={`action-btn ${liked ? 'active' : ''}`} type="button" disabled={!user || actionBusy} title={!user ? 'Sign in to like this post' : undefined} aria-pressed={liked} onClick={toggleLike}><ThumbsUp size={17} /><span>{liked ? 'Liked' : 'Like'}{likeCount > 0 ? ` · ${likeCount}` : ''}</span></button>
        <button className={`action-btn ${showComments ? 'active' : ''}`} type="button" onClick={() => setShowComments((shown) => !shown)} aria-expanded={showComments}><MessageSquare size={17} /><span>Comment</span></button>
        <button className="action-btn" type="button" onClick={sharePost}><Share2 size={17} /><span>Share</span></button>
        <button className={`action-btn ${saved ? 'active' : ''}`} type="button" disabled={!user || actionBusy} title={!user ? 'Sign in to save this post' : undefined} aria-pressed={saved} onClick={toggleSave}><Bookmark size={17} /><span>{saved ? 'Saved' : 'Save'}</span></button>
      </div>

      {showComments && <CommentSection postId={post.id} />}
      {showExplanation && <ExplanationModal post={post} onClose={() => setShowExplanation(false)} />}
    </article>
  );
};
