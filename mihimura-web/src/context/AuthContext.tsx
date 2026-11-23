import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';

import { platformApi } from '../services/platformApi';
import { supabase, supabaseConfigured } from '../services/supabase';

type SessionUser = {
  uid: string;
  email?: string | null;
  displayName?: string | null;
  provider: string;
  requestedRole?: string | null;
};

type AuthContextValue = {
  user: SessionUser | null;
  profile: any;
  loading: boolean;
  profileError: string;
  supabaseConfigured: boolean;
  loginEmail: (email: string, password: string) => Promise<any>;
  registerEmail: (name: string, email: string, password: string, role?: string) => Promise<any>;
  loginGoogle: () => Promise<any>;
  sendPhoneOtp: (phone: string) => Promise<any>;
  verifyPhoneOtp: (code: string) => Promise<any>;
  resetPassword: (email: string) => Promise<any>;
  updatePassword: (password: string) => Promise<any>;
  demoLogin: () => Promise<any>;
  logout: () => Promise<void>;
  completeOnboarding: (data: any) => Promise<any>;
  refreshProfile: () => Promise<any>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const DEMO_KEY = 'mihimura_demo_session';
const DEMO_UID = '00000000-0000-0000-0000-000000000001';
let pendingPhone = '';

function mapUser(u: User): SessionUser {
  const metadata = u.user_metadata || {};
  return {
    uid: u.id,
    email: u.email,
    displayName: metadata.full_name || metadata.name || u.email?.split('@')[0] || 'Farmer',
    provider: u.app_metadata?.provider || 'supabase',
    requestedRole: metadata.requested_role || null,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const [profileError, setProfileError] = useState('');
  const sessionRevision = useRef(0);
  const currentUid = useRef<string | null>(null);

  const refreshProfile = async () => {
    const revision = sessionRevision.current;
    try {
      const latest = await platformApi.me();
      if (revision === sessionRevision.current) {
        setProfile(latest);
        setProfileError('');
      }
      return latest;
    } catch (error) {
      if (revision === sessionRevision.current) {
        setProfileError(error instanceof Error ? error.message : 'Your profile could not be loaded.');
      }
      throw error;
    }
  };

  useEffect(() => {
    let alive = true;

    const applySession = async (session: Session | null) => {
      if (!alive) return;
      const revision = ++sessionRevision.current;
      let identity = session?.user ? mapUser(session.user) : null;
      if (identity) {
        localStorage.removeItem(DEMO_KEY);
      } else if (localStorage.getItem(DEMO_KEY)) {
        try {
          const demo = JSON.parse(localStorage.getItem(DEMO_KEY) || '{}');
          if (demo.uid === DEMO_UID && demo.provider === 'demo') identity = demo;
        } catch {
          localStorage.removeItem(DEMO_KEY);
        }
      }
      currentUid.current = identity?.uid ?? null;
      setUser(identity);
      setProfile(null);
      setProfileError('');
      setLoading(Boolean(identity));
      try {
        if (identity) await refreshProfile();
      } catch {
        // The sign-in screen offers a profile retry.
      } finally {
        if (alive && revision === sessionRevision.current) setLoading(false);
      }
    };

    const subscription = supabase?.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') sessionStorage.setItem('mihimura_password_recovery', '1');
      // Schedule outside the auth callback because profile requests read the Supabase session.
      window.setTimeout(() => {
        if (event !== 'PASSWORD_RECOVERY' && session?.user.id === currentUid.current) return;
        void applySession(session);
      }, 0);
    });
    if (!supabase) void applySession(null);

    return () => {
      alive = false;
      sessionRevision.current++;
      subscription?.data.subscription.unsubscribe();
    };
  }, []);

  const requireSupabase = () => {
    if (!supabase || !supabaseConfigured)
      throw new Error('Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.');
    return supabase;
  };

  const loginEmail = async (email: string, password: string) => {
    const client = requireSupabase();
    const { data, error } = await client.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  };

  const registerEmail = async (name: string, email: string, password: string, role = 'farmer') => {
    const client = requireSupabase();
    const { data, error } = await client.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: name, name, requested_role: role },
        emailRedirectTo: `${window.location.origin}/?flow=signup#/auth`,
      },
    });
    if (error) throw error;
    return { ...data, needsEmailConfirmation: Boolean(data.user && !data.session) };
  };

  const loginGoogle = async () => {
    const client = requireSupabase();
    const { data, error } = await client.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/?flow=oauth#/auth` },
    });
    if (error) throw error;
    return data;
  };

  const sendPhoneOtp = async (phone: string) => {
    const client = requireSupabase();
    pendingPhone = phone;
    const { data, error } = await client.auth.signInWithOtp({ phone });
    if (error) throw error;
    return data;
  };

  const verifyPhoneOtp = async (code: string) => {
    const client = requireSupabase();
    if (!pendingPhone) throw new Error('Request a verification code first.');
    const { data, error } = await client.auth.verifyOtp({ phone: pendingPhone, token: code, type: 'sms' });
    if (error) throw error;
    pendingPhone = '';
    return data;
  };

  const resetPassword = async (email: string) => {
    const client = requireSupabase();
    if (!email) throw new Error('Enter your email address first.');
    const { data, error } = await client.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/?flow=recovery#/auth?mode=recovery`,
    });
    if (error) throw error;
    return data;
  };

  const updatePassword = async (password: string) => {
    const client = requireSupabase();
    if (password.length < 6) throw new Error('Use at least 6 characters.');
    const { data, error } = await client.auth.updateUser({ password });
    if (error) throw error;
    return data;
  };

  const demoLogin = async () => {
    if (supabase) await supabase.auth.signOut().catch(() => undefined);
    const demo: SessionUser = {
      uid: DEMO_UID,
      email: 'demo@mihimura.lk',
      displayName: 'Demo Farmer',
      provider: 'demo',
    };
    localStorage.setItem(DEMO_KEY, JSON.stringify(demo));
    try {
      const latest = await platformApi.me();
      currentUid.current = demo.uid;
      setUser(demo);
      setProfile(latest);
      setProfileError('');
      return latest;
    } catch (error) {
      localStorage.removeItem(DEMO_KEY);
      throw error;
    }
  };

  const logout = async () => {
    localStorage.removeItem(DEMO_KEY);
    sessionStorage.removeItem('mihimura_pending_identity');
    if (supabase && currentUid.current !== DEMO_UID) {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    }
    sessionRevision.current++;
    currentUid.current = null;
    setLoading(false);
    setProfileError('');
    setUser(null);
    setProfile(null);
  };

  const completeOnboarding = async (data: any) => {
    const saved = await platformApi.saveProfile({ ...data, onboarding_complete: true });
    setProfile(saved);
    return saved;
  };

  useEffect(() => {
    let accessibility: any = {};
    try {
      accessibility =
        typeof profile?.accessibility_json === 'string'
          ? JSON.parse(profile.accessibility_json)
          : profile?.accessibility_json || {};
    } catch {
      accessibility = {};
    }
    document.documentElement.classList.toggle('large-text', Boolean(accessibility.largeText));
    document.documentElement.classList.toggle('high-contrast', Boolean(accessibility.highContrast));
  }, [profile]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      profile,
      loading,
      profileError,
      supabaseConfigured,
      loginEmail,
      registerEmail,
      loginGoogle,
      sendPhoneOtp,
      verifyPhoneOtp,
      resetPassword,
      updatePassword,
      demoLogin,
      logout,
      completeOnboarding,
      refreshProfile,
    }),
    [user, profile, loading, profileError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
