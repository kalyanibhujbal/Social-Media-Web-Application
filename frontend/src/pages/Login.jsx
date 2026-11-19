import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { OpenVibeLogo } from '../components/common/OpenVibeLogo';
import { LogIn, AlertCircle, Mail, LockKeyhole, Eye, EyeOff } from 'lucide-react';

export const Login = ({ setActivePage }) => {
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const loggedUser = await login(email, password);
      setActivePage(loggedUser.role === 'ADMIN' ? 'admin' : 'dashboard');
    } catch (err) {
      const message = err.message || '';
      setError(message === 'Failed to fetch' || message.includes('NetworkError')
        ? 'OpenVibe could not reach the server. Check that the backend is running and try again.'
        : message || 'Sign in failed. Check your details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main id="main-content" className="container page-shell narrow-page">
      <section className="card login-card">
        <header className="auth-heading">
          <OpenVibeLogo size={42} />
          <h1>Welcome back</h1>
          <p>Sign in to continue to your OpenVibe account and moderation dashboard.</p>
        </header>
        {error && <div className="notice-card notice-card-error" role="alert"><AlertCircle size={17} /> {error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="login-email" className="form-label">Email address</label>
            <div className="input-with-icon"><Mail size={16} aria-hidden="true" /><input id="login-email" type="email" className="form-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required /></div>
          </div>
          <div className="form-group">
            <label htmlFor="login-password" className="form-label">Password</label>
            <div className="input-with-icon"><LockKeyhole size={16} aria-hidden="true" /><input id="login-password" type={showPassword ? 'text' : 'password'} className="form-input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Your password" autoComplete="current-password" required /><button className="password-visibility" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>
          </div>
          <button type="submit" className="btn btn-primary auth-submit" disabled={loading}><LogIn size={16} aria-hidden="true" /> {loading ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <p className="auth-footer">New to OpenVibe? <button type="button" className="text-button" onClick={() => setActivePage('register')}>Create an account</button></p>
      </section>
    </main>
  );
};
