import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { api } from '../../services/api';
import { ModerationBadge } from '../moderation/ModerationBadge';
import { ExplanationModal } from '../moderation/ExplanationModal';
import { CommentSection } from '../comments/CommentSection';
import { Avatar } from '../common/Avatar';
import {
  ThumbsUp, MessageSquare, Share2, Bookmark, CircleHelp, AlertCircle,
  ShieldCheck, Trash2, CalendarDays, MapPin, BookOpen,
  ChevronLeft, ChevronRight, Expand, X,
} from 'lucide-react';

const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
};

export const PostCard = ({ post, onSavedStateChange, onOpenProfile, onOpenArticle }) => {
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
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [mediaItems, setMediaItems] = useState(post.media || []);
  const [removingMedia, setRemovingMedia] = useState('');
  const [lightboxIndex, setLightboxIndex] = useState(null);
  const isLightboxOpen = lightboxIndex !== null;
  const [articleExpanded, setArticleExpanded] = useState(false);

  const prediction = post.ai_prediction;
  const isOwner = user && user.id === post.author_id;
  const scoreEntries = prediction?.probabilities && typeof prediction.probabilities === 'object'
    ? Object.entries(prediction.probabilities).filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
    : [];
  const ruleIndicators = Array.isArray(prediction?.explanation?.top_words) ? prediction.explanation.top_words : [];
  const explanationAvailable = scoreEntries.length > 0 || ruleIndicators.length > 0;
  const explanationText = typeof post.moderation_explanation === 'string' ? post.moderation_explanation.trim() : '';
  const showReviewStatus = isOwner && post.moderation_status && post.moderation_status !== 'APPROVED';
  const showModerationExplanation = explanationText && !/no text was submitted|media is not analyzed by the moderation model/i.test(explanationText);
  const visibleMedia = mediaItems.slice(0, 4);
  const hiddenMediaCount = Math.max(0, mediaItems.length - visibleMedia.length);

  useEffect(() => {
    if (lightboxIndex === null) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setLightboxIndex(null);
      if (event.key === 'ArrowLeft') setLightboxIndex((index) => (index - 1 + mediaItems.length) % mediaItems.length);
      if (event.key === 'ArrowRight') setLightboxIndex((index) => (index + 1) % mediaItems.length);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxIndex, mediaItems.length]);

  useEffect(() => {
    if (!isLightboxOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previousOverflow; };
  }, [isLightboxOpen]);

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

  const deleteOwnPost = async () => {
    if (!window.confirm('Delete this post and its attached media? This cannot be undone.')) return;
    setDeleteBusy(true);
    setActionError('');
    try {
      await api.deletePost(post.id);
      setDeleted(true);
    } catch (error) {
      setActionError(error.message || 'This post could not be deleted.');
    } finally {
      setDeleteBusy(false);
    }
  };

  const removeOwnMedia = async (item) => {
    if (!window.confirm('Remove this media from your post? This cannot be undone.')) return;
    setRemovingMedia(item.filename);
    setActionError('');
    try {
      await api.deletePostMedia(post.id, item.filename);
      setMediaItems((items) => items.filter((mediaItem) => mediaItem.filename !== item.filename));
    } catch (error) {
      setActionError(error.message || 'This media could not be removed.');
    } finally {
      setRemovingMedia('');
    }
  };

  if (deleted) return null;

  return (
    <article id={`post-${post.id}`} className="post-card" aria-label={`Post by ${post.author_full_name || post.author_username}`}>
      <header className="post-header">
        <div className="post-author">
          <Avatar name={post.author_full_name || post.author_username || 'OpenVibe member'} src={post.author_avatar_url} size="lg" />
          <div>
            {onOpenProfile ? <button type="button" className="post-author-name post-author-profile-link" onClick={() => onOpenProfile(post.author_id)}>{post.author_full_name || post.author_username || 'OpenVibe member'}</button> : <div className="post-author-name">{post.author_full_name || post.author_username || 'OpenVibe member'}</div>}
            <div className="post-author-headline">{post.author_full_name ? `@${post.author_username}` : 'OpenVibe community member'}</div>
            <div className="post-timestamp"><time dateTime={post.created_at}>{formatDate(post.created_at)}</time>{post.language && <> · {post.language.toUpperCase()}</>}{post.language_supported === false && <span className="language-review-note" title={post.language_notice || 'The configured model is not verified for this language.'}> · language routed for review</span>}</div>
          </div>
        </div>
        <div className="post-header-actions">
          {showReviewStatus && <ModerationBadge prediction={prediction} status={post.moderation_status} />}
          {isOwner && <button type="button" className="btn btn-quiet btn-icon post-delete-button" disabled={deleteBusy} onClick={deleteOwnPost} aria-label={`Delete ${post.content_type?.toLowerCase() || 'post'}`} title="Delete your post and media"><Trash2 size={16} /></button>}
        </div>
      </header>

      {post.content_type === 'EVENT' && <section className="event-post-details">
        <div className="content-type-label"><CalendarDays size={15} /> OpenVibe event</div>
        <h2>{post.event?.title || 'Community event'}</h2>
        <p className="post-content">{post.content}</p>
        <div className="event-meta-row">
          <span><CalendarDays size={15} />{post.event?.event_date ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${post.event.event_date}T00:00:00`)) : 'Date to be announced'}{post.event?.event_time ? ` · ${post.event.event_time}` : ''}</span>
          {post.event?.location && <span><MapPin size={15} />{post.event.location}</span>}
        </div>
      </section>}

      {post.content_type === 'ARTICLE' && <section className="article-post-preview">
        <div className="content-type-label"><BookOpen size={15} /> Article</div>
        <h2>{post.article?.title || 'OpenVibe article'}</h2>
        <p className="post-content article-excerpt">{articleExpanded || onOpenArticle ? post.content : `${post.content.slice(0, 360)}${post.content.length > 360 ? '…' : ''}`}</p>
        {post.content.length > 360 && !onOpenArticle && <button type="button" className="text-link-button article-read-button" onClick={() => setArticleExpanded((expanded) => !expanded)}>{articleExpanded ? 'Show less' : 'Continue reading'}</button>}
        {onOpenArticle && <button type="button" className="btn btn-outline btn-sm article-read-button" onClick={() => onOpenArticle(post)}><BookOpen size={15} /> Read article</button>}
      </section>}

      {post.content_type !== 'EVENT' && post.content_type !== 'ARTICLE' && post.content && <p className="post-content">{post.content}</p>}

      {mediaItems.length > 0 && <div className={`post-media-gallery ${mediaItems.length > 1 ? 'post-media-multiple' : ''}`} aria-label="Post media">
        {visibleMedia.map((item, index) => <div className={`post-media-item ${item.media_type === 'video' ? 'post-video-item' : ''}`} key={item.filename}>
          {item.media_type === 'video'
            ? <>
              <video src={api.mediaUrl(item.url)} controls playsInline preload="metadata" crossOrigin="use-credentials" aria-label={`Video shared by ${post.author_full_name || post.author_username}`} />
              <button type="button" className="media-view-button" onClick={() => setLightboxIndex(index)} aria-label="Open video in media viewer"><Expand size={16} /></button>
            </>
            : <button type="button" className="post-media-open" onClick={() => setLightboxIndex(index)} aria-label={`View image ${index + 1} of ${mediaItems.length}`}>
              <img src={api.mediaUrl(item.url)} alt={post.content_type === 'ARTICLE' ? `Cover image for ${post.article?.title || 'article'}` : post.content ? `Image shared with post: ${post.content.slice(0, 100)}` : `Image shared by ${post.author_full_name || post.author_username}`} loading="lazy" crossOrigin="use-credentials" />
            </button>}
          {isOwner && <button type="button" className="media-remove-button" disabled={removingMedia === item.filename} onClick={() => removeOwnMedia(item)} aria-label={`Remove media ${index + 1} from your post`} title="Remove this media"><Trash2 size={14} /></button>}
          {index === visibleMedia.length - 1 && hiddenMediaCount > 0 && <button type="button" className="post-media-more" onClick={() => setLightboxIndex(index)} aria-label={`View ${hiddenMediaCount} more media items`}>
            <strong>+{hiddenMediaCount} more</strong><span>View all media</span>
          </button>}
        </div>)}
      </div>}

      {showReviewStatus && <section className="post-owner-review-status" aria-label="Your post review status">
        {showModerationExplanation && <p>{explanationText}</p>}
        <div className="post-moderation-actions">
          {explanationAvailable && <button type="button" className="btn btn-quiet btn-sm" onClick={() => setShowExplanation(true)}>
            <CircleHelp size={15} aria-hidden="true" /> View review details
          </button>}
          {isOwner && post.moderation_status !== 'APPROVED' && <button type="button" className="btn btn-outline btn-sm" onClick={() => setShowAppealForm((shown) => !shown)}>Request human review</button>}
        </div>
      </section>}

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
      {lightboxIndex !== null && mediaItems[lightboxIndex] && <div className="media-lightbox" role="dialog" aria-modal="true" aria-label="Post media viewer" onClick={() => setLightboxIndex(null)}>
        <div className="media-lightbox-content" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="media-lightbox-close" onClick={() => setLightboxIndex(null)} aria-label="Close media viewer"><X size={21} /></button>
          {mediaItems.length > 1 && <button type="button" className="media-lightbox-nav media-lightbox-previous" onClick={() => setLightboxIndex((index) => (index - 1 + mediaItems.length) % mediaItems.length)} aria-label="Previous media"><ChevronLeft size={24} /></button>}
          {mediaItems[lightboxIndex].media_type === 'video'
            ? <video key={mediaItems[lightboxIndex].filename} className="media-lightbox-media" src={api.mediaUrl(mediaItems[lightboxIndex].url)} controls autoPlay playsInline crossOrigin="use-credentials" />
            : <img className="media-lightbox-media" src={api.mediaUrl(mediaItems[lightboxIndex].url)} alt={`Media ${lightboxIndex + 1} of ${mediaItems.length}`} crossOrigin="use-credentials" />}
          {mediaItems.length > 1 && <button type="button" className="media-lightbox-nav media-lightbox-next" onClick={() => setLightboxIndex((index) => (index + 1) % mediaItems.length)} aria-label="Next media"><ChevronRight size={24} /></button>}
          <div className="media-lightbox-count">{lightboxIndex + 1} / {mediaItems.length}</div>
        </div>
      </div>}
    </article>
  );
};
