import React, { useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { NotificationCountContext } from '../../context/NotificationCountContext';
import { Home, Compass, Users, Plus, Bell, UserRound } from 'lucide-react';

export const MobileNavigation = ({ activePage, setActivePage }) => {
  const { user } = useContext(AuthContext);
  const { total: unreadCount, sections: unreadBySection } = useContext(NotificationCountContext);

  const createPost = () => {
    if (!user) { setActivePage('login'); return; }
    setActivePage('home');
    window.setTimeout(() => {
      const composer = document.getElementById('post-content');
      composer?.focus();
      composer?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  };

  const links = [
    { key: 'home', label: 'Home', Icon: Home, onClick: () => setActivePage('home') },
    { key: 'explore', label: 'Explore', Icon: Compass, onClick: () => setActivePage('explore') },
    { key: 'network', label: 'Network', Icon: Users, onClick: () => setActivePage('network') },
    { key: 'create', label: user ? 'Create' : 'Sign in', Icon: Plus, onClick: createPost },
    { key: 'notifications', label: 'Alerts', Icon: Bell, onClick: () => setActivePage('notifications') },
    { key: 'profile', label: 'Profile', Icon: UserRound, onClick: () => setActivePage(user ? 'profile' : 'login') },
  ];

  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
      {links.map(({ key, label, Icon, onClick }) => {
        const count = key === 'notifications' ? unreadCount : (unreadBySection[key] || 0);
        return <button
          key={key}
          type="button"
          className={`mobile-nav-item ${activePage === key || (key === 'profile' && activePage === 'login') ? 'active' : ''} ${key === 'create' ? 'mobile-create-button' : ''}`}
          onClick={onClick}
          aria-current={activePage === key ? 'page' : undefined}
          aria-label={key === 'create' ? 'Create a post' : count > 0 ? `${label}, ${count} unread` : label}
        ><Icon size={20} strokeWidth={1.9} aria-hidden="true" /><span>{label}{count > 0 && <span className="nav-unread-count">{count > 99 ? '99+' : count}</span>}</span></button>;
      })}
    </nav>
  );
};
