import { useState } from 'react';
import type { FormEvent } from 'react';
import { AlertCircle, CheckCircle2, KeyRound, ShieldCheck, UserRound } from 'lucide-react';
import { api, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export function AccountPage() {
  const { user, refreshUser } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setToast('');
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    setSaving(true);
    try {
      await api.post('/auth/change-password/', {
        currentPassword,
        newPassword,
      });
      await refreshUser();
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setToast('Password changed successfully.');
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="page-eyebrow">My account</span>
          <h1 className="page-title">Account settings</h1>
          <p className="page-subtitle">
            Review your profile and update your sign-in password.
          </p>
        </div>
      </div>

      {user?.must_change_password ? (
        <div className="alert alert-warning">
          <ShieldCheck size={18} /> Your password must be changed before you continue.
        </div>
      ) : null}
      {toast ? (
        <div className="alert alert-success">
          <CheckCircle2 size={18} /> {toast}
        </div>
      ) : null}
      {error ? (
        <div className="alert alert-danger">
          <AlertCircle size={18} /> {error}
        </div>
      ) : null}

      <div className="account-grid">
        <section className="content-card">
          <div className="mini-section-head">
            <h3><UserRound size={18} /> Profile</h3>
          </div>
          <dl className="detail-list">
            <div><dt>Full name</dt><dd>{user?.full_name ?? '—'}</dd></div>
            <div><dt>Email</dt><dd>{user?.email ?? '—'}</dd></div>
            <div><dt>Employee number</dt><dd>{user?.employee_no ?? '—'}</dd></div>
            <div><dt>Role</dt><dd>{user?.role_name ?? '—'}</dd></div>
            <div><dt>Branch</dt><dd>{user?.branch_name ?? '—'}</dd></div>
            <div><dt>Phone</dt><dd>{user?.phone ?? '—'}</dd></div>
          </dl>
        </section>

        <section className="content-card">
          <div className="mini-section-head">
            <h3><KeyRound size={18} /> Change password</h3>
          </div>
          <form className="form-grid" onSubmit={submit} noValidate>
            <label className="form-field full">
              <span className="field-label">Current password</span>
              <input
                className="input"
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            <label className="form-field full">
              <span className="field-label">New password</span>
              <input
                className="input"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
                required
              />
              <span className="field-help">At least 8 characters and not a common password.</span>
            </label>
            <label className="form-field full">
              <span className="field-label">Confirm new password</span>
              <input
                className="input"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                required
              />
            </label>
            <div className="form-actions full">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Change password'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}

export default AccountPage;
