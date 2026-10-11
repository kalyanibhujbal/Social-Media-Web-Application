import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { ConsentContext } from '../context/ConsentContext';
import { api } from '../services/api';

const updated = '2 October 2026';
const cardStyle = { display: 'grid', gap: '0.9rem' };

function RequestForm({ requestType = 'PRIVACY_CONCERN', onSubmitted }) {
  const { user } = useContext(AuthContext);
  const [category, setCategory] = useState(requestType);
  const [description, setDescription] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const created = await api.createPrivacyRequest(category, description);
      setMessage(`Request received (${created.id}). You can check its status on this page.`);
      setDescription('');
      onSubmitted?.();
    } catch (err) {
      setError(err.message || 'Could not submit request.');
    } finally {
      setBusy(false);
    }
  };

  if (!user) {
    return <p>Please sign in to submit a private data or grievance request. Requests are tied to your account and are visible only to you and authorized administrators.</p>;
  }

  return (
    <form onSubmit={submit} style={cardStyle}>
      <div className="form-group">
        <label className="form-label" htmlFor="privacy-request-type">Request type</label>
        <select id="privacy-request-type" className="form-input" value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="CORRECT">Correct my account information</option>
          <option value="DELETE">Request data deletion</option>
          <option value="WITHDRAW_CONSENT">Withdraw optional consent</option>
          <option value="PROCESSING_QUESTION">Ask about data processing</option>
          <option value="PRIVACY_CONCERN">Submit a privacy concern or grievance</option>
        </select>
      </div>
      <div className="form-group">
        <label className="form-label" htmlFor="privacy-request-description">Details (optional)</label>
        <textarea
          id="privacy-request-description"
          className="form-input"
          rows={4}
          maxLength={2000}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          aria-describedby="privacy-request-help"
        />
        <p id="privacy-request-help" className="form-help">Do not include passwords, payment details, or information about another person. Maximum 2,000 characters.</p>
      </div>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? 'Submitting…' : 'Submit private request'}</button>
    </form>
  );
}

