import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { ConsentProvider } from './context/ConsentContext';
import { Navbar } from './components/common/Navbar';
import { Footer } from './components/common/Footer';
import { CookieBanner } from './components/common/CookieBanner';
import { MobileNavigation } from './components/common/MobileNavigation';

import { Home } from './pages/Home';
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

  const openProfile = (id) => { setProfileUserId(id); setActivePage('profile'); };
  const openOwnProfile = () => { setProfileUserId(null); setActivePage('profile'); };

  const renderPage = () => {
    switch (activePage) {
      case 'home':
        return <Home setActivePage={setActivePage} searchQuery={searchQuery} onSearch={setSearchQuery} onOpenProfile={openProfile} onOpenOwnProfile={openOwnProfile} />;
      case 'network':
        return <MyNetwork setActivePage={setActivePage} onOpenProfile={openProfile} />;
      case 'notifications':
        return <Notifications setActivePage={setActivePage} />;
      case 'messages':
        return <Messages setActivePage={setActivePage} />;
      case 'profile':
        return <Profile setActivePage={setActivePage} viewedUserId={profileUserId} />;
      case 'saved':
        return <SavedPosts setActivePage={setActivePage} />;
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
        return <Home setActivePage={setActivePage} searchQuery={searchQuery} onSearch={setSearchQuery} onOpenProfile={openProfile} onOpenOwnProfile={openOwnProfile} />;
    }
  };

  return (
    <AuthProvider>
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
    </AuthProvider>
  );
}

export default App;
