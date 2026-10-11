import React, { useContext, useState } from 'react';
import { ConsentContext } from '../../context/ConsentContext';

export const CookieBanner = () => {
  const {
    consentGiven,
    analyticsAllowed,
    preferencesOpen,
    consentMessage,
    acceptAll,
    acceptNecessaryOnly,
    openPreferences,
    closePreferences,
  } = useContext(ConsentContext);
  const [analyticsChoice, setAnalyticsChoice] = useState(analyticsAllowed);

  if (consentGiven && !preferencesOpen) return null;

  return (
    <section
      className="cookie-banner"
      aria-label="Cookie and storage preferences"
      aria-describedby="cookie-description"
    >
      <div className="container cookie-banner-content">
        <div>
          <h2 className="cookie-banner-title">Cookie and storage preferences</h2>
          <p id="cookie-description">
            Essential session cookie: required for sign-in. Analytics and marketing cookies are not
            active in this version. Your optional preference is saved in this browser; if you are
            signed in, the analytics preference is also recorded on your account.
          </p>
          {preferencesOpen && (
            <div className="cookie-preferences">
              <div className="consent-category"><strong>Essential</strong><span>Always on while signed in · required for account access</span></div>
              <label htmlFor="optional-analytics">
                <input
                  id="optional-analytics"
                  type="checkbox"
                  checked={analyticsChoice}
                  onChange={(event) => setAnalyticsChoice(event.target.checked)}
                />
                <span><strong>Analytics</strong><small>No analytics tools are active in this version.</small></span>
              </label>
              <div className="consent-category"><strong>Marketing</strong><span>Off · no marketing or ad tracking is used</span></div>
              <p>If analytics tools are added later, they will only run after you enable this preference.</p>
            </div>
          )}
          {consentMessage && <p role="status" className="cookie-status">{consentMessage}</p>}
        </div>
        <div className="cookie-banner-actions">
          {preferencesOpen ? (
            <>
              <button type="button" className="btn btn-secondary" onClick={closePreferences}>Cancel</button>
              <button type="button" className="btn btn-secondary" onClick={acceptNecessaryOnly}>Reject Non-Essential</button>
              <button type="button" className="btn btn-primary" onClick={() => analyticsChoice ? acceptAll() : acceptNecessaryOnly()}>
                Save preferences
              </button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn-secondary" onClick={acceptNecessaryOnly}>Reject Non-Essential</button>
              <button type="button" className="btn btn-secondary" onClick={() => { setAnalyticsChoice(analyticsAllowed); openPreferences(); }}>Manage preferences</button>
              <button type="button" className="btn btn-primary" onClick={acceptAll}>Accept All</button>
            </>
          )}
        </div>
      </div>
    </section>
  );
};
