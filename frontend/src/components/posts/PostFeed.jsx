import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';
import { PostCard } from './PostCard';
import { FileText, Globe2, Heart, Play, RefreshCw, Search, X } from 'lucide-react';

const EXPLORE_PAGE_SIZE = 24;

const getFeedError = (error) => {
  const message = error.message || '';
  return message === 'Failed to fetch' || message.includes('NetworkError')
    ? 'The community API is unreachable. Check that the backend is running and try again.'
    : message || 'We could not load the community feed. Please try again.';
};

const ExploreTile = ({ post, index, onClick }) => {
  const media = post.media?.[0];
  const isVideo = media?.media_type === 'video';
  const caption = post.content || post.article?.title || post.event?.title || '';
  const author = post.author_full_name || post.author_username || 'OpenVibe member';

  return (
    <button
      type="button"
      className={`explore-post-tile ${index % 10 === 4 ? 'explore-post-tile-featured' : ''}`}
      onClick={onClick}
      aria-label={`Open post by ${author}${caption ? `: ${caption.slice(0, 100)}` : ''}`}
    >
      {media
        ? isVideo
          ? <video src={api.mediaUrl(media.url)} muted autoPlay loop playsInline preload="metadata" crossOrigin="use-credentials" aria-hidden="true" />
          : <img src={api.mediaUrl(media.url)} alt="" loading="lazy" crossOrigin="use-credentials" />
        : <div className="explore-text-tile">
          <FileText size={22} aria-hidden="true" />
          <span>{caption || 'OpenVibe community post'}</span>
        </div>}
      {isVideo && <span className="explore-video-indicator" aria-hidden="true"><Play size={16} fill="currentColor" /></span>}
      <span className="explore-tile-overlay">
        <span className="explore-tile-author">{author}</span>
        {caption && <span className="explore-tile-caption">{caption}</span>}
        <span className="explore-tile-stats">
          <span><Heart size={15} fill="currentColor" aria-hidden="true" />{post.like_count || 0}</span>
        </span>
      </span>
    </button>
  );
};

