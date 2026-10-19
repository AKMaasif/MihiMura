import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  Fingerprint,
  Globe2,
  Leaf,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sprout,
  UserRound,
} from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../common/UI';

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-1.99 3.02v2.54h3.22c1.88-1.73 2.99-4.28 2.99-7.41Z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.7 0 4.96-.89 6.61-2.36l-3.22-2.54c-.89.6-2.03.96-3.39.96-2.6 0-4.81-1.76-5.6-4.13H3.07v2.61A10 10 0 0 0 12 22Z"
      />
      <path
        fill="#FBBC05"
        d="M6.4 13.93A6.02 6.02 0 0 1 6.08 12c0-.67.11-1.32.32-1.93V7.46H3.07A10 10 0 0 0 2 12c0 1.61.38 3.13 1.07 4.54l3.33-2.61Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.94c1.47 0 2.79.51 3.83 1.5l2.87-2.87C16.96 2.95 14.7 2 12 2a10 10 0 0 0-8.93 5.46l3.33 2.61C7.19 7.7 9.4 5.94 12 5.94Z"
      />
    </svg>
  );
}

const steps = ['Identity', 'Contact', 'Security', 'Ready'];
const demoEnabled = import.meta.env.VITE_DEMO_AUTH !== 'false';
// Guided email/phone login and registration are intentionally disabled for now.
// Set VITE_GUIDED_AUTH_ENABLED=true later when those flows are ready to reopen.
const guidedAccessEnabled = import.meta.env.VITE_GUIDED_AUTH_ENABLED === 'true';
type Mode = 'choice' | 'login' | 'register' | 'recovery';

