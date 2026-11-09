import { NavLink } from 'react-router-dom';
import { ShieldCheck, X } from 'lucide-react';
import { navigation } from '../config/navigation';
import { useAuth } from '../auth/AuthContext';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { can, user } = useAuth();

  return (
    <aside className={`sidebar${open ? ' sidebar-open' : ''}`}>
      <div className="sidebar-brand">
        <div className="brand-mark">
          <ShieldCheck size={22} />
        </div>
        <div className="brand-copy">
          <strong>IBMS</strong>
          <span>Brokerage Management</span>
        </div>
        <button
          type="button"
          className="sidebar-close"
          onClick={onClose}
          aria-label="Close navigation"
        >
          <X size={18} />
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {navigation.map((group) => {
          const items = group.items.filter(
            (item) => !item.permission || can(item.permission),
          );
          if (items.length === 0) return null;
          return (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `nav-link${isActive ? ' nav-link-active' : ''}`
                    }
                    onClick={onClose}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <span className="avatar avatar-sm">
            {(user?.first_name?.[0] ?? '') + (user?.last_name?.[0] ?? '')}
          </span>
          <div>
            <strong>{user?.full_name ?? 'Signed out'}</strong>
            <span>{user?.role_name ?? 'No role'}</span>
          </div>
        </div>
        <p className="sidebar-version">IBMS v1.0 · Secure workspace</p>
      </div>
    </aside>
  );
}
