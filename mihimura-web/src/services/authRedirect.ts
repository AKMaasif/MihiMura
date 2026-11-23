/** Supabase redirect allow-list entries are origins, not hash routes. */
export function oauthRedirectUrl(origin: string) {
  return `${origin.replace(/\/$/, '')}/`;
}

/** Message for a provider redirect that came back without a session. */
export function readOAuthError(search: string) {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
  const code = params.get('error');
  if (!code) return '';
  if (code === 'access_denied') return 'Google sign-in was cancelled before MihiMura received a session.';
  return (
    params.get('error_description') ||
    'Google sign-in did not complete. Check the Supabase redirect URL and try again.'
  );
}

/** Move a failed provider return onto the auth screen before React Router starts. */
export function installOAuthReturn() {
  if (typeof window === 'undefined') return;
  const message = readOAuthError(window.location.search);
  if (!message) return;
  sessionStorage.setItem('mihimura_oauth_error', message);
  sessionStorage.removeItem('mihimura_oauth_pending');
  window.history.replaceState({}, '', `${window.location.origin}/#/auth`);
}
