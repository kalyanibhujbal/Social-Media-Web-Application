import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { Avatar } from '../components/common/Avatar';
import { PostCard } from '../components/posts/PostCard';
import { AlertCircle, Bell, BookOpen, CalendarDays, Check, CheckCheck, Heart, LoaderCircle, MessageSquare, ShieldCheck, UserRoundPlus, UsersRound, X, Globe2 } from 'lucide-react';

const PAGE_SIZE = 30;
const details = {
  POST_LIKE: ['liked your post', Heart],
  COMMENT: ['commented on your post', MessageSquare],
  COMMENT_LIKE: ['liked your comment', Heart],
  CONNECTION_REQUEST: ['sent you a connection request', UserRoundPlus],
  CONNECTION_ACCEPTED: ['accepted your connection request', UsersRound],
  CONNECTION_REJECTED: ['declined your connection request', UsersRound],
  FOLLOW_REQUEST: ['requested to follow you', UserRoundPlus],
  FOLLOW_ACCEPTED: ['accepted your follow request', UsersRound],
  FOLLOW_REJECTED: ['declined your follow request', UsersRound],
  FOLLOW: ['started following you', UsersRound],
  NETWORK_POST: ['shared a new post', Globe2],
  NETWORK_ARTICLE: ['published a new article', BookOpen],
  NETWORK_EVENT: ['created a new event', CalendarDays],
  EVENT_INVITATION: ['invited you to an event', CalendarDays],
  EVENT_REMINDER: ['reminded you about an event', CalendarDays],
  DISCOVERY_POST: ['has a new public post for you', Globe2],
  MESSAGE: ['sent you a message', MessageSquare],
  MODERATION_RESULT: ['your post was sent for moderation review', ShieldCheck],
};

const relativeTime = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Date unavailable';
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const ranges = [
    ['year', 31536000], ['month', 2592000], ['week', 604800],
    ['day', 86400], ['hour', 3600], ['minute', 60],
  ];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  for (const [unit, size] of ranges) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(seconds, 'second');
};

