export const ACCESS_TOKEN_COOKIE = "zitadel-access-token";
export const SESSION_ID_COOKIE = "zitadel-session-id";
export const SESSION_TOKEN_COOKIE = "zitadel-session-token";
export const AUTH_REQUEST_COOKIE = 'auth_request_id';
export const USER_ID_COOKIE = 'user_id';
export const PKCE_VERIFIER_COOKIE = 'pkce_verifier';
export const PKCE_STATE_COOKIE = 'pkce_state';
export const COOKIE_MAX_AGE = 10 * 60; 

export function getCookieOptions() {
  const isProduction = process.env.NODE_ENV === 'production';
  // Allow insecure cookies for local testing on custom IPs if explicitly disabled
  const secure = isProduction && process.env.NEXT_PUBLIC_DISABLE_SECURE_COOKIES !== 'true';
  
  return {
    httpOnly: true,
    secure,
    sameSite: 'lax' as const,
    maxAge: COOKIE_MAX_AGE,
    path: '/',
  };
} 
