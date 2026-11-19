import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { CreatePostForm } from '../components/posts/CreatePostForm';
import { PostFeed } from '../components/posts/PostFeed';
import { ModerationSandbox } from '../components/posts/ModerationSandbox';
import { Avatar } from '../components/common/Avatar';
import { BrandImage } from '../components/common/BrandImage';
import { PostCard } from '../components/posts/PostCard';
import { api } from '../services/api';
import {
  Activity, ArrowRight, Bookmark, BookOpen, CalendarDays, Compass, FileText, LockKeyhole,
  Search, ShieldCheck, Sparkles, UserRound,
} from 'lucide-react';

export const Home = ({ setActivePage, searchQuery = '', onSearch, onOpenProfile, onOpenOwnProfile, onOpenArticle }) => {
  const { user } = useContext(AuthContext);
  const [showSandbox, setShowSandbox] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileQuery, setMobileQuery] = useState(searchQuery);
  const [searchResults, setSearchResults] = useState({ users: [], posts: [] });
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState('');

  useEffect(() => setMobileQuery(searchQuery), [searchQuery]);

  useEffect(() => {
    const query = searchQuery.trim();
    if (!user || query.length < 2) { setSearchResults({ users: [], posts: [] }); setSearchLoading(false); return undefined; }
    let active = true;
    const timer = window.setTimeout(async () => {
      setSearchLoading(true);
      setSearchError('');
      try { const result = await api.search(query); if (active) setSearchResults(result); }
      catch (err) { if (active) setSearchError(err.message || 'Search could not be completed.'); }
      finally { if (active) setSearchLoading(false); }
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [searchQuery, user]);

  return (
    <main id="main-content" className="container page-shell">
      <div className="feed-layout">
        <aside className="left-sidebar" aria-label="Your profile and shortcuts">
          <section className="card mini-profile-card">
            <BrandImage className="mini-profile-cover" src="/images/cover.jpg" alt="OpenVibe profile cover artwork" loading="eager" />
            <div className="mini-profile-body">
              <Avatar name={user?.full_name || user?.username || 'OpenVibe member'} src={user?.avatar_url} size="xl" className="mini-profile-avatar" />
              {user ? <>
                <h2>{user.full_name || user.username}</h2>
                <p className="mini-profile-subtitle">{user.headline || `@${user.username}`}</p>
                <div className="role-label"><ShieldCheck size={14} aria-hidden="true" /> {user.role === 'ADMIN' ? 'Administrator' : 'Community member'}</div>
                <button type="button" className="text-link-button" onClick={onOpenOwnProfile}>View your profile <ArrowRight size={14} /></button>
              </> : <>
                <h2>Welcome to OpenVibe</h2>
                <p className="mini-profile-subtitle">Ideas grow when we share them responsibly.</p>
                <button type="button" className="btn btn-primary btn-sm full-width" onClick={() => setActivePage('register')}>Create your account</button>
              </>}
            </div>
            {user && <div className="mini-profile-links">
              <button type="button" className="dropdown-item" onClick={() => setActivePage('dashboard')}><Activity size={16} /> My activity & moderation</button>
              <button type="button" className="dropdown-item" onClick={() => setActivePage('account-settings')}><UserRound size={16} /> Account settings</button>
              <button type="button" className="dropdown-item" onClick={() => setActivePage('data-rights')}><LockKeyhole size={16} /> Privacy center</button>
            </div>}
          </section>

          <section className="card sidebar-prompt">
            <span className="sidebar-icon"><Compass size={17} aria-hidden="true" /></span>
            <h2>Find your community</h2>
            <p>Discover fresh perspectives, creators, and conversations across OpenVibe.</p>
            <button type="button" className="text-link-button" onClick={() => setActivePage('explore')}>Explore the community <ArrowRight size={14} /></button>
          </section>
        </aside>

        <section className="feed-column" aria-label="Community feed">
          <header className="feed-welcome">
            <div className="feed-welcome-copy">
              <span className="eyebrow">THE OPENVIBE COMMUNITY</span>
              <h1>{user ? `Good to see you, ${user.full_name || user.username}` : 'Make room for good ideas.'}</h1>
              <p>Connect. Share. Engage. Responsibly.</p>
              {!user && <button type="button" className="btn btn-primary btn-sm" onClick={() => setActivePage('login')}>Sign in to join the conversation</button>}
            </div>
            <BrandImage src="/images/post-team.jpg" alt="A small team collaborating around laptops" loading="lazy" />
          </header>

          <nav className="content-discovery-links" aria-label="Community content">
            <span>Discover</span>
            <button type="button" onClick={() => setActivePage('events')}><CalendarDays size={16} /> Events <ArrowRight size={14} /></button>
            <button type="button" onClick={() => setActivePage('articles')}><BookOpen size={16} /> Articles <ArrowRight size={14} /></button>
          </nav>

          <form className="mobile-feed-search" role="search" onSubmit={(event) => { event.preventDefault(); onSearch?.(mobileQuery.trim()); }}>
            <Search size={17} aria-hidden="true" />
            <label htmlFor="mobile-post-search" className="sr-only">Search people and posts</label>
            <input id="mobile-post-search" type="search" value={mobileQuery} onChange={(event) => setMobileQuery(event.target.value)} placeholder="Search people and posts" />
            <button type="submit" className="btn btn-secondary btn-sm">Search</button>
          </form>

          {user ? <CreatePostForm onPostCreated={() => setRefreshKey((key) => key + 1)} /> : (
            <section className="card guest-composer">
              <Avatar name="OpenVibe member" size="md" />
              <button type="button" onClick={() => setActivePage('login')}>Sign in to start a post…</button>
            </section>
          )}

          {user && searchQuery.trim().length >= 2 ? <section className="search-results" aria-label="Search results">
            <div className="section-heading-row"><div><span className="eyebrow">SEARCH</span><h2>Results for “{searchQuery.trim()}”</h2></div><button className="text-link-button" type="button" onClick={() => onSearch?.('')}>Clear search</button></div>
            {searchLoading && <div className="card loading-state" role="status">Searching members and posts…</div>}
            {searchError && <div className="notice-card notice-card-error" role="alert">{searchError}</div>}
            {!searchLoading && !searchError && searchResults.users.length > 0 && <section className="search-people-results" aria-label="People"><h3>People</h3><div className="people-grid">{searchResults.users.map((person) => <article className="person-card search-person-card" key={person.id}><Avatar name={person.full_name || person.username} src={person.avatar_url} size="lg" /><div><button className="person-name-button" type="button" onClick={() => onOpenProfile?.(person.id)}>{person.full_name || person.username}</button><p>{person.headline || `@${person.username}`}</p><span className="muted-note">@{person.username}</span></div><button type="button" className="text-link-button" onClick={() => onOpenProfile?.(person.id)}>View profile <ArrowRight size={14} /></button></article>)}</div></section>}
            {!searchLoading && !searchError && searchResults.posts.length > 0 && <section aria-label="Posts"><h3>Posts</h3>{searchResults.posts.map((post) => <PostCard key={post.id} post={post} onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />)}</section>}
            {!searchLoading && !searchError && searchResults.users.length === 0 && searchResults.posts.length === 0 && <div className="card empty-state"><h3>No matching members or posts</h3><p>Try another name or phrase. Results include active public profiles and approved posts.</p></div>}
          </section> : user && searchQuery.trim().length === 1 ? <div className="card empty-state"><h3>Enter at least two characters to search</h3><p>Search active member profiles and approved posts.</p></div> : <PostFeed key={refreshKey} searchQuery={searchQuery} onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />}
        </section>

        <aside className="right-sidebar" aria-label="OpenVibe information">
          <section className="card moderation-feature">
            <BrandImage src="/images/post-ai.jpg" alt="A digital illustration about artificial intelligence" loading="lazy" />
            <div className="moderation-feature-body">
              <span className="eyebrow">OPENVIBE TOOLS</span>
              <h2>Explore the text sandbox</h2>
              <p>Try a sample and preview the tools available to community members.</p>
              <button type="button" className="text-link-button" onClick={() => setShowSandbox((shown) => !shown)} aria-expanded={showSandbox}>
                <Sparkles size={15} /> {showSandbox ? 'Close the sandbox' : 'Try the sandbox'} <ArrowRight size={14} />
              </button>
            </div>
          </section>

          {showSandbox && <ModerationSandbox />}

          <section className="card quick-links-card">
            <h2>Good to know</h2>
            <button type="button" className="quick-link" onClick={() => setActivePage('ai-transparency')}><Sparkles size={17} /><span>AI transparency</span><ArrowRight size={15} /></button>
            <button type="button" className="quick-link" onClick={() => setActivePage('terms')}><FileText size={17} /><span>Community terms</span><ArrowRight size={15} /></button>
            <button type="button" className="quick-link" onClick={() => setActivePage('privacy-policy')}><LockKeyhole size={17} /><span>Privacy policy</span><ArrowRight size={15} /></button>
            <button type="button" className="quick-link" onClick={() => setActivePage('events')}><CalendarDays size={17} /><span>Community events</span><ArrowRight size={15} /></button>
            <button type="button" className="quick-link" onClick={() => setActivePage('articles')}><BookOpen size={17} /><span>Member articles</span><ArrowRight size={15} /></button>
            <div className="privacy-mini-note"><Bookmark size={15} aria-hidden="true" /> This version does not run analytics or ad tracking.</div>
          </section>

          <div className="sidebar-footer-links">
            <button type="button" onClick={() => setActivePage('privacy-policy')}>Privacy</button>
            <button type="button" onClick={() => setActivePage('terms')}>Terms</button>
            <button type="button" onClick={() => setActivePage('cookies-policy')}>Cookies</button>
            <span>© 2026 OpenVibe</span>
          </div>
        </aside>
      </div>
    </main>
  );
};
