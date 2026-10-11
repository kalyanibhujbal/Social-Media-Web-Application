import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { OpenVibeLogo } from './OpenVibeLogo';
import { api } from '../../services/api';
import {
  Home, Users, Bell, MessageSquare, BarChart3, ShieldCheck,
  UserRound, Settings, LogOut, Search, ChevronDown, X, Bookmark,
} from 'lucide-react';

const PRIMARY_LINKS = [
  { key: 'home', label: 'Home', Icon: Home },
  { key: 'network', label: 'Network', Icon: Users },
  { key: 'notifications', label: 'Alerts', Icon: Bell },
  { key: 'messages', label: 'Messages', Icon: MessageSquare },
];

export const Navbar = ({ activePage, setActivePage, searchQuery = '', onSearch, onOpenProfile, onOpenOwnProfile }) => {
  const { user, logout } = useContext(AuthContext);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [query, setQuery] = useState(searchQuery);
  const [searchFocused, setSearchFocused] = useState(false);
  const [recentSearches, setRecentSearches] = useState([]);
  const [peopleResults, setPeopleResults] = useState([]);
  const [searchingPeople, setSearchingPeople] = useState(false);
  const [peopleSearchError, setPeopleSearchError] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => setQuery(searchQuery), [searchQuery]);

  useEffect(() => {
    const term = query.trim();
    if (!user || term.length < 2 || !searchFocused) { setPeopleResults([]); setSearchingPeople(false); return undefined; }
    let active = true;
    const timer = window.setTimeout(async () => {
      setSearchingPeople(true);
      setPeopleSearchError('');
      try {
        const rows = await api.searchUsers(term);
        if (active) setPeopleResults(rows);
      } catch (error) {
        if (active) setPeopleSearchError(error.message || 'People search is unavailable.');
      } finally { if (active) setSearchingPeople(false); }
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query, user, searchFocused]);

  useEffect(() => {
    if (!user) { setUnreadCount(0); return undefined; }
    let active = true;
    const refresh = () => api.getNotifications().then((result) => { if (active) setUnreadCount(result.unread_count); }).catch(() => {});
    refresh();
    const timer = window.setInterval(refresh, 60000);
    const handleUpdate = (event) => { if (Number.isInteger(event.detail?.unreadCount)) setUnreadCount(event.detail.unreadCount); else refresh(); };
    window.addEventListener('openvibe:notifications-updated', handleUpdate);
    return () => { active = false; window.clearInterval(timer); window.removeEventListener('openvibe:notifications-updated', handleUpdate); };
  }, [user]);

  const go = (page) => {
    setActivePage(page);
    setDropdownOpen(false);
  };

  const submitSearch = (event) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed) setRecentSearches((items) => [trimmed, ...items.filter((item) => item.toLowerCase() !== trimmed.toLowerCase())].slice(0, 5));
    onSearch?.(trimmed);
    setSearchFocused(false);
  };

  return (
    <header className="navbar">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <div className="container nav-content">
        <div className="nav-brand">
          <button type="button" className="nav-logo" onClick={() => go('home')} aria-label="OpenVibe home">
            <OpenVibeLogo size={34} />
          </button>
          <form className="nav-search" role="search" onSubmit={submitSearch}>
            <Search className="nav-search-icon" size={17} aria-hidden="true" />
            <input
              type="search"
              className="nav-search-input"
              placeholder="Search people and posts"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
              aria-label="Search people and posts"
              aria-expanded={searchFocused}
              aria-controls="search-suggestions"
            />
            {query && <button type="button" className="search-clear" onClick={() => { setQuery(''); onSearch?.(''); }} aria-label="Clear search"><X size={15} /></button>}
            {searchFocused && <div className="search-suggestions" id="search-suggestions" role="listbox" aria-label="Search suggestions">
              {query.trim() ? <>
                <button type="submit" role="option" onMouseDown={(event) => event.preventDefault()}><Search size={15} /><span>Search approved posts for <strong>“{query.trim()}”</strong></span></button>
                {user && <span className="search-suggestions-label">People</span>}
                {searchingPeople && <span className="search-suggestions-empty">Searching active member profiles…</span>}
                {peopleSearchError && <span className="search-suggestions-empty" role="status">{peopleSearchError}</span>}
                {peopleResults.map((person) => <button type="button" role="option" key={person.id} onMouseDown={(event) => event.preventDefault()} onClick={() => { onOpenProfile?.(person.id); setSearchFocused(false); }}><span className="search-person-avatar">{(person.full_name || person.username).slice(0, 1).toUpperCase()}</span><span><strong>{person.full_name || person.username}</strong><small>@{person.username}{person.headline ? ` · ${person.headline}` : ''}</small></span></button>)}
                {user && !searchingPeople && !peopleSearchError && peopleResults.length === 0 && <span className="search-suggestions-empty">No member profiles matched.</span>}
              </> : recentSearches.length ? <>
                <span className="search-suggestions-label">Recent searches · this session</span>
                {recentSearches.map((term) => <button type="button" role="option" key={term} onMouseDown={(event) => event.preventDefault()} onClick={() => { setQuery(term); onSearch?.(term); setSearchFocused(false); }}><Search size={14} /><span>{term}</span></button>)}
              </> : <span className="search-suggestions-empty">Search approved posts by text or author username.</span>}
              {!user && <span className="search-suggestions-note">Sign in to search member profiles.</span>}
            </div>}
          </form>
        </div>

        <div className="mobile-top-actions" aria-label="Quick navigation">
          <button type="button" onClick={() => go('notifications')} aria-label="Notifications"><Bell size={20} /></button>
          <button type="button" onClick={() => go(user ? 'profile' : 'login')} aria-label={user ? 'Profile' : 'Sign in'}><UserRound size={20} /></button>
        </div>

        <nav className="desktop-navigation" aria-label="Main navigation">
          <ul className="nav-links">
            {PRIMARY_LINKS.map(({ key, label, Icon }) => (
              <li key={key} className="nav-item">
                <button
                  type="button"
                  className={`nav-tab ${activePage === key ? 'active' : ''}`}
                  onClick={() => go(key)}
                  aria-current={activePage === key ? 'page' : undefined}
                  aria-label={key === 'notifications' && unreadCount > 0 ? `${label}, ${unreadCount} unread` : label}
                  title={key === 'messages' ? 'Messaging preview' : undefined}
                >
                  <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
                  <span>{label}{key === 'notifications' && unreadCount > 0 && <span className="nav-unread-count">{unreadCount > 99 ? '99+' : unreadCount}</span>}</span>
                </button>
              </li>
            ))}
            {user && <li className="nav-item">
              <button type="button" className={`nav-tab ${activePage === 'dashboard' ? 'active' : ''}`} onClick={() => go('dashboard')} aria-current={activePage === 'dashboard' ? 'page' : undefined}>
                <BarChart3 size={19} strokeWidth={1.9} aria-hidden="true" /><span>Insights</span>
              </button>
            </li>}
            {user ? (
              <li className="nav-item user-menu-wrapper">
                <button type="button" className={`nav-tab profile-menu-trigger ${activePage === 'profile' ? 'active' : ''}`} onClick={() => setDropdownOpen((open) => !open)} aria-expanded={dropdownOpen} aria-label="Profile and settings menu">
                  <span className="avatar avatar-sm avatar-initial">{(user.full_name || user.username)?.[0]?.toUpperCase() || 'U'}</span>
                  <span>Me</span><ChevronDown size={14} aria-hidden="true" />
                </button>
                {dropdownOpen && <div className="dropdown-menu">
                  <div className="dropdown-profile">
                    <span className="avatar avatar-lg avatar-initial">{(user.full_name || user.username)?.[0]?.toUpperCase() || 'U'}</span>
                    <strong>{user.full_name || user.username}</strong>
                    <span>{user.headline || (user.role === 'ADMIN' ? 'Administrator' : 'OpenVibe member')}</span>
                  </div>
                  <button className="dropdown-item" type="button" onClick={() => { onOpenOwnProfile?.(); setDropdownOpen(false); }}><UserRound size={17} /> View profile</button>
                  <button className="dropdown-item" type="button" onClick={() => go('saved')}><Bookmark size={17} /> Saved posts</button>
                  <button className="dropdown-item" type="button" onClick={() => go('account-settings')}><Settings size={17} /> Account settings</button>
                  <button className="dropdown-item" type="button" onClick={() => go('privacy-policy')}><ShieldCheck size={17} /> Privacy center</button>
                  {user.role === 'ADMIN' && <button className="dropdown-item" type="button" onClick={() => go('admin')}><ShieldCheck size={17} /> Moderation admin</button>}
                  <div className="dropdown-divider" />
                  <button className="dropdown-item dropdown-signout" type="button" onClick={() => { logout(); setDropdownOpen(false); }}><LogOut size={17} /> Sign out</button>
                </div>}
              </li>
            ) : (
              <li className="nav-item nav-auth-actions">
                <button type="button" className="btn btn-quiet btn-sm" onClick={() => go('login')}>Sign in</button>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => go('register')}>Join OpenVibe</button>
              </li>
            )}
          </ul>
        </nav>
      </div>
    </header>
  );
};
