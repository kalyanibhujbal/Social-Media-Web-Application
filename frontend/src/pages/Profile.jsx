import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { Avatar } from '../components/common/Avatar';
import { BrandImage } from '../components/common/BrandImage';
import { PostCard } from '../components/posts/PostCard';
import { AlertCircle, CalendarDays, FileText, LockKeyhole, MapPin, Settings, ShieldCheck, UserRound, UserRoundPlus, UsersRound } from 'lucide-react';

const formatJoinDate = (value) => {
  if (!value) return 'Not available';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not available' : new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(date);
};

export const Profile = ({ setActivePage, viewedUserId }) => {
  const { user } = useContext(AuthContext);
  const isOtherProfile = Boolean(viewedUserId && viewedUserId !== user?.id);
  const [profile, setProfile] = useState(isOtherProfile ? null : user);
  const [userPosts, setUserPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionNotice, setActionNotice] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (isOtherProfile) {
        const [details, posts] = await Promise.all([api.getPublicProfile(viewedUserId), api.getPublicUserPosts(viewedUserId)]);
        setProfile(details);
        setUserPosts(posts);
      } else if (user) {
        setProfile(user);
        setUserPosts(await api.getMyPosts());
      }
    } catch (err) { setError(err.message || 'Profile activity could not be loaded.'); }
    finally { setLoading(false); }
  }, [isOtherProfile, viewedUserId, user]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const updateRelationship = async (action) => {
    setActionBusy(true);
    setActionNotice('');
    setError('');
    try {
      const result = await action();
      setProfile((current) => ({ ...current, ...result }));
      if (result.following === true) setProfile((current) => ({ ...current, relationship: 'FOLLOWING', follower_count: result.follower_count }));
      if (result.following === false) setProfile((current) => ({ ...current, relationship: 'NONE', follower_count: result.follower_count }));
      if (result.status === 'PENDING') setProfile((current) => ({ ...current, relationship: 'REQUEST_SENT' }));
      setActionNotice(result.status === 'PENDING' ? 'Connection request sent.' : result.following ? 'You are now following this member.' : 'You unfollowed this member.');
    } catch (err) { setError(err.message || 'Your network update could not be saved.'); }
    finally { setActionBusy(false); }
  };

  if (!user && !viewedUserId) return <main id="main-content" className="container page-shell narrow-page"><section className="card auth-required-state"><LockKeyhole size={25} /><h1>Sign in to view your profile</h1><p>Your account profile and activity are private to your signed-in session.</p><button type="button" className="btn btn-primary" onClick={() => setActivePage('login')}>Sign in</button></section></main>;

  const name = profile?.full_name || profile?.username || 'OpenVibe member';
  const relationship = profile?.relationship || 'NONE';
  const canConnect = user && profile && user.id !== profile.id;

  return (
    <main id="main-content" className="container page-shell">
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{error}<button type="button" className="text-link-button" onClick={() => setRefreshKey((key) => key + 1)}>Retry</button></div>}
      {actionNotice && <div className="notice-card notice-card-success" role="status">{actionNotice}</div>}
      {loading && !profile ? <div className="card loading-state" role="status">Loading profile…</div> : profile && <>
        <section className="card profile-hero">
          <BrandImage className="profile-cover" src="/images/cover.jpg" alt="OpenVibe profile cover artwork" loading="eager" />
          <div className="profile-hero-content">
            <Avatar name={name} size="xxl" className="profile-avatar" />
            <div className="profile-hero-actions">
              {canConnect && relationship === 'NONE' && <button type="button" className="btn btn-outline btn-sm" disabled={actionBusy} onClick={() => updateRelationship(() => api.requestConnection(profile.id))}><UserRoundPlus size={15} /> Connect</button>}
              {canConnect && (relationship === 'REQUEST_SENT' || relationship === 'REQUEST_RECEIVED') && <span className="preview-pill">Request pending</span>}
              {canConnect && relationship === 'CONNECTED' && <button type="button" className="btn btn-secondary btn-sm" onClick={() => { window.dispatchEvent(new CustomEvent('openvibe:message-member', { detail: { userId: profile.id } })); setActivePage('messages'); }}>Message</button>}
              {canConnect && relationship !== 'FOLLOWING' && relationship !== 'CONNECTED' && <button type="button" className="btn btn-secondary btn-sm" disabled={actionBusy} onClick={() => updateRelationship(() => api.followUser(profile.id))}>Follow</button>}
              {canConnect && relationship === 'FOLLOWING' && <button type="button" className="btn btn-secondary btn-sm" disabled={actionBusy} onClick={() => updateRelationship(() => api.unfollowUser(profile.id))}>Following</button>}
              {!isOtherProfile && <><button type="button" className="btn btn-secondary btn-sm" onClick={() => setActivePage('account-settings')}><Settings size={15} /> Edit profile</button><button type="button" className="btn btn-primary btn-sm" onClick={() => setActivePage('data-rights')}><LockKeyhole size={15} /> Privacy & data</button></>}
            </div>
            <h1>{name}</h1>
            <p className="profile-subtitle">{profile?.headline || `@${profile?.username}`}</p>
            {profile?.location && <p className="profile-location"><MapPin size={15} />{profile.location}</p>}
            <div className="profile-meta"><span><CalendarDays size={15} /> Member since {formatJoinDate(profile?.created_at)}</span><span><UsersRound size={15} /> {profile?.connection_count || 0} connections</span><span><UserRound size={15} /> {profile?.follower_count || 0} followers</span><span><FileText size={15} /> {userPosts.length} posts</span></div>
          </div>
        </section>

        <div className="profile-content-grid">
          <div className="profile-main-column">
            <section className="card profile-section"><div className="section-heading-row"><h2>About</h2><span className="sample-label">PROFILE</span></div><p>{profile?.about || 'This member has not added an about section yet.'}</p>{profile?.skills?.length > 0 && <div className="profile-skill-list" aria-label="Skills">{profile.skills.map((skill) => <span className="tag-pill" key={skill}>{skill}</span>)}</div>}</section>
            <section className="profile-section" aria-labelledby="activity-heading"><div className="section-heading-row"><div><h2 id="activity-heading">Activity</h2><p>{isOtherProfile ? 'Approved public posts from this member.' : 'Your posts and their current moderation results.'}</p></div><ShieldCheck size={19} aria-hidden="true" /></div>{loading && <div className="profile-loading" role="status"><span className="skeleton-line" /><span className="skeleton-line short" /></div>}{!loading && !error && userPosts.length === 0 && <div className="card empty-state"><span className="empty-icon"><FileText size={22} /></span><h3>No posts yet</h3><p>Approved posts from this profile will appear here.</p>{!isOtherProfile && <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActivePage('home')}>Go to the feed</button>}</div>}{!error && userPosts.map((post) => <PostCard key={post.id} post={post} />)}</section>
          </div>
          <aside className="profile-side-column">
            <section className="card profile-details-card"><h2><UserRound size={17} /> Profile details</h2><dl><div><dt>Username</dt><dd>@{profile?.username}</dd></div>{!isOtherProfile && <><div><dt>Account email</dt><dd>{profile?.email}</dd></div><div><dt>Account type</dt><dd>{profile?.role === 'ADMIN' ? 'Administrator' : 'Member'}</dd></div></>}<div><dt>Joined</dt><dd>{formatJoinDate(profile?.created_at)}</dd></div></dl>{!isOtherProfile && <button type="button" className="text-link-button" onClick={() => setActivePage('account-settings')}>Edit account details</button>}</section>
            <section className="card profile-note-card"><ShieldCheck size={19} /><h2>{isOtherProfile ? 'Responsible community' : 'Your data stays in context'}</h2><p>{isOtherProfile ? 'Profile details are public. Account email and private activity are not shown here.' : 'Moderation history is visible in your account dashboard. Export or delete your account from the Privacy Center.'}</p>{!isOtherProfile && <button type="button" className="text-link-button" onClick={() => setActivePage('dashboard')}>Open dashboard</button>}</section>
          </aside>
        </div>
      </>}
    </main>
  );
};