export default function AuthExperience() {
  const {
    user,
    profile,
    loginEmail,
    registerEmail,
    loginGoogle,
    sendPhoneOtp,
    verifyPhoneOtp,
    resetPassword,
    updatePassword,
    demoLogin,
    supabaseConfigured,
  } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();

  const requestedMode = new URLSearchParams(loc.search).get('mode');
  const initialMode: Mode =
    guidedAccessEnabled && requestedMode === 'register'
      ? 'register'
      : requestedMode === 'recovery' || sessionStorage.getItem('mihimura_password_recovery') === '1'
        ? 'recovery'
        : 'choice';

  const [mode, setMode] = useState<Mode>(initialMode);
  const [step, setStep] = useState(0);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [data, setData] = useState({ name: '', email: '', password: '', role: 'farmer' });
  const [newPassword, setNewPassword] = useState('');
  const [loginMethod, setLoginMethod] = useState<'email' | 'phone'>('email');
  const [phone, setPhone] = useState('+94');
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  useEffect(() => {
    if (!user || mode === 'recovery') return;
    if (profile?.onboarding_complete) nav('/app/dashboard', { replace: true });
    else if (profile !== undefined && profile !== null) nav('/onboarding', { replace: true });
  }, [user, profile, mode, nav]);

  useEffect(() => {
    if (sessionStorage.getItem('mihimura_password_recovery') === '1') setMode('recovery');
  }, [loc.key]);

  useEffect(() => {
    // Defensive guard: guided access must remain unavailable even if a stale UI state
    // or a manually edited URL attempts to open login/register directly.
    if (!guidedAccessEnabled && (mode === 'login' || mode === 'register')) setMode('choice');
  }, [mode]);

  const canNext = useMemo(
    () =>
      step === 0
        ? Boolean(data.name && data.role)
        : step === 1
          ? /^[^@]+@[^@]+\.[^@]+$/.test(data.email)
          : step === 2
            ? data.password.length >= 6
            : true,
    [step, data],
  );

  const google = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      sessionStorage.setItem(
        'mihimura_pending_identity',
        JSON.stringify({ name: data.name || undefined, role: mode === 'register' ? data.role : 'farmer' }),
      );
      await loginGoogle();
      // Supabase OAuth performs a browser redirect. AuthProvider completes routing when it returns.
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const emailLogin = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      await loginEmail(data.email, data.password);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const phoneLogin = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      if (!otpSent) {
        await sendPhoneOtp(phone);
        setOtpSent(true);
        setInfo('Verification code sent. Enter the code from SMS.');
      } else {
        await verifyPhoneOtp(otp);
        setInfo('Phone verified. Opening your MihiMura profile…');
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const forgot = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      await resetPassword(data.email);
      setInfo('Password-reset email sent. Open the secure link in that email to choose a new password.');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const create = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      sessionStorage.setItem(
        'mihimura_pending_identity',
        JSON.stringify({ name: data.name, email: data.email, role: data.role }),
      );
      const result = await registerEmail(data.name, data.email, data.password, data.role);
      if (result?.needsEmailConfirmation) {
        setInfo('Account created. Check your email and confirm the address, then sign in.');
        setMode('login');
        return;
      }
      // If email confirmation is disabled, AuthProvider will route the new authenticated user to onboarding.
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const finishRecovery = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      await updatePassword(newPassword);
      sessionStorage.removeItem('mihimura_password_recovery');
      setInfo('Password updated successfully.');
      if (profile?.onboarding_complete) nav('/app/dashboard', { replace: true });
      else nav('/onboarding', { replace: true });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const demo = async () => {
    setBusy(true);
    try {
      await demoLogin();
      nav('/app/dashboard');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-experience">
      <div className="auth-scene">
        <div className="auth-grid-lines" />
        <div className="auth-sun" />
        <div className="auth-land land-a" />
        <div className="auth-land land-b" />
        <div className="auth-brand">
          <span>
            <Leaf />
          </span>
          <div>
            <b>MihiMura</b>
            <small>මිහිමුර</small>
          </div>
        </div>
        <div className="auth-story">
          <span>Your field companion is ready</span>
          <h1>
            One identity.
            <br />
            Every field remembered.
          </h1>
          <p>
            Sign in to a living farm digital twin that combines weather, crop evidence, tasks and safe AI
            coordination.
          </p>
          <div className="auth-agent-pills">
            <em>
              <Sprout /> Farm memory
            </em>
            <em>
              <Globe2 /> Climate context
            </em>
            <em>
              <ShieldCheck /> Safety gates
            </em>
          </div>
        </div>
        <div className="auth-signal">
          <i />
          <span>24/7</span>
          <b>Stay Updated</b>
        </div>
      </div>
      <div className="auth-panel">
        <button className="auth-back-home" onClick={() => nav('/welcome')}>
          <ArrowLeft /> Back to MihiMura
        </button>
        {mode === 'choice' && (
          <div className="auth-choice">
            <div className="auth-mini-brand">
              <Leaf />
            </div>
            <span className="auth-kicker">Secure field access</span>
            <h2>How would you like to continue?</h2>
            <p>Use your Google identity, or enter the guided MihiMura access journey.</p>
            <button className="google-btn" disabled={busy || !supabaseConfigured} onClick={google}>
              <span className="google-g">
                <GoogleIcon />
              </span>
              <b>Continue with Google</b>
              <small>{supabaseConfigured ? 'Secure Supabase sign-in' : 'Requires Supabase setup'}</small>
              <ArrowRight />
            </button>
            <div className="auth-divider">
              <span />
              or
              <span />
            </div>
            <div className="auth-paths">
              <button
                disabled={!guidedAccessEnabled}
                aria-disabled={!guidedAccessEnabled}
                title={!guidedAccessEnabled ? 'This access option is coming soon' : undefined}
                onClick={() => setMode('login')}
              >
                <span>
                  <Fingerprint />
                </span>
                <div>
                  <b>I already have a field profile</b>
                  <small>Continue to my digital twins</small>
                </div>
                <ArrowRight />
              </button>
              <button
                disabled={!guidedAccessEnabled}
                aria-disabled={!guidedAccessEnabled}
                title={!guidedAccessEnabled ? 'This access option is coming soon' : undefined}
                onClick={() => {
                  setMode('register');
                  setStep(0);
                }}
              >
                <span>
                  <Sprout />
                </span>
                <div>
                  <b>I’m starting with MihiMura</b>
                  <small>Create a new farmer identity</small>
                </div>
                <ArrowRight />
              </button>
            </div>
            {demoEnabled && (
              <button className="demo-access" onClick={demo}>
                Explore with a safe demo farmer
              </button>
            )}
            {error && <p className="auth-error">{error}</p>}
          </div>
        )}

        {mode === 'login' && (
          <div className="auth-journey login-journey">
            <button className="mini-back" onClick={() => setMode('choice')}>
              <ArrowLeft /> Access options
            </button>
            <span className="auth-kicker">Welcome back</span>
            <h2>Open your field memory</h2>
            <p>Your projects, task history and previous recommendations are waiting.</p>
            <div className="auth-method-tabs">
              <button
                className={loginMethod === 'email' ? 'active' : ''}
                onClick={() => {
                  setLoginMethod('email');
                  setError('');
                  setInfo('');
                }}
              >
                <Mail /> Email key
              </button>
              <button
                className={loginMethod === 'phone' ? 'active' : ''}
                onClick={() => {
                  setLoginMethod('phone');
                  setError('');
                  setInfo('');
                }}
              >
                <Fingerprint /> Phone OTP
              </button>
            </div>
            {loginMethod === 'email' ? (
              <>
                <div className="journey-field">
                  <span>
                    <Mail />
                  </span>
                  <input
                    autoFocus
                    placeholder="Email address"
                    value={data.email}
                    onChange={(e) => setData({ ...data, email: e.target.value })}
                  />
                </div>
                <div className="journey-field">
                  <span>
                    <LockKeyhole />
                  </span>
                  <input
                    type={show ? 'text' : 'password'}
                    placeholder="Password"
                    value={data.password}
                    onChange={(e) => setData({ ...data, password: e.target.value })}
                  />
                  <button onClick={() => setShow((v) => !v)}>{show ? <EyeOff /> : <Eye />}</button>
                </div>
                <button className="forgot-link" disabled={busy || !data.email} onClick={forgot}>
                  Forgot access key? Send a secure reset link
                </button>
                <Button disabled={busy || !data.email || !data.password} onClick={emailLogin}>
                  {busy ? 'Opening field memory…' : 'Enter MihiMura'} <ArrowRight />
                </Button>
              </>
            ) : (
              <>
                <div className="journey-field">
                  <span>
                    <Fingerprint />
                  </span>
                  <input
                    autoFocus
                    placeholder="+94 77 123 4567"
                    value={phone}
                    disabled={otpSent}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
                {otpSent && (
                  <div className="journey-field otp-field">
                    <span>
                      <ShieldCheck />
                    </span>
                    <input
                      inputMode="numeric"
                      maxLength={8}
                      placeholder="SMS verification code"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    />
                    <button
                      onClick={() => {
                        setOtpSent(false);
                        setOtp('');
                      }}
                    >
                      Change
                    </button>
                  </div>
                )}
                <Button
                  disabled={busy || (!otpSent ? phone.length < 10 : otp.length < 6)}
                  onClick={phoneLogin}
                >
                  {busy ? 'Verifying…' : otpSent ? 'Verify code & continue' : 'Send one-time code'}{' '}
                  <ArrowRight />
                </Button>
                <small className="otp-note">
                  Requires Phone authentication and an SMS provider to be configured in Supabase Auth.
                </small>
              </>
            )}
            <button className="google-small" disabled={!supabaseConfigured} onClick={google}>
              <span className="google-g">
                <GoogleIcon />
              </span>{' '}
              Use Google instead
            </button>
            {info && <p className="auth-info">{info}</p>}
            {error && <p className="auth-error">{error}</p>}
          </div>
        )}

        {mode === 'register' && (
          <div className="auth-journey">
            <button className="mini-back" onClick={() => (step ? setStep((s) => s - 1) : setMode('choice'))}>
              <ArrowLeft /> {step ? 'Previous step' : 'Access options'}
            </button>
            <div className="journey-progress">
              {steps.map((s, i) => (
                <div key={s} className={i <= step ? 'active' : ''}>
                  <i>{i < step ? <Check /> : i + 1}</i>
                  <span>{s}</span>
                </div>
              ))}
            </div>
            {step === 0 && (
              <>
                <span className="auth-kicker">Step 1 · Identity</span>
                <h2>Who will MihiMura support?</h2>
                <p>This shapes the workspace and permissions after onboarding.</p>
                <div className="journey-field">
                  <span>
                    <UserRound />
                  </span>
                  <input
                    autoFocus
                    placeholder="Your name"
                    value={data.name}
                    onChange={(e) => setData({ ...data, name: e.target.value })}
                  />
                </div>
                <div className="role-cards">
                  {[
                    ['farmer', 'Farmer', 'Daily field decisions'],
                    ['manager', 'Farm manager', 'Teams and multiple plots'],
                    ['agronomist', 'Agronomist', 'Review and expert cases'],
                    ['supplier', 'Verified supplier', 'Catalog and delivery operations'],
                    ['analyst', 'Gov / NGO analyst', 'Privacy-preserving regional analytics'],
                  ].map((x) => (
                    <button
                      className={data.role === x[0] ? 'active' : ''}
                      onClick={() => setData({ ...data, role: x[0] })}
                      key={x[0]}
                    >
                      <b>{x[1]}</b>
                      <small>{x[2]}</small>
                    </button>
                  ))}
                </div>
              </>
            )}
            {step === 1 && (
              <>
                <span className="auth-kicker">Step 2 · Contact</span>
                <h2>Where should your field identity live?</h2>
                <p>
                  Use an email you can access for account confirmation, recovery and optional Google linking.
                </p>
                <div className="journey-field">
                  <span>
                    <Mail />
                  </span>
                  <input
                    autoFocus
                    type="email"
                    placeholder="you@example.com"
                    value={data.email}
                    onChange={(e) => setData({ ...data, email: e.target.value })}
                  />
                </div>
              </>
            )}
            {step === 2 && (
              <>
                <span className="auth-kicker">Step 3 · Security</span>
                <h2>Create your access key</h2>
                <p>Use at least 6 characters. Supabase Auth can be configured with MFA for production.</p>
                <div className="journey-field">
                  <span>
                    <LockKeyhole />
                  </span>
                  <input
                    autoFocus
                    type={show ? 'text' : 'password'}
                    placeholder="Secure password"
                    value={data.password}
                    onChange={(e) => setData({ ...data, password: e.target.value })}
                  />
                  <button onClick={() => setShow((v) => !v)}>{show ? <EyeOff /> : <Eye />}</button>
                </div>
                <div className={`password-meter ${data.password.length >= 6 ? 'good' : ''}`}>
                  <i />
                  <span>
                    {data.password.length >= 6 ? 'Ready for account creation' : 'At least 6 characters'}
                  </span>
                </div>
              </>
            )}
            {step === 3 && (
              <>
                <span className="auth-kicker">Step 4 · Ready</span>
                <h2>Your MihiMura identity is ready.</h2>
                <p>
                  After account creation, we’ll collect only the farm context required to personalize climate
                  and crop guidance.
                </p>
                <div className="identity-summary">
                  <div>
                    <UserRound />
                    <span>
                      <small>Name</small>
                      <b>{data.name}</b>
                    </span>
                  </div>
                  <div>
                    <Mail />
                    <span>
                      <small>Email</small>
                      <b>{data.email}</b>
                    </span>
                  </div>
                  <div>
                    <ShieldCheck />
                    <span>
                      <small>Role</small>
                      <b>{data.role}</b>
                    </span>
                  </div>
                </div>
              </>
            )}
            {step < 3 ? (
              <Button disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
                Continue journey <ArrowRight />
              </Button>
            ) : (
              <Button disabled={busy || !supabaseConfigured} onClick={create}>
                {busy ? 'Creating secure identity…' : 'Create identity & personalize'} <ArrowRight />
              </Button>
            )}
            <button className="google-small" disabled={!supabaseConfigured} onClick={google}>
              <span className="google-g">
                <GoogleIcon />
              </span>{' '}
              Prefer Google? Continue instantly
            </button>
            {info && <p className="auth-info">{info}</p>}
            {error && <p className="auth-error">{error}</p>}
          </div>
        )}

        {mode === 'recovery' && (
          <div className="auth-journey login-journey">
            <span className="auth-kicker">Secure recovery</span>
            <h2>Choose a new password</h2>
            <p>
              The reset link established a temporary authenticated recovery session. Set a new access key to
              finish.
            </p>
            <div className="journey-field">
              <span>
                <LockKeyhole />
              </span>
              <input
                autoFocus
                type={show ? 'text' : 'password'}
                placeholder="New password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
              <button onClick={() => setShow((v) => !v)}>{show ? <EyeOff /> : <Eye />}</button>
            </div>
            <div className={`password-meter ${newPassword.length >= 6 ? 'good' : ''}`}>
              <i />
              <span>{newPassword.length >= 6 ? 'Ready to update' : 'At least 6 characters'}</span>
            </div>
            <Button disabled={busy || newPassword.length < 6 || !user} onClick={finishRecovery}>
              {busy ? 'Updating…' : 'Update password'} <ArrowRight />
            </Button>
            {!user && (
              <p className="auth-error">
                Open this page from the password-reset link so Supabase can validate the recovery session.
              </p>
            )}
            {info && <p className="auth-info">{info}</p>}
            {error && <p className="auth-error">{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
