// Check if we're in Docker build time with placeholder env vars
export const isBuildTime = () => {
  const url = process.env.NEXT_PUBLIC_APP_URL;
  return !url || url.startsWith("__");
};

// Get the base URL for Better Auth
// During Docker build, placeholders like __NEXT_PUBLIC_APP_URL__ are used
// These get replaced at runtime by the entrypoint script with actual values
// We need a valid URL for build time only - at runtime the real URL will be present
export const getBaseUrl = () => {
  const url = process.env.NEXT_PUBLIC_APP_URL;
  // Detect Docker build placeholder pattern (starts with __)
  if (!url || url.startsWith("__")) {
    return "http://localhost:3000"; // Build-time fallback only
  }
  return url;
};

// Better Auth session cookie name
// In production with secure cookies (HTTPS), Better Auth prefixes cookie names with "__Secure-"
// This is a browser security feature: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#cookie_prefixes
export const getSessionCookieName = () => {
  const useSecureCookies = String(process.env.BETTER_AUTH_SECURE_COOKIES).trim() !== "false"
    && process.env.NODE_ENV === "production";
  return useSecureCookies
    ? "__Secure-better-auth.session_token"
    : "better-auth.session_token";
};

// Export the cookie name constant for use in places where a function call isn't ideal
export const SESSION_COOKIE_NAME_DEV = "better-auth.session_token";
export const SESSION_COOKIE_NAME_PROD = "__Secure-better-auth.session_token";

export const getCookieDomain = (): string | undefined => {
  const domain = process.env.BETTER_AUTH_COOKIE_DOMAIN;
  // Return undefined if not set or if it's a placeholder
  if (!domain || domain.startsWith("__")) {
    return undefined;
  }
  return domain;
};

