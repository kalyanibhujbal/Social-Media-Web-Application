import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import { PostCard } from './PostCard';
import { Globe2, RefreshCw, Search, FileText } from 'lucide-react';

export const PostFeed = ({ searchQuery = '', explore = false, contentType = null, onOpenProfile, onOpenArticle }) => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = explore ? await api.listExplorePosts() : await api.listPosts('APPROVED', contentType);
      setPosts(data);
    } catch (err) {
      const message = err.message || '';
      setError(message === 'Failed to fetch' || message.includes('NetworkError')
        ? 'The community API is unreachable. Check that the backend is running and try again.'
        : message || 'We could not load the community feed. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [contentType, explore]);

  useEffect(() => { fetchPosts(); }, [fetchPosts]);

  const filteredPosts = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    if (!query) return posts;
    return posts.filter((post) => `${post.content} ${post.author_username}`.toLocaleLowerCase().includes(query));
  }, [posts, searchQuery]);

  return (
    <section className="feed-stream" aria-label={explore ? 'Explore public posts' : contentType === 'EVENT' ? 'Community events' : contentType === 'ARTICLE' ? 'Community articles' : 'Approved community posts'} aria-live="polite">
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
          <h3>{searchQuery ? 'No matching posts' : contentType === 'EVENT' ? 'No events yet' : contentType === 'ARTICLE' ? 'No articles yet' : 'The feed is ready for your first post'}</h3>
          <p>{searchQuery ? 'Try a different name or phrase. Search currently covers approved post text and author usernames.' : explore ? 'Public posts from across OpenVibe, with creators you can get to know.' : contentType === 'EVENT' ? 'Published events from the OpenVibe community will appear here.' : contentType === 'ARTICLE' ? 'Long-form stories and ideas from community members will appear here.' : 'Approved community posts will appear here. Sign in to share an update; posts are checked by the moderation service before publication.'}</p>
        </div>
      )}

      {!loading && !error && filteredPosts.map((post) => <PostCard key={post.id} post={post} onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />)}
    </section>
  );
};
