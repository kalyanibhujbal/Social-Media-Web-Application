import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { OpenVibeLogo } from '../components/common/OpenVibeLogo';
import { UserPlus, AlertCircle, UserRound, Mail, LockKeyhole, Eye, EyeOff, User } from 'lucide-react';

export const Register = ({ setActivePage }) => {
  const { register } = useContext(AuthContext);
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!termsAccepted) {
      setError('Please agree to the Terms & Conditions and acknowledge the Privacy Policy to create an account.');
      return;
    }
    if (password !== confirmPassword) {
      setError('The passwords do not match.');
      return;
    }
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError('Use at least 8 characters, including a letter and a number.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await register(username, email, password, termsAccepted, fullName);
      setActivePage('login');
    } catch (err) {
      setError(err.message || 'Account creation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main id="main-content" className="container page-shell narrow-page">
      <section className="card register-card">
        <header className="auth-heading">
          <OpenVibeLogo size={42} />
          <h1>Join OpenVibe</h1>
          <p>Build your profile and take part in a more thoughtful community.</p>
        </header>
        {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} /> {error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="reg-full-name" className="form-label">Full name</label>
            <div className="input-with-icon"><User size={16} aria-hidden="true" /><input id="reg-full-name" type="text" className="form-input" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Your name" autoComplete="name" required minLength={1} maxLength={80} /></div>
          </div>
          <div className="form-group">
            <label htmlFor="reg-username" className="form-label">Username</label>
            <div className="input-with-icon"><UserRound size={16} aria-hidden="true" /><input id="reg-username" type="text" className="form-input" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Choose a username" autoComplete="username" required minLength={3} maxLength={30} /></div>
          </div>
          <div className="form-group">
            <label htmlFor="reg-email" className="form-label">Email address</label>
            <div className="input-with-icon"><Mail size={16} aria-hidden="true" /><input id="reg-email" type="email" className="form-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required /></div>
          </div>
          <div className="form-group">
            <label htmlFor="reg-password" className="form-label">Password <span className="muted-note">(8+ characters, include a letter and number)</span></label>
            <div className="input-with-icon"><LockKeyhole size={16} aria-hidden="true" /><input id="reg-password" type={showPassword ? 'text' : 'password'} className="form-input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Create a password" autoComplete="new-password" required minLength={8} maxLength={100} /><button className="password-visibility" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>
          </div>
          <div className="form-group">
            <label htmlFor="reg-confirm-password" className="form-label">Confirm password</label>
            <div className="input-with-icon"><LockKeyhole size={16} aria-hidden="true" /><input id="reg-confirm-password" type={showPassword ? 'text' : 'password'} className="form-input" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter your password again" autoComplete="new-password" required minLength={8} maxLength={100} /></div>
          </div>
          <div className="form-group consent-form-card">
            <label htmlFor="terms-checkbox">
              <input type="checkbox" id="terms-checkbox" checked={termsAccepted} onChange={(event) => setTermsAccepted(event.target.checked)} required />
              <span>I agree to the <a href="#terms" onClick={(event) => { event.preventDefault(); setActivePage('terms'); }}>Terms & Conditions</a> and acknowledge the <a href="#privacy" onClick={(event) => { event.preventDefault(); setActivePage('privacy-policy'); }}>Privacy Policy</a>. This is required to create an account.</span>
            </label>
          </div>
          <button type="submit" className="btn btn-primary auth-submit" disabled={loading || !termsAccepted}><UserPlus size={16} aria-hidden="true" /> {loading ? 'Creating account…' : 'Create account'}</button>
        </form>
        <p className="auth-footer">Already have an account? <button type="button" className="text-button" onClick={() => setActivePage('login')}>Sign in</button></p>
      </section>
    </main>
  );
};
