import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { ConsentProvider } from './context/ConsentContext';
import { NotificationCountProvider } from './context/NotificationCountContext';
import { Navbar } from './components/common/Navbar';
import { Footer } from './components/common/Footer';
import { CookieBanner } from './components/common/CookieBanner';
import { MobileNavigation } from './components/common/MobileNavigation';

import { Home } from './pages/Home';
import { Explore } from './pages/Explore';
import { Events } from './pages/Events';
import { Articles } from './pages/Articles';
import { ArticleReader } from './pages/ArticleReader';
import { MyNetwork } from './pages/MyNetwork';
import { Notifications } from './pages/Notifications';
import { Messages } from './pages/Messages';
import { Profile } from './pages/Profile';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { AccountSettings } from './pages/AccountSettings';
import { LegalPages } from './pages/LegalPages';
import { SavedPosts } from './pages/SavedPosts';

export function App() {
  const [activePage, setActivePage] = useState('home');
  const [searchQuery, setSearchQuery] = useState('');
  const [profileUserId, setProfileUserId] = useState(null);
  const [selectedArticle, setSelectedArticle] = useState(null);

  const openProfile = (id) => { setProfileUserId(id); setActivePage('profile'); };
  const openOwnProfile = () => { setProfileUserId(null); setActivePage('profile'); };
  const openArticle = (article) => { setSelectedArticle(article); setActivePage('article'); };
  const openComposerFormat = (format) => {
    setActivePage('home');
    window.setTimeout(() => {
      document.querySelector(`[data-content-format="${format}"]`)?.click();
      document.getElementById('post-content')?.focus();
    }, 80);
  };

  const renderPage = () => {
    switch (activePage) {
      case 'home':
        return <Home setActivePage={setActivePage} searchQuery={searchQuery} onSearch={setSearchQuery} onOpenProfile={openProfile} onOpenOwnProfile={openOwnProfile} onOpenArticle={openArticle} />;
      case 'explore':
        return <Explore setActivePage={setActivePage} onOpenProfile={openProfile} onOpenArticle={openArticle} />;
      case 'events':
        return <Events setActivePage={setActivePage} onOpenProfile={openProfile} onOpenArticle={openArticle} onCreateEvent={() => openComposerFormat('event')} />;
      case 'articles':
        return <Articles setActivePage={setActivePage} onOpenProfile={openProfile} onOpenArticle={openArticle} onCreateArticle={() => openComposerFormat('article')} />;
      case 'article':
        return <ArticleReader key={selectedArticle?.id} article={selectedArticle} onBack={() => setActivePage('articles')} onOpenProfile={openProfile} onArticleUpdated={setSelectedArticle} onArticleDeleted={() => { setSelectedArticle(null); setActivePage('articles'); }} />;
      case 'network':
        return <MyNetwork setActivePage={setActivePage} onOpenProfile={openProfile} />;
      case 'notifications':
        return <Notifications setActivePage={setActivePage} onOpenArticle={openArticle} />;
      case 'messages':
        return <Messages setActivePage={setActivePage} />;
      case 'profile':
        return <Profile setActivePage={setActivePage} viewedUserId={profileUserId} onOpenProfile={openProfile} onOpenArticle={openArticle} />;
      case 'saved':
        return <SavedPosts setActivePage={setActivePage} onOpenProfile={openProfile} onOpenArticle={openArticle} />;
      case 'login':
        return <Login setActivePage={setActivePage} />;
      case 'register':
        return <Register setActivePage={setActivePage} />;
      case 'dashboard':
        return <Dashboard />;
      case 'admin':
        return <AdminDashboard />;
      case 'account-settings':
        return <AccountSettings />;
      case 'privacy-policy':
      case 'terms':
      case 'cookies-policy':
      case 'refund-policy':
      case 'consent':
      case 'data-rights':
      case 'grievance':
      case 'ai-transparency':
      case 'accessibility':
      case 'copyright':
        return <LegalPages pageType={activePage} setActivePage={setActivePage} />;
      default:
        return <Home setActivePage={setActivePage} searchQuery={searchQuery} onSearch={setSearchQuery} onOpenProfile={openProfile} onOpenOwnProfile={openOwnProfile} onOpenArticle={openArticle} />;
    }
  };

  return (
    <AuthProvider>
      <NotificationCountProvider>
        <ConsentProvider>
          <div className="app-shell">
            <Navbar
              activePage={activePage}
              setActivePage={setActivePage}
              searchQuery={searchQuery}
              onSearch={(query) => { setSearchQuery(query); setActivePage('home'); }}
              onOpenProfile={openProfile}
              onOpenOwnProfile={openOwnProfile}
            />
            <div className="app-content">{renderPage()}</div>
            <Footer setActivePage={setActivePage} />
            <MobileNavigation activePage={activePage} setActivePage={(page) => { if (page === 'profile') openOwnProfile(); else setActivePage(page); }} />
            <CookieBanner />
          </div>
        </ConsentProvider>
      </NotificationCountProvider>
    </AuthProvider>
  );
}

export default App;
