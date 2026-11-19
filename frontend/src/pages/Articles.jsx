import React from 'react';
import { Plus } from 'lucide-react';
import { PostFeed } from '../components/posts/PostFeed';
import { SectionNotifications } from '../components/common/SectionNotifications';

export const Articles = ({ setActivePage, onOpenProfile, onOpenArticle, onCreateArticle }) => (
  <main id="main-content" className="container page-shell narrow-page">
    <header className="page-heading">
      <div>
        <span className="eyebrow">IDEAS IN DEPTH</span>
        <h1>Articles</h1>
        <p>Thoughtful long-form stories and perspectives from OpenVibe members.</p>
      </div>
      <button type="button" className="btn btn-primary" onClick={onCreateArticle}><Plus size={16} /> Write an article</button>
    </header>
    <SectionNotifications section="articles" title="New articles from your network" setActivePage={setActivePage} onOpenArticle={onOpenArticle} />
    <PostFeed contentType="ARTICLE" onOpenProfile={onOpenProfile} onOpenArticle={onOpenArticle} />
  </main>
);