export const PostFeed = ({ searchQuery = '', explore = false, contentType = null, onOpenProfile, onOpenArticle }) => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');
  const [loadMoreError, setLoadMoreError] = useState('');
  const [selectedPost, setSelectedPost] = useState(null);
  const loadMoreSentinel = useRef(null);
  const hasMoreRef = useRef(false);
  const loadingRef = useRef(true);
  const loadingMoreRef = useRef(false);
  const nextOffsetRef = useRef(0);
  const generationRef = useRef(0);

  const fetchPosts = useCallback(async () => {
    const generation = ++generationRef.current;
    loadingRef.current = true;
    loadingMoreRef.current = false;
    hasMoreRef.current = false;
    nextOffsetRef.current = 0;
    setLoading(true);
    setLoadingMore(false);
    setHasMore(false);
    setLoadMoreError('');
    setError('');
    try {
      const data = explore
        ? await api.listExplorePosts(0, EXPLORE_PAGE_SIZE)
        : await api.listPosts('APPROVED', contentType);
      if (generation !== generationRef.current) return;
      setPosts(data);
      nextOffsetRef.current = data.length;
      const more = explore && data.length === EXPLORE_PAGE_SIZE;
      hasMoreRef.current = more;
      setHasMore(more);
    } catch (err) {
      if (generation === generationRef.current) setError(getFeedError(err));
    } finally {
      if (generation === generationRef.current) {
        loadingRef.current = false;
        setLoading(false);
      }
    }
  }, [contentType, explore]);

  const fetchMore = useCallback(async () => {
    if (!explore || loadingRef.current || loadingMoreRef.current || !hasMoreRef.current) return;
    loadingMoreRef.current = true;
    const generation = generationRef.current;
    setLoadingMore(true);
    setLoadMoreError('');
    try {
      const data = await api.listExplorePosts(nextOffsetRef.current, EXPLORE_PAGE_SIZE);
      if (generation !== generationRef.current) return;
      nextOffsetRef.current += data.length;
      setPosts((current) => {
        const existingIds = new Set(current.map((post) => post.id));
        return [...current, ...data.filter((post) => !existingIds.has(post.id))];
      });
      const more = data.length === EXPLORE_PAGE_SIZE;
      hasMoreRef.current = more;
      setHasMore(more);
    } catch (err) {
      if (generation === generationRef.current) setLoadMoreError(getFeedError(err));
    } finally {
      if (generation === generationRef.current) {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      }
    }
  }, [explore]);

  useEffect(() => { fetchPosts(); }, [fetchPosts]);

  useEffect(() => {
    if (!explore || !hasMore || loading || error || !loadMoreSentinel.current || !('IntersectionObserver' in window)) {
      return undefined;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) fetchMore();
    }, { rootMargin: '480px 0px' });
    observer.observe(loadMoreSentinel.current);
    return () => observer.disconnect();
  }, [error, fetchMore, hasMore, explore, loading]);

  useEffect(() => {
    if (!selectedPost) return undefined;
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setSelectedPost(null);
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedPost]);

  const query = searchQuery.trim().toLocaleLowerCase();
  const filteredPosts = !query ? posts : posts.filter((post) => (
    `${post.content} ${post.author_username}`.toLocaleLowerCase().includes(query)
  ));

  return (
    <section className={`feed-stream ${explore ? 'feed-stream-explore' : ''}`} aria-label={explore ? 'Explore public posts' : contentType === 'EVENT' ? 'Community events' : contentType === 'ARTICLE' ? 'Community articles' : 'Approved community posts'} aria-live="polite">
      <div className="feed-section-heading">
        <div>
          <span className="eyebrow">{explore ? 'PUBLIC COMMUNITY' : contentType === 'EVENT' ? 'GATHER TOGETHER' : contentType === 'ARTICLE' ? 'IDEAS IN DEPTH' : 'COMMUNITY'}</span>
          <h2>{searchQuery ? 'Search results' : explore ? 'Discover something new' : contentType === 'EVENT' ? 'Upcoming events' : contentType === 'ARTICLE' ? 'Community articles' : 'Latest conversations'}</h2>
        </div>
        <button type="button" className="btn btn-quiet btn-sm" onClick={fetchPosts} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} aria-hidden="true" /> Refresh
        </button>
      </div>

      {searchQuery && <div className="search-results-summary"><Search size={15} aria-hidden="true" /> Approved posts matching <strong>“{searchQuery}”</strong></div>}
      {loading && <div className="feed-skeletons" role="status" aria-label="Loading posts"><span className="skeleton-post" /><span className="skeleton-post" /></div>}
      {error && <div className="empty-state card" role="alert"><span className="empty-icon"><Globe2 size={22} /></span><h3>Feed temporarily unavailable</h3><p>{error}</p><button type="button" className="btn btn-secondary btn-sm" onClick={fetchPosts}>Try again</button></div>}

      {!loading && !error && filteredPosts.length === 0 && (
        <div className="empty-state card" role="status">
          <span className="empty-icon">{searchQuery ? <Search size={22} aria-hidden="true" /> : <FileText size={22} aria-hidden="true" />}</span>
          <h3>{searchQuery ? 'No matching posts' : contentType === 'EVENT' ? 'No events yet' : contentType === 'ARTICLE' ? 'No articles yet' : explore ? 'Nothing to explore yet' : 'The feed is ready for your first post'}</h3>
          <p>{searchQuery ? 'Try a different name or phrase. Search currently covers approved post text and author usernames.' : explore ? 'Approved posts from public accounts will appear here as the community shares.' : contentType === 'EVENT' ? 'Published events from the OpenVibe community will appear here.' : contentType === 'ARTICLE' ? 'Long-form stories and ideas from community members will appear here.' : 'Approved community posts will appear here. Sign in to share an update; posts are checked by the moderation service before publication.'}</p>
        </div>
      )}

      {!loading && !error && explore && filteredPosts.length > 0 && <div className="explore-post-grid">
        {filteredPosts.map((post, index) => <ExploreTile key={post.id} post={post} index={index} onClick={() => setSelectedPost(post)} />)}
      </div>}

      {!loading && !error && !explore && filteredPosts.map((post) => <PostCard key={post.id} post={post} onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />)}

      {explore && !loading && !error && hasMore && <>
        <div className="explore-load-sentinel" ref={loadMoreSentinel} aria-hidden="true" />
        {loadMoreError && <div className="notice-card notice-card-error" role="alert">{loadMoreError}</div>}
        <div className="explore-load-more">
          <button type="button" className="btn btn-secondary btn-sm" onClick={fetchMore} disabled={loadingMore}>
            {loadingMore ? 'Loading more posts…' : loadMoreError ? 'Try loading more' : 'Load more'}
          </button>
        </div>
      </>}

      {explore && !loading && !error && !hasMore && filteredPosts.length > 0 && <p className="explore-end-note">You’re all caught up on public posts.</p>}

      {selectedPost && <div className="explore-post-backdrop" role="presentation" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setSelectedPost(null);
      }}>
        <section className="explore-post-dialog" role="dialog" aria-modal="true" aria-labelledby="explore-post-dialog-title">
          <header className="explore-post-dialog-header">
            <h2 id="explore-post-dialog-title">Post</h2>
            <button type="button" className="btn btn-quiet btn-icon" onClick={() => setSelectedPost(null)} aria-label="Close post details" autoFocus><X size={19} /></button>
          </header>
          <PostCard post={selectedPost} onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />
        </section>
      </div>}
    </section>
  );
};
