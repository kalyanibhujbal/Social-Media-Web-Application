import React, { createContext, useContext, useState } from 'react';
import { AuthContext } from './AuthContext';
import { api } from '../services/api';

const CONSENT_KEY = 'cookie_consent';
export const ConsentContext = createContext(null);

export const ConsentProvider = ({ children }) => {
  const { user } = useContext(AuthContext);
  const [initialPreference] = useState(() => {
    try {
      const saved = localStorage.getItem(CONSENT_KEY);
      if (!saved) return { consentGiven: false, analyticsAllowed: false };
      const parsed = JSON.parse(saved);
      if (typeof parsed.analytics !== 'boolean') return { consentGiven: false, analyticsAllowed: false };
      return { consentGiven: true, analyticsAllowed: parsed.analytics };
    } catch {
      try { localStorage.removeItem(CONSENT_KEY); } catch { /* Browser storage is unavailable. */ }
      return { consentGiven: false, analyticsAllowed: false };
    }
  });
  const [consentGiven, setConsentGiven] = useState(initialPreference.consentGiven);
  const [analyticsAllowed, setAnalyticsAllowed] = useState(initialPreference.analyticsAllowed);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [consentMessage, setConsentMessage] = useState('');

  const savePreference = async (analytics) => {
    setAnalyticsAllowed(analytics);
    setConsentGiven(true);
    setPreferencesOpen(false);
    setConsentMessage('Your preference is saved in this browser. This version does not load analytics or tracking tools.');
    try {
      localStorage.setItem(CONSENT_KEY, JSON.stringify({
        consent_type: 'analytics_cookies',
        status: analytics ? 'GRANTED' : 'WITHDRAWN',
        analytics,
        policy_version: '1.0',
        timestamp: new Date().toISOString(),
      }));
    } catch {
      setConsentMessage('This browser could not store your preference. No optional analytics or tracking tools are active.');
    }
    if (user) {
      try {
        await api.saveConsent(analytics);
      } catch {
        setConsentMessage('Your browser preference is saved. The account preference record could not be updated.');
      }
    }
  };

  return (
    <ConsentContext.Provider value={{
      consentGiven,
      analyticsAllowed,
      preferencesOpen,
      consentMessage,
      acceptAll: () => savePreference(true),
      acceptNecessaryOnly: () => savePreference(false),
      openPreferences: () => { setConsentMessage(''); setPreferencesOpen(true); },
      closePreferences: () => setPreferencesOpen(false),
    }}>
      {children}
    </ConsentContext.Provider>
  );
};
