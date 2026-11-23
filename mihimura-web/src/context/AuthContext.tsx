import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';

import { oauthRedirectUrl } from '../services/authRedirect';
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
  authError: string;
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
const PHONE_KEY = 'mihimura_pending_phone';

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
  const [authError, setAuthError] = useState('');

  const refreshProfile = async () => {
    const latest = await platformApi.me();
    setAuthError('');
    setProfile(latest);
    return latest;
  };

  const applySession = async (session: Session | null) => {
    if (!session?.user) {
      const rawDemo = localStorage.getItem(DEMO_KEY);
      if (rawDemo) {
        try {
          const demo = JSON.parse(rawDemo);
          setUser(demo);
          const latest = await platformApi.me();
          setAuthError('');
          setProfile(latest);
          return;
        } catch (error) {
          console.error('[AUTH] Demo session failed:', error);
          localStorage.removeItem(DEMO_KEY);
          setAuthError(error instanceof Error ? error.message : 'Demo sign-in could not reach the API.');
        }
      }
      setUser(null);
      setProfile(null);
      return;
    }

    localStorage.removeItem(DEMO_KEY);
    setUser(mapUser(session.user));
    try {
      const latest = await platformApi.me();
      setAuthError('');
      setProfile(latest);
    } catch (error) {
      console.error('[AUTH] Supabase session is valid but backend profile loading failed:', error);
      setProfile(null);
      setAuthError(
        error instanceof Error
          ? error.message
          : 'Your Google session is valid, but the MihiMura profile could not be loaded.',
      );
    }
  };

  useEffect(() => {
    let alive = true;

    const initialize = async () => {
      setLoading(true);
      try {
        if (supabase && supabaseConfigured) {
          const { data, error } = await supabase.auth.getSession();
          if (error) throw error;
          if (alive) await applySession(data.session);
        } else if (alive) {
          await applySession(null);
        }
      } catch (error) {
        console.error('[AUTH] Initialization failed:', error);
      } finally {
        if (alive) setLoading(false);
      }
    };

    void initialize();

    if (!supabase)
      return () => {
        alive = false;
      };
    const { data: subscription } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') sessionStorage.setItem('mihimura_password_recovery', '1');
      // getSession() already applied the first session. Refresh must not flash the boot screen.
      if (event === 'INITIAL_SESSION' || event === 'TOKEN_REFRESHED') return;
      window.setTimeout(() => {
        if (!alive) return;
        setLoading(true);
        void applySession(session)
          .catch((error) => console.error('[AUTH] Session update failed:', error))
          .finally(() => alive && setLoading(false));
      }, 0);
    });

    return () => {
      alive = false;
      subscription.subscription.unsubscribe();
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
        emailRedirectTo: oauthRedirectUrl(window.location.origin),
      },
    });
    if (error) throw error;
    return { ...data, needsEmailConfirmation: Boolean(data.user && !data.session) };
  };

  const loginGoogle = async () => {
    const client = requireSupabase();
    sessionStorage.setItem('mihimura_oauth_pending', '1');
    const { data, error } = await client.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: oauthRedirectUrl(window.location.origin) },
    });
    if (error) sessionStorage.removeItem('mihimura_oauth_pending');
    if (error) throw error;
    return data;
  };

  const sendPhoneOtp = async (phone: string) => {
    const client = requireSupabase();
    sessionStorage.setItem(PHONE_KEY, phone);
    const { data, error } = await client.auth.signInWithOtp({ phone });
    if (error) throw error;
    return data;
  };

  const verifyPhoneOtp = async (code: string) => {
    const client = requireSupabase();
    const phone = sessionStorage.getItem(PHONE_KEY) || '';
    if (!phone) throw new Error('Request a verification code first.');
    const { data, error } = await client.auth.verifyOtp({ phone, token: code, type: 'sms' });
    if (error) throw error;
    sessionStorage.removeItem(PHONE_KEY);
    return data;
  };

  const resetPassword = async (email: string) => {
    const client = requireSupabase();
    if (!email) throw new Error('Enter your email address first.');
    const { data, error } = await client.auth.resetPasswordForEmail(email, {
      redirectTo: oauthRedirectUrl(window.location.origin),
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
    setUser(demo);
    setAuthError('');
    const latest = await platformApi.me();
    setProfile(latest);
    return latest;
  };

  const logout = async () => {
    if (supabase) await supabase.auth.signOut().catch(() => undefined);
    localStorage.removeItem(DEMO_KEY);
    setUser(null);
    setProfile(null);
    setAuthError('');
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
      authError,
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
    [user, profile, loading, authError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
