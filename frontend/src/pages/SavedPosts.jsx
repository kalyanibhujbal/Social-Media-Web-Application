import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { PostCard } from '../components/posts/PostCard';
import { AlertCircle, Bookmark, LoaderCircle } from 'lucide-react';

export const SavedPosts = ({ setActivePage, onOpenProfile, onOpenArticle }) => {
  const { user } = useContext(AuthContext);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    if (!user) { setLoading(false); return; }
    setLoading(true);
    setError('');
    try { setPosts(await api.getSavedPosts()); }
    catch (err) { setError(err.message || 'Saved posts could not be loaded.'); }
    finally { setLoading(false); }
  }, [user]);
  useEffect(() => { load(); }, [load]);

  if (!user) return <main id="main-content" className="container page-shell narrow-page"><section className="card auth-required-state"><Bookmark size={24} /><h1>Sign in to view saved posts</h1><p>Your saved posts are private to your account.</p><button className="btn btn-primary" type="button" onClick={() => setActivePage('login')}>Sign in</button></section></main>;
  return <main id="main-content" className="container page-shell narrow-page"><header className="page-heading"><div><span className="eyebrow">YOUR LIBRARY</span><h1>Saved posts</h1><p>Posts you saved from the OpenVibe feed.</p></div><div className="page-heading-mark"><Bookmark size={22} /></div></header>{error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{error}<button className="text-link-button" type="button" onClick={load}>Retry</button></div>}{loading ? <div className="card loading-state" role="status"><LoaderCircle className="spin" size={18} /> Loading saved posts…</div> : posts.length ? posts.map((post) => <PostCard key={post.id} post={post} onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} onSavedStateChange={(id, saved) => { if (!saved) setPosts((items) => items.filter((item) => item.id !== id)); }} />) : <div className="card empty-state"><span className="empty-icon"><Bookmark size={22} /></span><h2>No saved posts yet</h2><p>Use Save on a post to keep it here.</p><button type="button" className="btn btn-secondary btn-sm" onClick={() => setActivePage('home')}>Browse the feed</button></div>}</main>;
};
