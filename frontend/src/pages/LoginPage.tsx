import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { getErrorMessage } from '../api/client';

interface LocationState {
  from?: string;
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(email.trim(), password);
      const state = location.state as LocationState | null;
      navigate(state?.from ?? '/dashboard', { replace: true });
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-brand">
        <Link to="/" className="login-logo" aria-label="Back to the IBMS home page">
          <span className="brand-mark brand-mark-light">
            <ShieldCheck size={24} />
          </span>
          <span>IBMS</span>
        </Link>

        <div className="login-brand-copy">
          <span className="login-eyebrow">Insurance Brokerage Management System</span>
          <h1>One workspace for every policy, premium and claim.</h1>
          <p>
            Manage clients, quotations, policies, collections and claims with a
            complete audit trail and role-based access across your branches.
          </p>
          <ul className="login-features">
            <li>
              <span>01</span> Client &amp; risk management with KYC tracking
            </li>
            <li>
              <span>02</span> Quotation-to-policy workflow and renewals
            </li>
            <li>
              <span>03</span> Premium collections, commissions and remittances
            </li>
            <li>
              <span>04</span> Claims, approvals and management reporting
            </li>
          </ul>
        </div>

        <p className="login-footnote">
          Secure by design · Role-based permissions · Full audit trail
        </p>
      </section>

      <section className="login-panel">
        <div className="login-card">
          <span className="page-eyebrow">Welcome back</span>
          <h2 className="login-title">Sign in to your workspace</h2>
          <p className="login-subtitle">
            Use your company email address and password to continue.
          </p>

          {error ? (
            <div className="alert alert-danger">
              <AlertCircle size={18} /> {error}
            </div>
          ) : null}

          <form onSubmit={submit} className="login-form" noValidate>
            <div className="form-field">
              <label className="field-label" htmlFor="login-email">
                Email address
              </label>
              <div className="input-icon">
                <Mail size={17} />
                <input
                  id="login-email"
                  className="input"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  autoFocus
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="login-password">
                Password
              </label>
              <div className="input-icon">
                <LockKeyhole size={17} />
                <input
                  id="login-password"
                  className="input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button
                  type="button"
                  className="input-icon-button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} />
            </button>
          </form>

          <p className="login-hint">
            Authorized users only. Contact your system administrator if you need access.
          </p>
        </div>
      </section>
    </div>
  );
}

export default LoginPage;
