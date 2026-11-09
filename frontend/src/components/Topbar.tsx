import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronDown, LogOut, Menu, Search, UserRound } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

interface TopbarProps {
  onMenu: () => void;
}

export function Topbar({ onMenu }: TopbarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') ?? '');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (location.pathname === '/search') {
      setQuery(searchParams.get('q') ?? '');
    }
  }, [location.pathname, searchParams]);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 2) return;
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
  };

  const initials = `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`;

  return (
    <header className="topbar">
      <button
        type="button"
        className="menu-toggle"
        onClick={onMenu}
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>

      <form className="topbar-search" onSubmit={submit} role="search">
        <Search size={17} />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search clients, policies, claims, vehicles…"
          aria-label="Global search"
        />
      </form>

      <div className="topbar-right">
        <div className="user-menu" ref={menuRef}>
          <button
            type="button"
            className="user-chip"
            onClick={() => setMenuOpen((current) => !current)}
            aria-expanded={menuOpen}
          >
            <span className="avatar">{initials || 'IB'}</span>
            <span className="user-chip-copy">
              <strong>{user?.full_name ?? 'User'}</strong>
              <small>{user?.role_name ?? 'Member'}</small>
            </span>
            <ChevronDown size={16} />
          </button>
          {menuOpen ? (
            <div className="user-dropdown">
              <div className="dropdown-head">
                <strong>{user?.full_name}</strong>
                <span>{user?.email}</span>
                <span className="badge badge-info">{user?.branch_name ?? 'Head office'}</span>
              </div>
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setMenuOpen(false);
                  navigate('/account');
                }}
              >
                <UserRound size={16} /> Account settings
              </button>
              <button
                type="button"
                className="dropdown-item"
                onClick={async () => {
                  setMenuOpen(false);
                  await logout();
                  navigate('/login', { replace: true });
                }}
              >
                <LogOut size={16} /> Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export default Topbar;
