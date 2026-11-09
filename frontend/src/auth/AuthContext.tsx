import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api, REFRESH_KEY, TOKEN_KEY } from '../api/client';
import type { User } from '../types';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  can: (code: string) => boolean;
  canModule: (module: string, action?: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const response = await api.get('/auth/me/');
    setUser(response.data.data as User);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const response = await api.get('/auth/me/');
        if (!cancelled) setUser(response.data.data as User);
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [token, clearSession]);

  useEffect(() => {
    const handler = () => clearSession();
    window.addEventListener('ibms:unauthorized', handler);
    return () => window.removeEventListener('ibms:unauthorized', handler);
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.post('/auth/login/', { email, password });
    const payload = response.data.data;
    localStorage.setItem(TOKEN_KEY, payload.token);
    localStorage.setItem(REFRESH_KEY, payload.refresh);
    setToken(payload.token);
    setUser(payload.user as User);
  }, []);

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem(REFRESH_KEY);
    try {
      await api.post('/auth/logout/', { refresh });
    } catch {
      // ignore network errors during logout
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const can = useCallback(
    (code: string) => {
      if (!user) return false;
      if (user.role_code === 'ADMIN') return true;
      return user.permissions?.includes(code) ?? false;
    },
    [user],
  );

  const canModule = useCallback(
    (module: string, action = 'view') => can(`${module}:${action}`),
    [can],
  );

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      login,
      logout,
      refreshUser,
      can,
      canModule,
    }),
    [user, token, loading, login, logout, refreshUser, can, canModule],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
