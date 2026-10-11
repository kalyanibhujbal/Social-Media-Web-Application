import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { api } from '../services/api';
import { Avatar } from '../components/common/Avatar';
import { AlertCircle, LoaderCircle, MessageSquareText, RefreshCw, Search, Send } from 'lucide-react';

const displayName = (person) => person?.full_name || person?.username || 'OpenVibe member';
const formatTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(date);
};

export const Messages = ({ setActivePage }) => {
  const { user } = useContext(AuthContext);
  const [conversations, setConversations] = useState([]);
  const [connections, setConnections] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [conversation, setConversation] = useState(null);
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!user) { setLoading(false); return; }
    setLoading(true);
    setError('');
    try {
      const [items, members] = await Promise.all([api.getConversations(), api.getConnections()]);
      setConversations(items);
      setConnections(members);
      if (!selectedId && items.length) setSelectedId(items[0].id);
    } catch (err) {
      setError(err.message || 'Your inbox could not be loaded. Please try again.');
    } finally { setLoading(false); }
  }, [user, selectedId]);

  useEffect(() => { load(); }, [load]);

  const openConversation = useCallback(async (id) => {
    if (!id) return;
    setSelectedId(id);
    setError('');
    try {
      const result = await api.getConversation(id);
      setConversation(result);
      await api.markConversationRead(id);
      setConversations((items) => items.map((item) => item.id === id ? { ...item, unread_count: 0 } : item));
    } catch (err) { setError(err.message || 'This conversation could not be opened.'); }
  }, []);

  useEffect(() => { if (selectedId) openConversation(selectedId); }, [selectedId, openConversation]);

  const startWith = async (memberId) => {
    setError('');
    try {
      const result = await api.startConversation(memberId);
      setConversations((items) => [result, ...items.filter((item) => item.id !== result.id)]);
      setSelectedId(result.id);
    } catch (err) { setError(err.message || 'Could not start this conversation.'); }
  };

  useEffect(() => {
    const handleStart = (event) => { if (event.detail?.userId) startWith(event.detail.userId); };
    window.addEventListener('openvibe:message-member', handleStart);
    return () => window.removeEventListener('openvibe:message-member', handleStart);
  }, [connections]);

  const send = async (event) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !selectedId || sending) return;
    setSending(true);
    setError('');
    try {
      const result = await api.sendMessage(selectedId, content);
      setConversation((current) => current ? { ...current, messages: [...current.messages, result] } : current);
      setDraft('');
      setConversations((items) => items.map((item) => item.id === selectedId ? { ...item, last_message: result.content.slice(0, 160), last_message_at: result.created_at } : item).sort((a, b) => (b.last_message_at || '').localeCompare(a.last_message_at || '')));
    } catch (err) { setError(err.message || 'Message could not be sent.'); }
    finally { setSending(false); }
  };

  if (!user) return <main id="main-content" className="container page-shell narrow-page"><section className="card auth-required-state"><MessageSquareText size={25} /><h1>Sign in to view messages</h1><p>Private conversations are available to connected members.</p><button className="btn btn-primary" type="button" onClick={() => setActivePage('login')}>Sign in</button></section></main>;

  const visible = conversations.filter((item) => displayName(item.other_user).toLowerCase().includes(query.toLowerCase()) || item.other_user?.username?.toLowerCase().includes(query.toLowerCase()));
  const current = conversation?.id === selectedId ? conversation : null;

  return (
    <main id="main-content" className="container page-shell">
      <header className="page-heading"><div><span className="eyebrow">PRIVATE CONVERSATIONS</span><h1>Messages</h1><p>Text conversations with your accepted connections.</p></div><button className="btn btn-secondary btn-sm" type="button" onClick={load} disabled={loading}><RefreshCw size={15} /> Refresh inbox</button></header>
      {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} />{error}</div>}
      <section className="messages-shell card" aria-label="Messages">
        <aside className="conversation-list" aria-label="Conversation list">
          <div className="conversation-list-heading"><h2>Inbox</h2><label className="conversation-search"><Search size={16} aria-hidden="true" /><input type="search" placeholder="Search conversations" aria-label="Search conversations" value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
          {loading ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={17} /> Loading inbox…</div> : visible.length ? <ul className="conversation-items">{visible.map((item) => <li key={item.id}><button type="button" className={`conversation-item ${selectedId === item.id ? 'active' : ''}`} onClick={() => openConversation(item.id)}><Avatar name={displayName(item.other_user)} size="md" /><span className="conversation-item-copy"><strong>{displayName(item.other_user)}</strong><small>{item.last_message || 'Conversation started'}</small></span><span className="conversation-item-meta">{item.unread_count > 0 && <span className="count-pill">{item.unread_count}</span>}<time>{formatTime(item.last_message_at)}</time></span></button></li>)}</ul> : <div className="conversation-list-empty"><MessageSquareText size={21} /><strong>No conversations</strong><span>Start a conversation with an accepted connection.</span></div>}
          {connections.length > 0 && <div className="message-start-list"><h3>Start a conversation</h3>{connections.map((member) => <button type="button" key={member.id} onClick={() => startWith(member.id)}><Avatar name={displayName(member)} size="sm" /><span>{displayName(member)}</span></button>)}</div>}
        </aside>
        <div className="conversation-panel">
          {current ? <>
            <header className="conversation-header"><Avatar name={displayName(current.other_user)} size="md" /><div><strong>{displayName(current.other_user)}</strong><span>{current.other_user?.headline || `@${current.other_user?.username}`}</span></div></header>
            <div className="message-history" aria-live="polite">{current.messages.length ? current.messages.map((message) => <article className={`message-bubble ${message.sender_id === user.id ? 'mine' : ''}`} key={message.id}><p>{message.content}</p><time dateTime={message.created_at}>{formatTime(message.created_at)}</time></article>) : <div className="conversation-placeholder"><span className="empty-icon"><MessageSquareText size={23} /></span><h2>Say hello</h2><p>Your messages are stored in this conversation and visible to its two members.</p></div>}</div>
            <form className="message-composer" onSubmit={send}><label htmlFor="message-input" className="sr-only">Message text</label><input id="message-input" type="text" placeholder="Write a message…" maxLength={2000} value={draft} onChange={(event) => setDraft(event.target.value)} required /><button type="submit" className="btn btn-primary btn-icon" aria-label="Send message" disabled={sending || !draft.trim()}><Send size={17} />{sending ? 'Sending…' : ''}</button></form>
            <p className="message-privacy-note">Text only · messages are not processed by the moderation classifier.</p>
          </> : <div className="conversation-placeholder"><span className="empty-icon"><MessageSquareText size={24} /></span><h2>{loading ? 'Loading your inbox' : 'Choose a conversation'}</h2><p>{connections.length ? 'Select an existing thread or start a conversation with a connection.' : 'Connect with another member first to send a message.'}</p>{!loading && !connections.length && <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActivePage('network')}>Find connections</button>}</div>}
        </div>
      </section>
    </main>
  );
};
