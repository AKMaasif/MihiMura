import { describe, expect, it } from 'vitest';
import { oauthRedirectUrl, readOAuthError } from './authRedirect';

describe('Google redirect helpers', () => {
  it('uses the site origin so the hash router does not swallow the auth code', () => {
    expect(oauthRedirectUrl('http://localhost:5173')).toBe('http://localhost:5173/');
    expect(oauthRedirectUrl('https://mihimura.example/')).toBe('https://mihimura.example/');
  });

  it('explains a cancelled or rejected provider return', () => {
    expect(readOAuthError('?error=access_denied')).toMatch(/cancelled/i);
    expect(readOAuthError('?error=server_error&error_description=redirect%20mismatch')).toBe('redirect mismatch');
    expect(readOAuthError('')).toBe('');
  });
});
