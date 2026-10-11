import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { Avatar } from '../components/common/Avatar';
import { AlertCircle, Bell, CheckCheck, Heart, LoaderCircle, MessageSquare, ShieldCheck, UserRoundPlus, UsersRound } from 'lucide-react';

const details = {
  POST_LIKE: ['liked your post', Heart],
  COMMENT: ['commented on your post', MessageSquare],
  COMMENT_LIKE: ['liked your comment', Heart],
  CONNECTION_REQUEST: ['sent you a connection request', UserRoundPlus],
  CONNECTION_ACCEPTED: ['accepted your connection request', UsersRound],
  FOLLOW: ['started following you', UsersRound],
  MESSAGE: ['sent you a message', MessageSquare],
  MODERATION_RESULT: ['your post was sent for moderation review', ShieldCheck],
};

export const Notifications = ({ setActivePage }) => {
  const { user } = useContext(AuthContext);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!user) { setLoading(false); return; }
    setLoading(true);
    setError('');
    try {
      const result = await api.getNotifications();
      setNotifications(result.notifications);
      setUnreadCount(result.unread_count);
    } catch (err) {
      setError(err.message || 'Your notifications could not be loaded. Please try again.');
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const markRead = async (notification) => {
    if (notification.is_read) return;
    try {
      await api.markNotificationRead(notification.id);
      setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
      const nextCount = Math.max(0, unreadCount - 1);
      setUnreadCount(nextCount);
      window.dispatchEvent(new CustomEvent('openvibe:notifications-updated', { detail: { unreadCount: nextCount } }));
    } catch (err) { setError(err.message || 'This notification could not be updated.'); }
  };

  const markAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
      window.dispatchEvent(new CustomEvent('openvibe:notifications-updated', { detail: { unreadCount: 0 } }));
    } catch (err) { setError(err.message || 'Notifications could not be updated.'); }
  };

  if (!user) return <main id="main-content" className="container page-shell narrow-page"><section className="card auth-required-state"><Bell size={25} /><h1>Sign in to view notifications</h1><p>Your account activity is private to your signed-in session.</p><button className="btn btn-primary" type="button" onClick={() => setActivePage('login')}>Sign in</button></section></main>;

  return (
    <main id="main-content" className="container page-shell narrow-page">
      <header className="page-heading"><div><span className="eyebrow">YOUR UPDATES</span><h1>Notifications</h1><p>Connection, message, and moderation activity from OpenVibe.</p></div><div className="page-heading-mark"><Bell size={22} aria-hidden="true" /></div></header>
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{error}<button className="text-link-button" type="button" onClick={load}>Retry</button></div>}
      <section className="card notification-panel" aria-label="Notifications">
        <div className="section-heading-row"><div><h2>Recent activity</h2><p>{unreadCount ? `${unreadCount} unread` : 'All caught up'}</p></div>{unreadCount > 0 && <button className="btn btn-quiet btn-sm" type="button" onClick={markAllRead}><CheckCheck size={16} /> Mark all read</button>}</div>
        {loading ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={18} /> Loading notifications…</div> : notifications.length === 0 ? <div className="empty-state"><span className="empty-icon"><Bell size={22} /></span><h3>You’re all caught up</h3><p>Connection requests, messages, and post activity will appear here.</p></div> : <ul className="notification-list">{notifications.map((notification) => {
          const [defaultLabel, Icon] = details[notification.kind] || ['updated your OpenVibe activity', Bell];
          const label = notification.kind === 'MODERATION_RESULT' && notification.resource_type === 'comment' ? 'your comment was sent for moderation review' : defaultLabel;
          return <li className={`notification-row ${notification.is_read ? '' : 'unread'}`} key={notification.id}>
            <Avatar name={notification.actor_username || (notification.kind === 'MODERATION_RESULT' ? 'OpenVibe' : 'OpenVibe member')} size="md" />
            <span className="notification-kind-icon"><Icon size={16} aria-hidden="true" /></span>
            <div className="notification-copy"><p><strong>{notification.actor_username || (notification.kind === 'MODERATION_RESULT' ? 'OpenVibe' : 'A member')}</strong> {label}.</p><time dateTime={notification.created_at}>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(notification.created_at))}</time></div>
            {!notification.is_read && <button type="button" className="notification-mark-read" aria-label="Mark notification as read" onClick={() => markRead(notification)} />}
          </li>;
        })}</ul>}
      </section>
    </main>
  );
};
