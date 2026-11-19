import React, { useContext, useEffect, useRef, useState } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { api } from '../../services/api';
import { Avatar } from '../common/Avatar';
import {
  AlertCircle, CalendarDays, CheckCircle2, FileText, Image, MapPin,
  Send, ShieldAlert, X,
} from 'lucide-react';

const FORMATS = [
  { id: 'post', label: 'Post', Icon: FileText },
  { id: 'media', label: 'Media', Icon: Image },
  { id: 'event', label: 'Event', Icon: CalendarDays },
  { id: 'article', label: 'Article', Icon: FileText },
];

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp']);
const VIDEO_EXTENSIONS = new Set(['mp4', 'webm']);
const IMAGE_LIMIT = 10 * 1024 * 1024;
const VIDEO_LIMIT = 100 * 1024 * 1024;

const fileExtension = (file) => file.name.split('.').pop()?.toLowerCase() || '';
const formatSize = (size) => size >= 1024 * 1024
  ? `${(size / (1024 * 1024)).toFixed(1)} MB`
  : `${Math.max(1, Math.round(size / 1024))} KB`;

export const CreatePostForm = ({ onPostCreated }) => {
  const { user } = useContext(AuthContext);
  const [format, setFormat] = useState('post');
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [eventTime, setEventTime] = useState('');
  const [location, setLocation] = useState('');
  const [selectedMedia, setSelectedMedia] = useState([]);
  const [coverImage, setCoverImage] = useState(null);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const selectedMediaRef = useRef([]);
  const coverImageRef = useRef(null);

  useEffect(() => () => {
    selectedMediaRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    if (coverImageRef.current) URL.revokeObjectURL(coverImageRef.current.previewUrl);
  }, []);

  const replaceSelectedMedia = (items) => {
    selectedMediaRef.current = items;
    setSelectedMedia(items);
  };

  const clearSelectedMedia = () => {
    selectedMediaRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    replaceSelectedMedia([]);
  };

  const clearCoverImage = () => {
    if (coverImageRef.current) URL.revokeObjectURL(coverImageRef.current.previewUrl);
    coverImageRef.current = null;
    setCoverImage(null);
  };

  const chooseFormat = (nextFormat) => {
    if (nextFormat !== format) {
      clearSelectedMedia();
      clearCoverImage();
      setError('');
      setLastResult(null);
      setFormat(nextFormat);
    }
  };

  const handleMediaSelection = (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (!files.length) return;
    if (files.length + selectedMedia.length > 5) {
      setError('A post can contain up to five images and videos combined.');
      return;
    }
    const invalid = files.find((file) => {
      const extension = fileExtension(file);
      const isImage = IMAGE_EXTENSIONS.has(extension);
      const isVideo = VIDEO_EXTENSIONS.has(extension);
      const maxSize = isVideo ? VIDEO_LIMIT : IMAGE_LIMIT;
      return (!isImage && !isVideo) || file.size > maxSize || file.size === 0;
    });
    if (invalid) {
      const isVideo = VIDEO_EXTENSIONS.has(fileExtension(invalid));
      setError(isVideo
        ? 'Videos must be MP4 or WEBM and smaller than 100 MB.'
        : 'Images must be JPG, PNG, or WEBP and smaller than 10 MB each.');
      return;
    }
    setError('');
    replaceSelectedMedia([
      ...selectedMedia,
      ...files.map((file) => ({ file, previewUrl: URL.createObjectURL(file) })),
    ]);
  };

  const handleCoverSelection = (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!IMAGE_EXTENSIONS.has(fileExtension(file)) || file.size > IMAGE_LIMIT || file.size === 0) {
      setError('Choose a JPG, PNG, or WEBP cover image smaller than 10 MB.');
      return;
    }
    setError('');
    clearCoverImage();
    const selection = { file, previewUrl: URL.createObjectURL(file) };
    coverImageRef.current = selection;
    setCoverImage(selection);
  };

  const resetForm = () => {
    setContent('');
    setTitle('');
    setEventDate('');
    setEventTime('');
    setLocation('');
    clearSelectedMedia();
    clearCoverImage();
  };

  const submit = async (event) => {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setProgress(0);
    setError('');
    setLastResult(null);
    try {
      let post;
      if (format === 'post') {
        post = await api.createPost(content.trim());
      } else if (format === 'media') {
        if (!selectedMedia.length) throw new Error('Choose at least one photo or video first.');
        post = await api.createMediaPost(content.trim(), selectedMedia.map((item) => item.file), setProgress);
      } else if (format === 'event') {
        post = await api.createEvent({
          title: title.trim(),
          description: content.trim(),
          eventDate,
          eventTime,
          location: location.trim(),
          coverImage: coverImage?.file,
        }, setProgress);
      } else {
        post = await api.createArticle({
          title: title.trim(),
          content: content.trim(),
          coverImage: coverImage?.file,
        }, setProgress);
      }

      setLastResult(post);
      onPostCreated?.(post);
      if (post.moderation_status === 'APPROVED') resetForm();
    } catch (err) {
      setError(err.message || 'Your content could not be submitted. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const published = lastResult?.moderation_status === 'APPROVED';
  const submittedForReview = lastResult?.moderation_status === 'FLAGGED_FOR_REVIEW';
  const resultExplanation = typeof lastResult?.moderation_explanation === 'string'
    ? lastResult.moderation_explanation.trim()
    : '';
  const showResultExplanation = !published && resultExplanation
    && !/no text was submitted|media is not analyzed by the moderation model/i.test(resultExplanation);
  const isMediaPost = format === 'media';
  const mediaAccept = '.jpg,.jpeg,.png,.webp,.mp4,.webm,image/jpeg,image/png,image/webp,video/mp4,video/webm';

  return (
    <section className="card create-post-card" aria-label="Create content">
      <form onSubmit={submit}>
        <div className="content-format-tabs" role="group" aria-label="Choose what to create">
          {FORMATS.map(({ id, label, Icon }) => <button
            type="button"
            className={`content-format-tab ${format === id ? 'active' : ''}`}
            data-content-format={id}
            aria-pressed={format === id}
            key={id}
            onClick={() => chooseFormat(id)}
          ><Icon size={16} aria-hidden="true" />{label}</button>)}
        </div>

        <div className="composer-main">
          <Avatar name={user?.full_name || user?.username || 'OpenVibe member'} src={user?.avatar_url} size="lg" />
          <div className="composer-field-wrap">
            {format === 'event' && <>
              <label className="form-label" htmlFor="event-title">Event title</label>
              <input id="event-title" className="form-input content-title-input" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={140} required placeholder="Give your event a name" />
              <div className="event-fields-grid">
                <div><label className="form-label" htmlFor="event-date">Date</label><input id="event-date" className="form-input" type="date" value={eventDate} onChange={(event) => setEventDate(event.target.value)} required /></div>
                <div><label className="form-label" htmlFor="event-time">Time</label><input id="event-time" className="form-input" type="time" value={eventTime} onChange={(event) => setEventTime(event.target.value)} required /></div>
                <div className="event-location-field"><label className="form-label" htmlFor="event-location">Location</label><div className="input-with-icon"><MapPin size={16} aria-hidden="true" /><input id="event-location" className="form-input" value={location} onChange={(event) => setLocation(event.target.value)} maxLength={180} required placeholder="Venue or online" /></div></div>
              </div>
            </>}
            {format === 'article' && <>
              <label className="form-label" htmlFor="article-title">Article title</label>
              <input id="article-title" className="form-input content-title-input" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={180} required placeholder="Write a clear, compelling headline" />
            </>}

            <label htmlFor="post-content" className="sr-only">
              {format === 'article' ? 'Article text' : format === 'event' ? 'Event description' : 'Your post or caption'}
            </label>
            <textarea
              id="post-content"
              className="form-textarea composer-textarea"
              rows={format === 'article' ? 8 : format === 'event' ? 4 : 3}
              placeholder={format === 'article'
                ? 'Write your article. Separate paragraphs with a blank line.'
                : format === 'event'
                  ? 'Tell people what to expect at your event…'
                  : format === 'media'
                    ? 'Add a caption (optional)…'
                    : `What would you like to share, ${user?.full_name?.split(' ')[0] || user?.username || 'there'}?`}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              maxLength={format === 'article' ? 20000 : 2000}
              required={format === 'post' || format === 'event' || format === 'article'}
            />
            <div className="composer-meta">
              <span>{content.length} / {format === 'article' ? '20,000' : '2,000'}</span>
            </div>
          </div>
        </div>

        {isMediaPost && <div className="media-picker-panel">
          <label className="btn btn-outline btn-sm media-picker-button">
              <Image size={16} />
              {selectedMedia.length ? 'Add more media' : 'Choose photos or videos'}
              <input type="file" accept={mediaAccept} multiple onChange={handleMediaSelection} hidden />
          </label>
            <span className="muted-note">JPG, JPEG, PNG, WEBP · 10 MB each · MP4 or WEBM · 100 MB each · up to 5 files</span>
            {selectedMedia.length > 0 && <div className="media-preview-grid">
            {selectedMedia.map(({ file, previewUrl }, index) => <div className="media-preview-item" key={`${file.name}-${file.lastModified}-${index}`}>
                {VIDEO_EXTENSIONS.has(fileExtension(file))
                ? <video src={previewUrl} controls preload="metadata" aria-label={`Preview of ${file.name}`} />
                : <img src={previewUrl} alt={`Selected image ${index + 1}: ${file.name}`} />}
              <span>{file.name} · {formatSize(file.size)}</span>
              <button type="button" className="media-remove-button" aria-label={`Remove ${file.name}`} onClick={() => {
                URL.revokeObjectURL(previewUrl);
                replaceSelectedMedia(selectedMedia.filter((item) => item.previewUrl !== previewUrl));
              }}><X size={15} /></button>
            </div>)}
          </div>}
        </div>}

        {(format === 'event' || format === 'article') && <div className="media-picker-panel cover-image-panel">
          <label className="btn btn-outline btn-sm media-picker-button">
            <Image size={16} /> {coverImage ? 'Replace cover image' : 'Add cover image (optional)'}
            <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" onChange={handleCoverSelection} hidden />
          </label>
          {coverImage && <div className="cover-image-preview">
            <img src={coverImage.previewUrl} alt="Selected cover preview" />
            <span>{coverImage.file.name} · {formatSize(coverImage.file.size)}</span>
            <button type="button" className="media-remove-button" aria-label="Remove cover image" onClick={clearCoverImage}><X size={15} /></button>
          </div>}
        </div>}

        {loading && <div className="notice-card notice-card-info composer-feedback" role="status">
          <span className="spinner" />
          <span>{isMediaPost || coverImage ? `Uploading and checking text… ${progress}%` : 'Analyzing text and publishing…'}</span>
          {(isMediaPost || coverImage) && <progress className="upload-progress" value={progress} max="100" aria-label={`Upload progress ${progress}%`} />}
        </div>}
        {error && <div className="notice-card notice-card-error composer-feedback" role="alert"><AlertCircle size={17} aria-hidden="true" /> {error}</div>}
        {lastResult && <div className={`notice-card ${published ? 'notice-card-success' : 'notice-card-warning'} composer-feedback`} role="status">
          {published ? <CheckCircle2 size={18} aria-hidden="true" /> : <ShieldAlert size={18} aria-hidden="true" />}
          <div>
            <strong>{published ? 'Your content is live.' : submittedForReview ? 'Your content is waiting for human review.' : 'Your content was not published.'}</strong>
            {showResultExplanation && <p>{resultExplanation}</p>}
          </div>
        </div>}

        <div className="composer-toolbar">
          <button type="submit" className="btn btn-primary" disabled={loading || (isMediaPost && selectedMedia.length === 0)}>
            <Send size={16} aria-hidden="true" /> {loading ? 'Publishing…' : format === 'event' ? 'Publish event' : format === 'article' ? 'Publish article' : 'Publish post'}
          </button>
        </div>
      </form>
    </section>
  );
};
