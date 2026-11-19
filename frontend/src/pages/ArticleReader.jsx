import React, { useContext, useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowLeft, BookOpen, Check, Clock3, Heart, Pencil, Send, Trash2 } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';
import { Avatar } from '../components/common/Avatar';
import { CommentSection } from '../components/comments/CommentSection';
import { ModerationBadge } from '../components/moderation/ModerationBadge';
import { api } from '../services/api';

const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(date);
};

const articleParagraphs = (value) => (value || '').trim().split(/\n\s*\n/).filter(Boolean);

export const ArticleReader = ({ article, onBack, onOpenProfile, onArticleUpdated, onArticleDeleted }) => {
  const { user } = useContext(AuthContext);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(article?.article?.title || '');
  const [content, setContent] = useState(article?.content || '');
  const [coverImage, setCoverImage] = useState(null);
  const [coverPreview, setCoverPreview] = useState('');
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [liked, setLiked] = useState(Boolean(article?.liked_by_me));
  const [likeCount, setLikeCount] = useState(article?.like_count || 0);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const commentsRef = useRef(null);
  const coverPreviewRef = useRef('');
  const isOwner = user?.id === article?.author_id;
  const cover = article?.media?.find((item) => item.media_type === 'image');

  useEffect(() => () => {
    if (coverPreviewRef.current) URL.revokeObjectURL(coverPreviewRef.current);
  }, []);

  const chooseCover = (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!['jpg', 'jpeg', 'png', 'webp'].includes(extension) || file.size > 10 * 1024 * 1024 || !file.size) {
      setError('Choose a JPG, PNG, or WEBP cover image smaller than 10 MB.');
      return;
    }
    if (coverPreviewRef.current) URL.revokeObjectURL(coverPreviewRef.current);
    const previewUrl = URL.createObjectURL(file);
    coverPreviewRef.current = previewUrl;
    setCoverImage(file);
    setCoverPreview(previewUrl);
    setError('');
  };

  const saveArticle = async (event) => {
    event.preventDefault();
    setSaving(true);
    setProgress(0);
    setError('');
    setNotice('');
    try {
      const updated = await api.updateArticle(article.id, { title: title.trim(), content: content.trim(), coverImage }, setProgress);
      onArticleUpdated?.(updated);
      setCoverImage(null);
      if (coverPreviewRef.current) URL.revokeObjectURL(coverPreviewRef.current);
      coverPreviewRef.current = '';
      setCoverPreview('');
      setEditing(false);
      setNotice(updated.moderation_status === 'APPROVED' ? 'Article updated and published.' : 'Article updated; its text is awaiting moderation review.');
    } catch (err) {
      setError(err.message || 'The article could not be updated.');
    } finally {
      setSaving(false);
    }
  };

  const toggleLike = async () => {
    if (!user || busy) return;
    setBusy(true);
    setError('');
    try {
      const result = liked ? await api.unlikePost(article.id) : await api.likePost(article.id);
      setLiked(result.liked);
      setLikeCount(result.like_count);
    } catch (err) {
      setError(err.message || 'Your reaction could not be saved.');
    } finally {
      setBusy(false);
    }
  };

  const deleteArticle = async () => {
    if (!window.confirm('Delete this article and its cover image? This cannot be undone.')) return;
    setBusy(true);
    setError('');
    try {
      await api.deletePost(article.id);
      onArticleDeleted?.();
    } catch (err) {
      setError(err.message || 'The article could not be deleted.');
    } finally {
      setBusy(false);
    }
  };

  if (!article) return <main id="main-content" className="container page-shell narrow-page"><section className="card empty-state"><h1>Article unavailable</h1><p>Return to the articles section to choose another story.</p><button className="btn btn-primary" type="button" onClick={onBack}><ArrowLeft size={16} /> Back to articles</button></section></main>;

  return (
    <main id="main-content" className="container page-shell narrow-page">
      <button type="button" className="text-link-button article-back-button" onClick={onBack}><ArrowLeft size={16} /> Back to articles</button>
      {error && <div className="notice-card notice-card-error article-reader-feedback" role="alert"><AlertCircle size={16} />{error}</div>}
      {notice && <div className="notice-card notice-card-success article-reader-feedback" role="status"><Check size={16} />{notice}</div>}
      <article className="card article-reader">
        {editing ? <form onSubmit={saveArticle} className="article-edit-form">
          <label className="form-label" htmlFor="edit-article-title">Article title</label>
          <input id="edit-article-title" className="form-input" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={180} required />
          <label className="form-label" htmlFor="edit-article-content">Article text</label>
          <textarea id="edit-article-content" className="form-textarea" value={content} onChange={(event) => setContent(event.target.value)} maxLength={20000} rows={16} required />
          <p className="form-help">Separate paragraphs with a blank line for easier reading.</p>
          <label className="btn btn-outline btn-sm media-picker-button">
            <BookOpen size={15} /> Replace cover image (optional)
            <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" onChange={chooseCover} hidden />
          </label>
          {(coverPreview || cover) && <div className="article-edit-cover">
            <img src={coverPreview || api.mediaUrl(cover.url)} alt="Article cover preview" crossOrigin="use-credentials" />
            <span>{coverPreview ? 'New cover image selected' : 'Current cover image'}</span>
          </div>}
          {saving && <div className="article-progress" role="status">Saving article… {progress}%<progress value={progress} max="100" aria-label={`Upload progress ${progress}%`} /></div>}
          <div className="article-edit-actions">
            <button type="button" className="btn btn-quiet" onClick={() => { setEditing(false); setTitle(article.article?.title || ''); setContent(article.content || ''); setCoverImage(null); setCoverPreview(''); if (coverPreviewRef.current) URL.revokeObjectURL(coverPreviewRef.current); coverPreviewRef.current = ''; }}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !title.trim() || !content.trim()}><Check size={16} /> {saving ? 'Saving…' : 'Save article'}</button>
          </div>
        </form> : <>
          {cover && <img className="article-reader-cover" src={api.mediaUrl(cover.url)} alt={`Cover image for ${article.article?.title || 'article'}`} crossOrigin="use-credentials" />}
          <div className="article-reader-header">
            <span className="content-type-label"><BookOpen size={15} /> OpenVibe article</span>
            <h1>{article.article?.title || 'OpenVibe article'}</h1>
            <div className="article-byline">
              <button type="button" className="article-author-link" onClick={() => onOpenProfile?.(article.author_id)}>
                <Avatar name={article.author_full_name || article.author_username} src={article.author_avatar_url} size="md" />
                <span><strong>{article.author_full_name || article.author_username}</strong><small>@{article.author_username}</small></span>
              </button>
              <span><Clock3 size={14} /> {formatDate(article.created_at)}</span>
            </div>
            {isOwner && article.moderation_status !== 'APPROVED' && <ModerationBadge prediction={article.ai_prediction} status={article.moderation_status} />}
          </div>
          {editing ? null : <div className="article-reader-body">
            {articleParagraphs(article.content).map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 20)}`}>{paragraph.split('\n').map((line, lineIndex) => <React.Fragment key={lineIndex}>{lineIndex > 0 && <br />}{line}</React.Fragment>)}</p>)}
          </div>}
          <div className="article-reader-actions">
            <button type="button" className={`action-btn ${liked ? 'active' : ''}`} onClick={toggleLike} disabled={!user || busy}><Heart size={17} /><span>{liked ? 'Liked' : 'Like'}{likeCount > 0 ? ` · ${likeCount}` : ''}</span></button>
            <button type="button" className="action-btn" onClick={() => commentsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}><Send size={16} /><span>Join the discussion</span></button>
            {isOwner && <button type="button" className="btn btn-quiet btn-sm" onClick={() => { setEditing(true); setNotice(''); }}><Pencil size={15} /> Edit article</button>}
            {isOwner && <button type="button" className="btn btn-quiet btn-sm article-delete-action" onClick={deleteArticle} disabled={busy}><Trash2 size={15} /> Delete article</button>}
          </div>
          <div ref={commentsRef} className="article-reader-comments"><CommentSection postId={article.id} /></div>
        </>}
      </article>
    </main>
  );
};
