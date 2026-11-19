import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AlertCircle, Bell, BookOpen, CalendarDays, Globe2, Heart, LoaderCircle, MessageSquare, ShieldCheck, UserRoundPlus, UsersRound } from 'lucide-react';
import { AuthContext } from '../../context/AuthContext';
import { Avatar } from './Avatar';
import { PostCard } from '../posts/PostCard';
import { api } from '../../services/api';

const icons = {
  NETWORK_POST: Globe2,
  NETWORK_ARTICLE: BookOpen,
  NETWORK_EVENT: CalendarDays,
  EVENT_INVITATION: CalendarDays,
  EVENT_REMINDER: CalendarDays,
  POST_LIKE: Heart,
  COMMENT: MessageSquare,
  COMMENT_LIKE: Heart,
  CONNECTION_REQUEST: UserRoundPlus,
  CONNECTION_ACCEPTED: UsersRound,
  CONNECTION_REJECTED: UsersRound,
  FOLLOW_REQUEST: UserRoundPlus,
  FOLLOW_ACCEPTED: UsersRound,
  FOLLOW_REJECTED: UsersRound,
  FOLLOW: UsersRound,
  MESSAGE: MessageSquare,
  MODERATION_RESULT: ShieldCheck,
};

const labels = {
  NETWORK_POST: 'shared a new post',
  NETWORK_ARTICLE: 'published a new article',
  NETWORK_EVENT: 'created a new event',
  EVENT_INVITATION: 'invited you to an event',
  EVENT_REMINDER: 'reminded you about an event',
  POST_LIKE: 'liked your post',
  COMMENT: 'commented on your post',
  COMMENT_LIKE: 'liked your comment',
  CONNECTION_REQUEST: 'sent you a connection request',
  CONNECTION_ACCEPTED: 'accepted your connection request',
  CONNECTION_REJECTED: 'declined your connection request',
  FOLLOW_REQUEST: 'requested to follow you',
  FOLLOW_ACCEPTED: 'accepted your follow request',
  FOLLOW_REJECTED: 'declined your follow request',
  FOLLOW: 'started following you',
  MESSAGE: 'sent you a message',
  MODERATION_RESULT: 'your content has a moderation update',
  DISCOVERY_POST: 'recommended a public post for you',
};

const relativeTime = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const ranges = [['day', 86400], ['hour', 3600], ['minute', 60]];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  for (const [unit, size] of ranges) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return 'Just now';
};

export const SectionNotifications = ({
  section,
  title,
  setActivePage,
  onOpenArticle,
  excludeKinds = [],
}) => {
  const { user } = useContext(AuthContext);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPost, setSelectedPost] = useState(null);
  const excludeKey = excludeKinds.join('|');

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const result = await api.getNotifications(0, 10, section);
      const excluded = new Set(excludeKey ? excludeKey.split('|') : []);
      setNotifications(result.notifications.filter((item) => !excluded.has(item.kind)));
      setUnreadCount(result.section_unread_count || 0);
    } catch (err) {
      setError(err.message || 'Section updates could not be loaded.');
    } finally { setLoading(false); }
  }, [excludeKey, section, user]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const timer = window.setInterval(load, 30000);
    window.addEventListener('openvibe:notifications-updated', load);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('openvibe:notifications-updated', load);
    };
  }, [load]);

  const openNotification = async (notification) => {
    try {
      if (!notification.is_read) await api.markNotificationRead(notification.id);
      setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
      setUnreadCount((count) => Math.max(0, count - (notification.is_read ? 0 : 1)));
      window.dispatchEvent(new CustomEvent('openvibe:notifications-updated'));

      if (notification.kind === 'NETWORK_ARTICLE') {
        const article = await api.getPost(notification.resource_id);
        onOpenArticle?.(article);
        return;
      }
      if (['NETWORK_POST', 'NETWORK_EVENT', 'DISCOVERY_POST'].includes(notification.kind)) {
        setSelectedPost(await api.getPost(notification.resource_id));
        return;
      }
      if (notification.kind === 'MESSAGE') {
        setActivePage('messages');
        window.setTimeout(() => window.dispatchEvent(new CustomEvent('openvibe:open-conversation', {
          detail: { conversationId: notification.resource_id },
        })), 0);
        return;
      }
      setActivePage(notification.section || section);
    } catch (err) {
      setError(err.message || 'This update could not be opened.');
    }
  };

  if (!user || (!loading && !error && notifications.length === 0)) return null;

  return (
    <>
      <section className="card section-notification-panel" aria-label={`${title} notifications`}>
        <div className="section-heading-row">
          <div><h2>{title}</h2><p>{unreadCount ? `${unreadCount} unread` : 'Recent updates'}</p></div>
          {unreadCount > 0 && <span className="nav-unread-count" aria-label={`${unreadCount} unread ${section} notifications`}>{unreadCount > 99 ? '99+' : unreadCount}</span>}
        </div>
        {loading && <div className="loading-state" role="status"><LoaderCircle className="spin" size={16} /> Loading updates…</div>}
        {error && <div className="section-notification-error" role="alert"><AlertCircle size={15} />{error}</div>}
        {!loading && notifications.length > 0 && <ul className="section-notification-list">
          {notifications.slice(0, 5).map((notification) => {
            const Icon = icons[notification.kind] || Bell;
            return <li className={`section-notification-item ${notification.is_read ? '' : 'unread'}`} key={notification.id}>
              <Avatar name={notification.actor_full_name || notification.actor_username || 'OpenVibe'} src={notification.actor_avatar_url} size="sm" />
              <Icon size={16} className="section-notification-icon" aria-hidden="true" />
              <button type="button" className="section-notification-link" onClick={() => openNotification(notification)}>
                <span><strong>{notification.actor_full_name || notification.actor_username || 'OpenVibe'}</strong> {labels[notification.kind] || 'updated your account'}.</span>
                {notification.post_preview && <small>{notification.post_preview}</small>}
                <time dateTime={notification.created_at}>{relativeTime(notification.created_at)}</time>
              </button>
              {!notification.is_read && <span className="section-notification-unread-dot" aria-label="Unread" />}
            </li>;
          })}
        </ul>}
        <button type="button" className="section-notification-all-link" onClick={() => setActivePage('notifications')}>View all notifications</button>
      </section>
      {selectedPost && <div className="explore-post-backdrop" role="presentation" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setSelectedPost(null);
      }}>
        <section className="explore-post-dialog" role="dialog" aria-modal="true" aria-label="Notification details">
          <header className="explore-post-dialog-header"><h2>Update</h2><button type="button" className="btn btn-quiet btn-icon" onClick={() => setSelectedPost(null)} aria-label="Close update"><Bell size={18} /></button></header>
          <PostCard post={selectedPost} />
        </section>
      </div>}
    </>
  );
};
