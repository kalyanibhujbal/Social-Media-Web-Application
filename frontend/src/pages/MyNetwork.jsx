import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { Avatar } from '../components/common/Avatar';
import { SectionNotifications } from '../components/common/SectionNotifications';
import { AlertCircle, Check, Info, LoaderCircle, LockKeyhole, UserRoundPlus, UsersRound, X } from 'lucide-react';

const displayName = (person) => person.full_name || person.username;
const REQUEST_NOTIFICATION_KINDS = ['CONNECTION_REQUEST', 'FOLLOW_REQUEST'];

export const MyNetwork = ({ setActivePage, onOpenProfile }) => {
  const { user } = useContext(AuthContext);
  const [suggestions, setSuggestions] = useState([]);
  const [requests, setRequests] = useState({ incoming: [], outgoing: [] });
  const [followRequests, setFollowRequests] = useState({ incoming: [], outgoing: [] });
  const [connections, setConnections] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notificationError, setNotificationError] = useState('');
  const [actionError, setActionError] = useState('');
  const [busyId, setBusyId] = useState('');

  const load = useCallback(async () => {
    if (!user) { setLoading(false); return; }
    setLoading(true);
    setError('');
    try {
      const [people, invitations, accepted, follows] = await Promise.all([
        api.getConnectionSuggestions(), api.getConnectionRequests(), api.getConnections(), api.getFollowRequests(),
      ]);
      setSuggestions(people);
      setRequests(invitations);
      setConnections(accepted);
      setFollowRequests(follows);
      try {
        const activity = await api.getNotifications(0, 100, 'network');
        setNotifications(activity.notifications);
        setNotificationError('');
      } catch (notificationLoadError) {
        setNotificationError(notificationLoadError.message || 'Network notification status could not be loaded.');
      }
    } catch (err) {
      setError(err.message || 'Your network could not be loaded. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!user) return undefined;
    let active = true;
    const refreshRequests = async () => {
      try {
        const [invitations, follows, activity] = await Promise.all([
          api.getConnectionRequests(),
          api.getFollowRequests(),
          api.getNotifications(0, 100, 'network'),
        ]);
        if (active) {
          setRequests(invitations);
          setFollowRequests(follows);
          setNotifications(activity.notifications);
          setNotificationError('');
        }
      } catch (err) {
        if (active) setNotificationError(err.message || 'Network activity could not be refreshed.');
      }
    };
    const timer = window.setInterval(refreshRequests, 30000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [user]);

  const runAction = async (id, action) => {
    setBusyId(id);
    setActionError('');
    try {
      await action();
      window.dispatchEvent(new CustomEvent('openvibe:notifications-updated'));
      await load();
    }
    catch (err) { setActionError(err.message || 'That network update could not be saved.'); }
    finally { setBusyId(''); }
  };

  const markRequestOpened = async (notification) => {
    if (!notification || notification.is_read) return;
    try {
      await api.markNotificationRead(notification.id);
      setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item));
      window.dispatchEvent(new CustomEvent('openvibe:notifications-updated'));
    } catch (err) {
      setNotificationError(err.message || 'The request notification could not be updated.');
    }
  };

  const connectionRequestNotification = (request) => notifications.find((item) => item.kind === 'CONNECTION_REQUEST' && item.resource_id === request.id);
  const followRequestNotification = (request) => notifications.find((item) => item.kind === 'FOLLOW_REQUEST' && item.actor_id === request.other_user.id);

  if (!user) return (
    <main id="main-content" className="container page-shell narrow-page">
      <section className="card auth-required-state"><UsersRound size={25} /><h1>Build your network</h1><p>Sign in to find members, send invitations, and manage your connections.</p><button className="btn btn-primary" type="button" onClick={() => setActivePage('login')}>Sign in</button></section>
    </main>
  );

  return (
    <main id="main-content" className="container page-shell">
      <header className="page-heading"><div><span className="eyebrow">YOUR COMMUNITY</span><h1>My network</h1><p>Find members, manage invitations, and keep up with your connections.</p></div><div className="page-heading-mark"><UsersRound size={22} aria-hidden="true" /></div></header>
      <div className="notice-card notice-card-info" role="note"><Info size={18} aria-hidden="true" /><p>Network activity is stored with your account. Suggestions include active OpenVibe members only.</p></div>
      <SectionNotifications section="network" title="Connection updates" setActivePage={setActivePage} excludeKinds={REQUEST_NOTIFICATION_KINDS} />
      {notificationError && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={16} />{notificationError}</div>}
      {actionError && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{actionError}</div>}
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{error}<button className="text-link-button" type="button" onClick={load}>Retry</button></div>}

      <section className="card network-section" aria-labelledby="invitations-heading">
        <div className="section-heading-row"><div><h2 id="invitations-heading">Invitations</h2><p>Connection requests sent to you.</p></div><span className="count-pill">{requests.incoming.length} pending{notifications.filter((item) => item.kind === 'CONNECTION_REQUEST' && !item.is_read).length ? ` · ${notifications.filter((item) => item.kind === 'CONNECTION_REQUEST' && !item.is_read).length} new` : ''}</span></div>
        {loading ? <p className="loading-state" role="status"><LoaderCircle className="spin" size={17} /> Loading invitations…</p> : requests.incoming.length === 0 ? <div className="network-empty-state"><span className="empty-icon"><UserRoundPlus size={21} /></span><div><strong>No invitations yet</strong><p>New requests will appear here.</p></div></div> : <div className="invitation-list">{requests.incoming.map((request) => {
          const notice = connectionRequestNotification(request);
          return <article className={`invitation-row ${notice && !notice.is_read ? 'invitation-row-unread' : ''}`} key={request.id}>
            <button type="button" className="profile-inline-button" onClick={async () => { await markRequestOpened(notice); onOpenProfile?.(request.other_user.id); }}>
              <Avatar name={displayName(request.other_user)} size="lg" />
              <span><strong>{displayName(request.other_user)}</strong><small>{request.other_user.headline || `@${request.other_user.username}`}</small></span>
            </button>
            <div className="invitation-actions">{notice && !notice.is_read && <span className="network-new-indicator">New</span>}<button type="button" className="btn btn-primary btn-sm" disabled={busyId === request.id} onClick={() => runAction(request.id, () => api.acceptConnection(request.id))}><Check size={15} /> Accept</button><button type="button" className="btn btn-secondary btn-sm" disabled={busyId === request.id} onClick={() => runAction(request.id, () => api.rejectConnection(request.id))}><X size={15} /> Ignore</button></div>
          </article>;
        })}</div>}
      </section>

      <section className="card network-section" aria-labelledby="follow-requests-heading">
        <div className="section-heading-row"><div><h2 id="follow-requests-heading">Private account follow requests</h2><p>Approve requests to let members view your private posts and profile details.</p></div><span className="count-pill">{followRequests.incoming.length} pending{notifications.filter((item) => item.kind === 'FOLLOW_REQUEST' && !item.is_read).length ? ` · ${notifications.filter((item) => item.kind === 'FOLLOW_REQUEST' && !item.is_read).length} new` : ''}</span></div>
        {loading ? <p className="loading-state" role="status"><LoaderCircle className="spin" size={17} /> Loading follow requests…</p> : followRequests.incoming.length === 0 ? <div className="network-empty-state"><span className="empty-icon"><LockKeyhole size={21} /></span><div><strong>No follow requests</strong><p>Requests to follow your private account will appear here.</p></div></div> : <div className="invitation-list">{followRequests.incoming.map((request) => {
          const notice = followRequestNotification(request);
          return <article className={`invitation-row ${notice && !notice.is_read ? 'invitation-row-unread' : ''}`} key={request.id}>
            <button type="button" className="profile-inline-button" onClick={async () => { await markRequestOpened(notice); onOpenProfile?.(request.other_user.id); }}>
              <Avatar name={displayName(request.other_user)} src={request.other_user.avatar_url} size="lg" />
              <span><strong>{displayName(request.other_user)}</strong><small>{request.other_user.headline || `@${request.other_user.username}`}</small></span>
            </button>
            <div className="invitation-actions">{notice && !notice.is_read && <span className="network-new-indicator">New</span>}<button type="button" className="btn btn-primary btn-sm" disabled={busyId === request.id} onClick={() => runAction(request.id, () => api.acceptFollowRequest(request.other_user.id))}><Check size={15} /> Accept</button><button type="button" className="btn btn-secondary btn-sm" disabled={busyId === request.id} onClick={() => runAction(request.id, () => api.rejectFollowRequest(request.other_user.id))}><X size={15} /> Reject</button></div>
          </article>;
        })}</div>}
        {followRequests.outgoing.length > 0 && <div className="invitation-list"><h3 className="follow-request-subheading">Requests you sent</h3>{followRequests.outgoing.map((request) => <article className="invitation-row" key={request.id}><button type="button" className="profile-inline-button" onClick={() => onOpenProfile?.(request.other_user.id)}><Avatar name={displayName(request.other_user)} src={request.other_user.avatar_url} size="md" /><span><strong>{displayName(request.other_user)}</strong><small>@{request.other_user.username}</small></span></button><span className="preview-pill">Awaiting approval</span></article>)}</div>}
      </section>

      {requests.outgoing.length > 0 && <section className="card network-section" aria-labelledby="sent-heading"><div className="section-heading-row"><div><h2 id="sent-heading">Sent invitations</h2><p>Requests waiting for a response.</p></div><span className="count-pill">{requests.outgoing.length}</span></div><div className="invitation-list">{requests.outgoing.map((request) => <article className="invitation-row" key={request.id}><button type="button" className="profile-inline-button" onClick={() => onOpenProfile?.(request.other_user.id)}><Avatar name={displayName(request.other_user)} size="lg" /><span><strong>{displayName(request.other_user)}</strong><small>{request.other_user.headline || `@${request.other_user.username}`}</small></span></button><span className="preview-pill">Pending</span></article>)}</div></section>}

      <section className="card network-section" aria-labelledby="connections-heading"><div className="section-heading-row"><div><h2 id="connections-heading">Your connections</h2><p>Members who have accepted your invitation.</p></div><span className="count-pill">{connections.length}</span></div>{loading ? <p className="loading-state" role="status"><LoaderCircle className="spin" size={17} /> Loading connections…</p> : connections.length === 0 ? <div className="network-empty-state"><span className="empty-icon"><UsersRound size={21} /></span><div><strong>Your network is ready to grow</strong><p>Connect with members below to start messaging.</p></div></div> : <div className="people-grid">{connections.map((person) => <article className="person-card" key={person.id}><div className="person-cover" aria-hidden="true" /><Avatar name={displayName(person)} size="xl" className="person-avatar" /><div className="person-card-body"><button type="button" className="person-name-button" onClick={() => onOpenProfile?.(person.id)}>{displayName(person)}</button><p>{person.headline || `@${person.username}`}</p><span className="person-demo-note">Connected</span><div className="person-card-actions"><button type="button" className="btn btn-secondary btn-sm" onClick={() => { window.dispatchEvent(new CustomEvent('openvibe:message-member', { detail: { userId: person.id } })); setActivePage('messages'); }}>Message</button><button type="button" className="btn btn-quiet btn-sm" disabled={busyId === person.id} onClick={() => runAction(person.id, () => api.removeConnection(person.id))}>Remove</button></div></div></article>)}</div>}</section>

      <section className="network-section" aria-labelledby="people-heading"><div className="section-heading-row network-section-title"><div><h2 id="people-heading">People you may know</h2><p>Active OpenVibe members with profiles you can view.</p></div></div>{loading ? <div className="card loading-state" role="status"><LoaderCircle className="spin" size={17} /> Finding members…</div> : suggestions.length === 0 ? <div className="card empty-state"><h3>No new suggestions</h3><p>Check back as more members join OpenVibe.</p></div> : <div className="people-grid">{suggestions.map((person) => <article className="person-card" key={person.id}><div className="person-cover" aria-hidden="true" /><Avatar name={displayName(person)} size="xl" className="person-avatar" /><div className="person-card-body"><button type="button" className="person-name-button" onClick={() => onOpenProfile?.(person.id)}>{displayName(person)}</button><p>{person.headline || `@${person.username}`}</p><span className="person-demo-note">{person.connection_count} connections</span><div className="person-card-actions"><button type="button" className="btn btn-outline btn-sm" disabled={busyId === person.id} onClick={() => runAction(person.id, () => api.requestConnection(person.id))}><UserRoundPlus size={15} /> Connect</button><button type="button" className="btn btn-quiet btn-sm" disabled={busyId === person.id} onClick={() => runAction(person.id, () => api.followUser(person.id))}>Follow</button></div></div></article>)}</div>}</section>
    </main>
  );
};
