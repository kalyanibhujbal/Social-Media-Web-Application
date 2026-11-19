import React from 'react';
import { Plus } from 'lucide-react';
import { PostFeed } from '../components/posts/PostFeed';

export const Events = ({ onOpenProfile, onOpenArticle, onCreateEvent }) => (
  <main id="main-content" className="container page-shell narrow-page">
    <header className="page-heading">
      <div>
        <span className="eyebrow">MEET THE COMMUNITY</span>
        <h1>Events</h1>
        <p>Discover gatherings, conversations, and shared experiences.</p>
      </div>
      <button type="button" className="btn btn-primary" onClick={onCreateEvent}><Plus size={16} /> Create event</button>
    </header>
    <PostFeed contentType="EVENT" onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />
  </main>
);
