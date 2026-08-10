import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signInWithPhoneNumber,
  RecaptchaVerifier,
  sendPasswordResetEmail,
  signOut as firebaseSignOut,
  updateProfile,
  type ConfirmationResult,
  type User as FirebaseUser,
} from 'firebase/auth';

import {
  firebaseAuth,
  firebaseConfigured,
  googleProvider,
} from '../services/firebase';

import { platformApi } from '../services/platformApi';

type SessionUser = {
  uid: string;
  email?: string | null;
  displayName?: string | null;
  provider: string;
};

type AuthContextValue = {
  user: SessionUser | null;
  profile: any;
  loading: boolean;
  firebaseConfigured: boolean;

  loginEmail: (
    email: string,
    password: string
  ) => Promise<any>;

  registerEmail: (
    name: string,
    email: string,
    password: string
  ) => Promise<any>;

  loginGoogle: () => Promise<any>;

  sendPhoneOtp: (
    phone: string
  ) => Promise<any>;

  verifyPhoneOtp: (
    code: string
  ) => Promise<any>;

  resetPassword: (
    email: string
  ) => Promise<any>;

  demoLogin: () => Promise<any>;

  logout: () => Promise<void>;

  completeOnboarding: (
    data: any
  ) => Promise<any>;

  refreshProfile: () => Promise<any>;
};

const AuthContext =
  createContext<AuthContextValue | null>(null);

const DEMO_KEY = 'mihimura_demo_session';

let phoneConfirmation:
  ConfirmationResult | null = null;

let recaptchaVerifier:
  RecaptchaVerifier | null = null;