export const LegalPages = ({ pageType, setActivePage }) => {
  const { user } = useContext(AuthContext);
  const { openPreferences, analyticsAllowed, consentMessage } = useContext(ConsentContext);
  const [dataExport, setDataExport] = useState(null);
  const [requests, setRequests] = useState([]);
  const [contact, setContact] = useState(null);
  const [error, setError] = useState('');

  const loadRequests = useCallback(async () => {
    if (!user) return;
    try {
      setRequests(await api.getMyPrivacyRequests());
    } catch (err) {
      setError(err.message || 'Could not load requests.');
    }
  }, [user]);

  useEffect(() => {
    if (pageType === 'data-rights' || pageType === 'grievance') loadRequests();
  }, [pageType, loadRequests]);

  useEffect(() => {
    if (pageType !== 'privacy-policy' && pageType !== 'grievance' && pageType !== 'terms') return;
    api.getPrivacyContact().then(setContact).catch(() => setContact(null));
  }, [pageType]);

  const exportData = async () => {
    setError('');
    try {
      const data = await api.exportData();
      setDataExport(data);
    } catch (err) {
      setError(err.message || 'Export failed. Please sign in.');
    }
  };

  const downloadExport = () => {
    if (!dataExport) return;
    const blob = new Blob([JSON.stringify(dataExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'my-account-data.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const deleteAccount = async () => {
    if (!window.confirm('Delete your account, posts, comments, consent records, and related moderation records? This cannot be undone.')) return;
    try {
      await api.deleteAccount();
      window.location.reload();
    } catch (err) {
      setError(err.message || 'Account deletion failed.');
    }
  };

  return (
    <main id="main-content" className="container legal-page">
      {pageType === 'privacy-policy' && (
        <article className="card legal-content">
          <h1>Privacy Policy</h1>
          <p>Effective date: {updated}. This notice describes the application as implemented. It is not a legal certification.</p>
          <div><strong>Operator and contact:</strong>{contact?.organization_name || contact?.official_email || contact?.official_address || contact?.grievance_contact ? (
            <address className="contact-address">
              {contact.organization_name && <span>{contact.organization_name}</span>}
              {contact.official_email && <a href={`mailto:${contact.official_email}`}>{contact.official_email}</a>}
              {contact.official_address && <span>{contact.official_address}</span>}
              {contact.grievance_contact && <a href={`mailto:${contact.grievance_contact}`}>Grievance contact: {contact.grievance_contact}</a>}
            </address>
          ) : <p>The organization name, address, and grievance email are unconfigured placeholders. Set and verify the backend contact settings before public deployment. No Data Protection Officer or legal entity is claimed here.</p>}</div>
          <h2>Information processed and purposes</h2>
          <ul>
            <li><strong>Account:</strong> username, email address, password hash, role, active state, and account creation time for registration, sign-in, account display, and authorization. The application does not store the plain-text password.</li>
            <li><strong>Posts and comments:</strong> submitted text, account reference, post relationship, language heuristic, prediction label, confidence score, probability values, explanation highlights, moderation recommendation and status, and timestamps. These are used to provide the feed, moderation, dashboards, appeals, and review history.</li>
            <li><strong>Security and administration:</strong> event type, actor role/reference, related resource reference, and timestamp for important actions. Rate limiting temporarily uses the client IP in process memory; the application does not persist that IP in its own records. The standard Uvicorn access logger may write the client IP, request method/path, protocol, and response status to server process logs; production server and proxy logging is controlled by the operator.</li>
            <li><strong>Privacy requests:</strong> request category, optional description, account reference, status, and submitted/resolved times so the request can be handled. Do not submit passwords or unrelated sensitive information.</li>
            <li><strong>Preferences:</strong> the browser stores an optional analytics preference in local storage. If you are signed in when you save it, the account records the preference category, status, policy version, and time. No optional analytics or tracking currently runs.</li>
          </ul>
          <h2>Automated moderation</h2>
          <p>Post and comment text is processed by the backend. The current code combines English keyword rules with a locally loaded English sentiment model when available, then maps its output to Hate Speech, Offensive, or Normal. Language identification is based on simple script and word-pattern rules. The generated confidence values are not calibrated evaluation probabilities. User content is not sent to a model API and is not used to train models.</p>
          <h2>Storage and access</h2>
          <p>In production the backend requires MongoDB configured by the operator. Development may use temporary in-memory storage. Authorized account holders can access their own records. Public feed viewers see approved content; authorized administrators can inspect moderation content and the minimum account/audit information needed to operate the review system. Administrators are not shown email addresses or password hashes in the user-management view.</p>
          <h2>Third parties and technical requests</h2>
          <p>The frontend calls the configured application API. It contains no analytics, advertising pixels, external embeds, or remote fonts. Model loading is configured for local files only by default. The configured database provider and deployment host necessarily process service traffic under their own arrangements; the project does not identify a specific provider here. Build-time package installation contacts package registries, but this does not send users’ moderation content.</p>
          <h2>Retention and deletion</h2>
          <p>Account and user content remain while the account is active so the account, feed, and moderation history can function. Account deletion removes the account, its posts/comments, related moderation records, consent records, and privacy requests; retained audit events are anonymized and content references removed. Audit records are automatically purged after 365 days by default. Resolved privacy requests are purged after 365 days by default; open requests remain until resolution. Optional preference history is removed when the account is deleted. The browser-local preference remains until cleared in browser settings.</p>
          <p>Audit and resolved-request periods use the 365-day defaults shown here; an operator override must also update this notice. These application rules are project retention choices, not a statement that a particular legal retention period applies in every deployment. Operators must review them against their purpose and applicable law.</p>
          <h2>Your controls</h2>
          <p>You can export your own account data, correct username or email from Account Settings after confirming your password, submit a private data request, change the optional cookie preference, or delete your account. Deletion is immediate and cannot be undone. Requests are private to your account and authorized administrators.</p>
          <h2>Security and contact</h2>
          <p>Passwords are stored as salted PBKDF2 hashes. Browser sessions use an HttpOnly cookie, SameSite restrictions, origin checks for cookie-authenticated changes, backend role checks, and rate limits. Server access logs may include client IP, request method/path, protocol, and response status; logging and retention depend on the deployment operator. HTTPS and database-at-rest protections also depend on the deployment operator and are not asserted by this application. For a privacy question or grievance, sign in and submit a request on the <button type="button" className="text-button" onClick={() => setActivePage('grievance')}>Grievance & Privacy Complaint</button> page. Policy changes should update the displayed version and contact details.</p>
          <p>This project is designed with privacy and applicable data-protection requirements in mind. It does not claim DPDP Act compliance certification.</p>
        </article>
      )}

      {pageType === 'terms' && (
        <article className="card legal-content">
          <h1>Terms & Conditions</h1>
          <p>Effective date: {updated}. OpenVibe is an academic project demonstration, not a commercial social network or service-level agreement. This notice describes the prototype’s current behavior and should be reviewed by the operator before any public launch.</p>
          <h2>1. Acceptance of terms</h2>
          <p>Creating an account requires acceptance of these Terms & Conditions. The registration form records the backend’s existing <code>terms_accepted</code> field. The Privacy Policy explains the information processed to operate the application.</p>
          <h2>2. User accounts</h2>
          <p>Provide a username, email address, and password to create an account. Keep your password private. Account holders can correct their username or email after confirming their current password, export their account data, and request account deletion using the available controls.</p>
          <h2>3. User content</h2>
          <p>You remain responsible for the text you submit and should only share content you have the right to provide. The prototype stores submitted posts and comments to deliver the feed and moderation features. Only approved posts and comments are displayed in the public feed.</p>
          <h2>4. Community guidelines</h2>
          <ul><li>Use the service lawfully and respectfully.</li><li>Do not submit threats, targeted harassment, or content intended to harm others.</li><li>Do not attempt to bypass authentication, authorization, rate limits, or moderation.</li><li>Do not share passwords or another person’s sensitive information in a post or privacy request.</li></ul>
          <h2>5. AI moderation</h2>
          <p>Posts and comments are processed by an automated moderation pipeline. Predictions may lead to publication, blocking, or a request for review. The model is a prototype; its labels and confidence values are not calibrated, may be biased or incomplete, and are not legal determinations.</p>
          <h2>6. Human review and appeals</h2>
          <p>Items routed for review can be inspected by an authorized administrator. Account holders can request a review of their own moderated posts. The prototype records that request in its moderation and audit workflow; a review outcome is not guaranteed by a particular time.</p>
          <h2>7. Intellectual property</h2>
          <p>Third-party software and image assets remain subject to their respective licenses. User content remains associated with its submitting account. See the Copyright & Image Policy for the bundled demonstration imagery.</p>
          <h2>8. Privacy</h2>
          <p>Account, content, moderation, consent, audit, and privacy-request processing is described in the <button type="button" className="text-button" onClick={() => setActivePage('privacy-policy')}>Privacy Policy</button>. Use the Privacy Center to review preferences, request an export, or delete your account.</p>
          <h2>9. Account access and restrictions</h2>
          <p>The application enforces sign-in and administrator permissions on the backend. Accounts may become unavailable if the service is changed, interrupted, or an account is deactivated by the operator. This prototype does not provide a public account-appeal workflow for access restrictions.</p>
          <h2>10. Availability and limitations</h2>
          <p>The prototype is provided for demonstration and evaluation. Features can change or be unavailable during development. Automated moderation should not be relied on for safety-critical decisions, and the project makes no uptime or commercial support commitment.</p>
          <h2>11. Liability</h2>
          <p>This project notice does not create a commercial warranty or guarantee of uninterrupted service, moderation accuracy, or suitability for a particular purpose. The operator should obtain appropriate legal review before using this prototype as a public service.</p>
          <h2>12. Changes to these terms</h2>
          <p>Terms may be revised as the project changes. The effective date above should be updated when the displayed notice changes.</p>
          <h2>13. Contact information</h2>
          {contact?.organization_name || contact?.official_email || contact?.official_address || contact?.grievance_contact ? <>
            {contact.organization_name && <p><strong>Organization:</strong> {contact.organization_name}</p>}
            <address className="contact-address">
              {contact.official_email && <a href={`mailto:${contact.official_email}`}>{contact.official_email}</a>}
              {contact.grievance_contact && <a href={`mailto:${contact.grievance_contact}`}>Grievance contact: {contact.grievance_contact}</a>}
              {contact.official_address && <span>{contact.official_address}</span>}
            </address>
          </> : <p>Operator contact details are not configured. Do not rely on a placeholder contact; privacy or moderation concerns can be submitted through the signed-in <button type="button" className="text-button" onClick={() => setActivePage('grievance')}>Privacy & Grievance request form</button>.</p>}
        </article>
      )}

      {pageType === 'cookies-policy' && (
        <article className="card legal-content">
          <h1>Cookies and Browser Storage</h1>
          <p>Effective date: {updated}.</p>
          <h2>Necessary session cookie</h2>
          <p>After sign-in, the backend sets <code>moderation_session</code>, a signed session token cookie scoped to <code>/api/v1</code>, HttpOnly, and SameSite Strict. It expires according to the configured session lifetime (120 minutes by default); Secure is enabled in production. It is required to authenticate browser requests.</p>
          <h2>Preference storage</h2>
          <p>The browser stores the optional analytics choice in local storage as <code>cookie_consent</code>. This is browser storage, not a cookie. Signed-in preference changes also create a minimal account consent record.</p>
          <h2>Optional and third-party cookies</h2>
          <p>No analytics, advertising, or third-party cookies are currently set. No analytics or tracking scripts execute. Accepting an optional preference does not activate tracking in this version. Use Manage preferences at any time to change the saved choice.</p>
          <button type="button" className="btn btn-secondary" onClick={openPreferences}>Manage preferences</button>
        </article>
      )}

      {pageType === 'refund-policy' && (
        <article className="card legal-content">
          <h1>Refund & Cancellation Policy</h1>
          <p>This project currently offers no paid products, subscriptions, or payment transactions. There are no paid purchases to cancel or refund. If payment functionality is introduced, this page must be updated to match the actual offering before it is enabled.</p>
        </article>
      )}

      {pageType === 'consent' && (
        <article className="card legal-content">
          <h1>Consent Preferences</h1>
          <p>Necessary session processing supports sign-in. Optional analytics cookies are not currently used. No user content is used for model training, so the application does not request model-training consent.</p>
          <p>Saved optional analytics preference: <strong>{analyticsAllowed ? 'enabled for future use' : 'rejected'}</strong>. Enabling it does not start analytics in this version.</p>
          {consentMessage && <p role="status">{consentMessage}</p>}
          <button type="button" className="btn btn-secondary" onClick={openPreferences}>Manage preferences</button>
        </article>
      )}

      {pageType === 'data-rights' && (
        <article className="card legal-content">
          <h1>Privacy & Data Requests</h1>
          <p>Sign in to access only your account data, submit a correction/deletion/privacy request, or review your request status. Correct username or email directly from Account Settings after confirming your password. Account deletion removes your account and related user content.</p>
          {!user && <button className="btn btn-primary" type="button" onClick={() => setActivePage('login')}>Sign in to manage requests</button>}
          {user && (
            <div className="privacy-actions">
              <button className="btn btn-secondary" type="button" onClick={exportData}>Prepare my data export</button>
              {dataExport && <button className="btn btn-primary" type="button" onClick={downloadExport}>Download my data JSON</button>}
              <button className="btn btn-danger" type="button" onClick={deleteAccount}>Delete my account and content</button>
            </div>
          )}
          {error && <p role="alert">{error}</p>}
          <h2>Submit a private request</h2>
          <RequestForm onSubmitted={loadRequests} />
          {user && <>
            <h2>Your requests</h2>
            {requests.length === 0 ? <p>No privacy requests submitted.</p> : (
              <div className="table-scroll"><table>
                <caption className="sr-only">Your privacy requests</caption>
                <thead><tr><th scope="col">Type</th><th scope="col">Status</th><th scope="col">Submitted</th><th scope="col">Resolved</th></tr></thead>
                <tbody>{requests.map((item) => <tr key={item.id}><td>{item.request_type.replaceAll('_', ' ')}</td><td>{item.status}</td><td>{item.created_at}</td><td>{item.resolved_at || '—'}</td></tr>)}</tbody>
              </table></div>
            )}
          </>}
          <p>Requests are associated with your account; no separate contact information is collected. The application does not verify an external grievance email or officer identity. Configure verified operator contact details before public deployment.</p>
        </article>
      )}

      {pageType === 'grievance' && (
        <article className="card legal-content">
          <h1>Grievance & Privacy Complaint</h1>
          <p>Submit a concern using the private account request workflow below. Include only details needed to understand the issue; do not include passwords or another person’s sensitive information. Requests are visible to authorized administrators, and you can check their status on the Privacy & Data Requests page.</p>
          <div><strong>Configured contact:</strong>{contact?.grievance_contact || contact?.official_email || contact?.official_address ? (
            <address className="contact-address">
              {contact.grievance_contact && <a href={`mailto:${contact.grievance_contact}`}>{contact.grievance_contact}</a>}
              {!contact.grievance_contact && contact.official_email && <a href={`mailto:${contact.official_email}`}>{contact.official_email}</a>}
              {contact.official_address && <span>{contact.official_address}</span>}
            </address>
          ) : <p>Contact details are not configured. The in-app form saves a private request for authorized administrators. No official or government appointment is claimed; configure and verify a working contact route before public deployment.</p>}</div>
          <RequestForm requestType="PRIVACY_CONCERN" onSubmitted={loadRequests} />
          {error && <p role="alert">{error}</p>}
          {user && <p><button type="button" className="text-button" onClick={() => setActivePage('data-rights')}>View my request status</button></p>}
        </article>
      )}

      {pageType === 'ai-transparency' && (
        <article className="card legal-content">
          <h1>AI & Moderation Transparency</h1>
          <p>The current implementation is a prototype, not a validated hate-speech model. It returns Hate Speech, Offensive, or Normal labels.</p>
          <h2>What runs</h2>
          <p>English keyword lists can directly produce Hate Speech or Offensive predictions. Otherwise, when locally cached model files are available, the backend runs <code>distilbert-base-uncased-finetuned-sst-2-english</code>, an English sentiment model, and maps positive/negative sentiment scores into the three moderation categories. Without cached weights, a keyword/heuristic fallback is used. The model is loaded locally by default; submitted content is not sent to a model provider.</p>
          <h2>Language and preprocessing</h2>
          <p>Preprocessing normalizes Unicode and whitespace, replaces URLs and mentions, unpacks hashtags, converts emoji to text, and compresses repeated characters. The language label is produced by script and word-pattern heuristics. Multilingual identification does not mean that the inference model is multilingual; language support and results outside English are not validated.</p>
          <h2>Confidence and explanations</h2>
          <p>Confidence values are derived from rule values or sentiment scores and are not calibrated or supported by a current evaluation record. Highlighted words come from keyword rules; they are not LIME or SHAP explanations and do not prove why a neural model made a decision.</p>
          <h2>Limits, review, and evaluation</h2>
          <p>Context, reclaimed language, sarcasm, dialect, and group identity can lead to false positives or false negatives. Bias and performance have not been established by a verified current evaluation. Some items can be sent to an administrator for manual review and users can appeal decisions. An AI output is an automated prediction, not an unquestionable decision or legal determination. Model evaluation data not available.</p>
        </article>
      )}

      {pageType === 'accessibility' && (
        <article className="card legal-content">
          <h1>Accessibility Statement</h1>
          <p>The interface includes semantic page landmarks, a skip link, visible keyboard focus, associated labels on core forms, status/error announcements, keyboard-operable buttons, and text tables for moderation statistics.</p>
          <p>Accessibility has not been independently audited across browsers, assistive technologies, zoom settings, and color-contrast combinations. No WCAG conformance or certification is claimed. Charts provide text labels/tables where available; if you encounter a barrier, submit a privacy concern with “Accessibility” in the description.</p>
        </article>
      )}

      {pageType === 'copyright' && (
        <article className="card legal-content">
          <h1>Copyright & Image Policy</h1>
          <p>Demonstration photos are bundled as local files in the frontend, so viewers’ browsers do not request images from an external image host. Their Unsplash source pages and download URLs are recorded in the project asset credits. The OpenVibe mark and favicon are original project-local vectors. User-submitted text remains associated with its submitting account and should only be posted when the user has the right to share it.</p>
          <p>Open-source software dependencies remain subject to their respective licenses. This notice does not assert ownership of third-party software or user content.</p>
        </article>
      )}
    </main>
  );
};
