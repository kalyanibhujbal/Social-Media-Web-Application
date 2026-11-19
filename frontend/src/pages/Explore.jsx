import React from 'react';
import { Compass, Globe2 } from 'lucide-react';
import { PostFeed } from '../components/posts/PostFeed';

export const Explore = ({ onOpenProfile, onOpenArticle }) => (
  <main id="main-content" className="container page-shell">
    <header className="page-heading">
      <div>
        <span className="eyebrow">OPENVIBE DISCOVERY</span>
        <h1>Explore</h1>
        <p>Find thoughtful conversations and meet the people behind them.</p>
      </div>
      <div className="page-heading-mark"><Compass size={22} aria-hidden="true" /></div>
    </header>
    <div className="notice-card notice-card-info explore-privacy-note" role="note">
      <Globe2 size={17} aria-hidden="true" />
      <p>Explore includes approved posts from public accounts. Private-account posts are never shown here.</p>
    </div>
    <PostFeed explore onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />
  </main>
);