function mapFirebase(
  u: FirebaseUser
): SessionUser {
  return {
    uid: u.uid,
    email: u.email,
    displayName: u.displayName,
    provider:
      u.providerData[0]?.providerId ||
      'firebase',
  };
}

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {

  const [user, setUser] =
    useState<SessionUser | null>(null);

  const [profile, setProfile] =
    useState<any>(null);

  const [loading, setLoading] =
    useState(true);


  /* =====================================================
     PROFILE REFRESH
     ===================================================== */

  const refreshProfile = async () => {
    try {
      const latest =
        await platformApi.me();

      setProfile(latest);

      return latest;
    } catch (error) {
      console.error(
        '[AUTH] Could not load profile:',
        error
      );

      throw error;
    }
  };


  /* =====================================================
     FIREBASE AUTH STATE
     ===================================================== */

  useEffect(() => {

    if (
      firebaseAuth &&
      firebaseConfigured
    ) {

      const unsubscribe =
        onAuthStateChanged(
          firebaseAuth,
          async firebaseUser => {

            setLoading(true);

            try {

              if (!firebaseUser) {

                setUser(null);
                setProfile(null);

                setLoading(false);

                return;
              }

              const sessionUser =
                mapFirebase(firebaseUser);

              setUser(sessionUser);

              /*
               * Force Firebase to provide a valid
               * ID token before requesting the
               * backend profile.
               */
              await firebaseUser.getIdToken();

              console.log(
                '[AUTH] Firebase user ready:',
                firebaseUser.uid
              );

              const backendProfile =
                await platformApi.me();

              console.log(
                '[AUTH] Backend profile:',
                backendProfile
              );

              setProfile(
                backendProfile
              );

            } catch (error) {

              console.error(
                '[AUTH] Profile initialization failed:',
                error
              );

              setProfile(null);

            } finally {

              setLoading(false);

            }
          }
        );

      return unsubscribe;
    }


    /* ===================================================
       DEMO MODE
       =================================================== */

    const demo =
      localStorage.getItem(
        DEMO_KEY
      );

    if (demo) {

      try {

        const d =
          JSON.parse(demo);

        setUser(d);

        const p =
          localStorage.getItem(
            `mihimura_profile_${d.uid}`
          );

        setProfile(
          p
            ? JSON.parse(p)
            : {
                uid: d.uid,
                onboarding_complete: 1,
                name: 'Demo Farmer',
                role: 'farmer',
                language: 'English',
                district: 'Ampara',
              }
        );

      } catch {

        localStorage.removeItem(
          DEMO_KEY
        );
      }
    }

    setLoading(false);

  }, []);


  /* =====================================================
     EMAIL LOGIN
     ===================================================== */

  const loginEmail =
    async (
      email: string,
      password: string
    ) => {

      if (!firebaseAuth) {
        throw new Error(
          'Firebase is not configured.'
        );
      }

      return signInWithEmailAndPassword(
        firebaseAuth,
        email,
        password
      );
    };


  /* =====================================================
     EMAIL REGISTRATION
     ===================================================== */

  const registerEmail =
    async (
      name: string,
      email: string,
      password: string
    ) => {

      if (!firebaseAuth) {
        throw new Error(
          'Firebase is not configured.'
        );
      }

      const cred =
        await createUserWithEmailAndPassword(
          firebaseAuth,
          email,
          password
        );

      await updateProfile(
        cred.user,
        {
          displayName: name,
        }
      );

      /*
       * Do NOT manually call /users/me here.
       * onAuthStateChanged will handle it.
       */
      return cred;
    };


  /* =====================================================
     GOOGLE LOGIN
     ===================================================== */

  const loginGoogle =
    async () => {

      if (!firebaseAuth) {
        throw new Error(
          'Firebase is not configured.'
        );
      }

      /*
       * Do not manually set user/profile here.
       * Firebase auth observer is the single
       * source of truth.
       */
      return signInWithPopup(
        firebaseAuth,
        googleProvider
      );
    };


  /* =====================================================
     PHONE AUTH
     ===================================================== */

  const sendPhoneOtp =
    async (
      phone: string
    ) => {

      if (!firebaseAuth) {
        throw new Error(
          'Firebase is not configured.'
        );
      }

      try {

        if (!recaptchaVerifier) {

          recaptchaVerifier =
            new RecaptchaVerifier(
              firebaseAuth,
              'mihimura-recaptcha',
              {
                size: 'invisible',
              }
            );
        }

        phoneConfirmation =
          await signInWithPhoneNumber(
            firebaseAuth,
            phone,
            recaptchaVerifier
          );

      } catch (error) {

        recaptchaVerifier?.clear();

        recaptchaVerifier =
          null;

        throw error;
      }
    };


  const verifyPhoneOtp =
    async (
      code: string
    ) => {

      if (!phoneConfirmation) {
        throw new Error(
          'Request a verification code first.'
        );
      }

      await phoneConfirmation.confirm(
        code
      );

      phoneConfirmation =
        null;

      recaptchaVerifier?.clear();

      recaptchaVerifier =
        null;
    };


  /* =====================================================
     PASSWORD RESET
     ===================================================== */

  const resetPassword =
    async (
      email: string
    ) => {

      if (!firebaseAuth) {
        throw new Error(
          'Firebase is not configured.'
        );
      }

      if (!email) {
        throw new Error(
          'Enter your email address first.'
        );
      }

      await sendPasswordResetEmail(
        firebaseAuth,
        email
      );
    };


  /* =====================================================
     DEMO LOGIN
     ===================================================== */

  const demoLogin =
    async () => {

      const d = {
        uid: 'demo_farmer_001',
        email: 'demo@mihimura.lk',
        displayName: 'Demo Farmer',
        provider: 'demo',
      };

      localStorage.setItem(
        DEMO_KEY,
        JSON.stringify(d)
      );

      setUser(d);

      try {

        const backendProfile =
          await platformApi.me();

        setProfile(
          backendProfile
        );

      } catch {

        setProfile({
          uid: d.uid,
          onboarding_complete: 1,
          name: 'Demo Farmer',
          role: 'farmer',
          language: 'English',
          district: 'Ampara',
        });
      }
    };


  /* =====================================================
     LOGOUT
     ===================================================== */

  const logout =
    async () => {

      if (
        firebaseAuth?.currentUser
      ) {

        await firebaseSignOut(
          firebaseAuth
        );
      }

      localStorage.removeItem(
        DEMO_KEY
      );

      setUser(null);
      setProfile(null);
    };


  /* =====================================================
     ONBOARDING
     ===================================================== */

  const completeOnboarding =
    async (
      data: any
    ) => {

      console.log(
        '[AUTH] Saving onboarding profile...'
      );

      /*
       * IMPORTANT:
       * Do NOT silently fall back to
       * localStorage for real users.
       *
       * Database persistence must succeed.
       */
      const saved =
        await platformApi.saveProfile({
          ...data,
          onboarding_complete: true,
        });

      console.log(
        '[AUTH] Onboarding saved:',
        saved
      );

      setProfile(saved);

      return saved;
    };


  /* =====================================================
     ACCESSIBILITY
     ===================================================== */

  useEffect(() => {

    let accessibility: any =
      {};

    try {

      accessibility =
        typeof profile
          ?.accessibility_json ===
        'string'
          ? JSON.parse(
              profile
                .accessibility_json
            )
          : (
              profile
                ?.accessibility_json ||
              {}
            );

    } catch {

      accessibility = {};
    }

    document.documentElement
      .classList.toggle(
        'large-text',
        Boolean(
          accessibility.largeText
        )
      );

    document.documentElement
      .classList.toggle(
        'high-contrast',
        Boolean(
          accessibility
            .highContrast
        )
      );

  }, [profile]);


  const value =
    useMemo(
      () => ({
        user,
        profile,
        loading,
        firebaseConfigured,
        loginEmail,
        registerEmail,
        loginGoogle,
        sendPhoneOtp,
        verifyPhoneOtp,
        resetPassword,
        demoLogin,
        logout,
        completeOnboarding,
        refreshProfile,
      }),
      [
        user,
        profile,
        loading,
        firebaseConfigured,
      ]
    );


  return (
    <AuthContext.Provider
      value={value}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth() {

  const ctx =
    useContext(AuthContext);

  if (!ctx) {
    throw new Error(
      'useAuth must be used inside AuthProvider'
    );
  }

  return ctx;
}