export const Notifications = ({ setActivePage, onOpenArticle }) => {
  const { user } = useContext(AuthContext);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState(0);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState('');
  const [selectedPost, setSelectedPost] = useState(null);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const result = await api.getNotifications(0, PAGE_SIZE);
      setNotifications(result.notifications);
      setUnreadCount(result.unread_count);
      setHasMore(result.has_more);
      setNextOffset(result.next_offset);
    } catch (err) {
      setError(err.message || 'Your notifications could not be loaded. Please try again.');
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const retryLoad = () => {
    setLoading(true);
    setError('');
    load();
  };

  const updateUnreadCount = (nextCount) => {
    setUnreadCount(nextCount);
    window.dispatchEvent(new CustomEvent('openvibe:notifications-updated'));
  };

  const markRead = async (notification) => {
    if (notification.is_read) return;
    await api.markNotificationRead(notification.id);
    if (notification.kind === 'MESSAGE') {
      await load();
      window.dispatchEvent(new CustomEvent('openvibe:notifications-updated'));
      return;
    }
    setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
    updateUnreadCount(Math.max(0, unreadCount - 1));
  };

  const markAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
      updateUnreadCount(0);
    } catch (err) { setError(err.message || 'Notifications could not be updated.'); }
  };

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    setError('');
    try {
      const result = await api.getNotifications(nextOffset, PAGE_SIZE);
      setNotifications((items) => {
        const ids = new Set(items.map((item) => item.id));
        return [...items, ...result.notifications.filter((item) => !ids.has(item.id))];
      });
      setHasMore(result.has_more);
      setNextOffset(result.next_offset);
    } catch (err) {
      setError(err.message || 'More notifications could not be loaded.');
    } finally { setLoadingMore(false); }
  };

  const openNotification = async (notification) => {
    try {
      await markRead(notification);
      if (['NETWORK_POST', 'NETWORK_EVENT', 'DISCOVERY_POST'].includes(notification.kind)) {
        setSelectedPost(await api.getPost(notification.resource_id));
      } else if (notification.kind === 'NETWORK_ARTICLE') {
        onOpenArticle?.(await api.getPost(notification.resource_id));
      } else if (notification.kind === 'MESSAGE') {
        setActivePage('messages');
        window.setTimeout(() => window.dispatchEvent(new CustomEvent('openvibe:open-conversation', {
          detail: { conversationId: notification.resource_id },
        })), 0);
      } else if (['CONNECTION_REQUEST', 'FOLLOW_REQUEST', 'CONNECTION_ACCEPTED', 'CONNECTION_REJECTED', 'FOLLOW_ACCEPTED', 'FOLLOW_REJECTED', 'FOLLOW'].includes(notification.kind)) {
        setActivePage('network');
      } else if (notification.section && notification.section !== 'notifications') {
        setActivePage(notification.section);
      }
    } catch (err) {
      setError(err.message || 'This notification could not be opened.');
    }
  };

  const respondToRequest = async (notification, accept) => {
    setBusyId(notification.id);
    setError('');
    try {
      const isConnection = notification.kind === 'CONNECTION_REQUEST';
      if (isConnection) {
        if (accept) await api.acceptConnection(notification.resource_id);
        else await api.rejectConnection(notification.resource_id);
      } else if (accept) {
        await api.acceptFollowRequest(notification.actor_id);
      } else {
        await api.rejectFollowRequest(notification.actor_id);
      }
      setNotifications((items) => items.map((item) => item.id === notification.id
        ? { ...item, resource_status: accept ? 'ACCEPTED' : 'REJECTED', is_read: true }
        : item));
      if (!notification.is_read) updateUnreadCount(Math.max(0, unreadCount - 1));
    } catch (err) {
      setError(err.message || 'The request could not be updated.');
    } finally { setBusyId(''); }
  };

  const loadMorePost = (updatedPost) => setSelectedPost(updatedPost);

  if (!user) return <main id="main-content" className="container page-shell narrow-page"><section className="card auth-required-state"><Bell size={25} /><h1>Sign in to view notifications</h1><p>Your account activity is private to your signed-in session.</p><button className="btn btn-primary" type="button" onClick={() => setActivePage('login')}>Sign in</button></section></main>;

  return (
    <main id="main-content" className="container page-shell narrow-page">
      <header className="page-heading"><div><span className="eyebrow">YOUR UPDATES</span><h1>Notifications</h1><p>Connection, message, and post activity from OpenVibe.</p></div><div className="page-heading-mark"><Bell size={22} aria-hidden="true" /></div></header>
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{error}<button className="text-link-button" type="button" onClick={retryLoad}>Retry</button></div>}
      <section className="card notification-panel" aria-label="Notifications">
        <div className="section-heading-row"><div><h2>Recent activity</h2><p>{unreadCount ? `${unreadCount} unread` : 'All caught up'}</p></div>{unreadCount > 0 && <button className="btn btn-quiet btn-sm" type="button" onClick={markAllRead}><CheckCheck size={16} /> Mark all read</button>}</div>
        {loading ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={18} /> Loading notifications…</div> : notifications.length === 0 ? <div className="empty-state"><span className="empty-icon"><Bell size={22} /></span><h3>You’re all caught up</h3><p>Connection requests, messages, and post activity will appear here.</p></div> : <ul className="notification-list">{notifications.map((notification) => {
          const [defaultLabel, Icon] = details[notification.kind] || ['updated your OpenVibe activity', Bell];
          const label = notification.kind === 'MODERATION_RESULT' && notification.resource_type === 'comment' ? 'your comment was sent for moderation review' : defaultLabel;
          const isRequest = ['CONNECTION_REQUEST', 'FOLLOW_REQUEST'].includes(notification.kind);
          const status = (notification.resource_status || 'PENDING').toUpperCase();
          const requestPending = isRequest && status === 'PENDING';
          return <li className={`notification-row ${notification.is_read ? '' : 'unread'}`} key={notification.id}>
            <Avatar name={notification.actor_full_name || notification.actor_username || (notification.kind === 'MODERATION_RESULT' ? 'OpenVibe' : 'OpenVibe member')} src={notification.actor_avatar_url} size="md" />
            <span className="notification-kind-icon"><Icon size={16} aria-hidden="true" /></span>
            <div className="notification-copy">
              <button type="button" className="notification-open-button" onClick={() => openNotification(notification)}>
                <p><strong>{notification.actor_full_name || notification.actor_username || (notification.kind === 'MODERATION_RESULT' ? 'OpenVibe' : 'A member')}</strong> {label}.</p>
                {['NETWORK_POST', 'NETWORK_ARTICLE', 'NETWORK_EVENT', 'DISCOVERY_POST'].includes(notification.kind) && notification.post_preview && <span className="notification-post-preview">{notification.post_preview}</span>}
                <time dateTime={notification.created_at} title={new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(notification.created_at))}>{relativeTime(notification.created_at)}</time>
              </button>
              {requestPending && <div className="notification-request-actions">
                <button type="button" className="btn btn-primary btn-sm" disabled={busyId === notification.id} onClick={() => respondToRequest(notification, true)}><Check size={14} /> Accept</button>
                <button type="button" className="btn btn-quiet btn-sm" disabled={busyId === notification.id} onClick={() => respondToRequest(notification, false)}><X size={14} /> Reject</button>
              </div>}
              {isRequest && !requestPending && <span className={`notification-status notification-status-${status.toLowerCase()}`}>{status}</span>}
            </div>
            {!notification.is_read && <button type="button" className="notification-mark-read" aria-label="Mark notification as read" onClick={() => markRead(notification).catch((err) => setError(err.message || 'This notification could not be updated.'))} />}
          </li>;
        })}</ul>}
        {hasMore && <div className="notification-load-more"><button type="button" className="btn btn-secondary btn-sm" disabled={loadingMore} onClick={loadMore}>{loadingMore ? 'Loading…' : 'Load older notifications'}</button></div>}
      </section>
      {selectedPost && <div className="explore-post-backdrop" role="presentation" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setSelectedPost(null);
      }}>
        <section className="explore-post-dialog" role="dialog" aria-modal="true" aria-label="Post details">
          <header className="explore-post-dialog-header"><h2>Post</h2><button type="button" className="btn btn-quiet btn-icon" onClick={() => setSelectedPost(null)} aria-label="Close post details"><X size={19} /></button></header>
          <PostCard post={selectedPost} onPostUpdated={loadMorePost} />
        </section>
      </div>}
    </main>
  );
};
