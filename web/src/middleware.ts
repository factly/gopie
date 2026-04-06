import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getSessionCookieName } from "@/lib/auth/auth-config";

// Build CSP once at module load — env vars are static for the lifetime of the process.
const API_URL = process.env.NEXT_PUBLIC_GOPIE_API_URL ?? "http://localhost:8000";
const COMPANION_URL = process.env.NEXT_PUBLIC_COMPANION_URL ?? "http://localhost:3020";
const STORAGE_URL = process.env.NEXT_PUBLIC_STORAGE_URL ?? "http://localhost:9000";

// Companion generates presigned URLs using virtual-hosted style (e.g. http://gopie.localhost:9000).
// Derive a wildcard CSP entry to cover all bucket subdomains.
const STORAGE_URL_WILDCARD = (() => {
  try {
    const u = new URL(STORAGE_URL);
    return `${u.protocol}//*.${u.host}`;
  } catch {
    return "";
  }
})();

// NOTE: 'unsafe-inline' in script-src weakens XSS protection significantly.
// The proper Next.js 15 approach is to generate a per-request nonce in middleware,
// pass it via a request header (x-nonce), read it in the root layout via headers(),
// and replace 'unsafe-inline' with `'nonce-{nonce}' 'strict-dynamic'`.
// 'unsafe-eval' remains required for Monaco Editor; 'wasm-unsafe-eval' for DuckDB WASM.
const BASE_CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' 'unsafe-eval' https://cdn.jsdelivr.net",
  "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  `connect-src 'self' ${API_URL} ${COMPANION_URL} ${STORAGE_URL} ${STORAGE_URL_WILDCARD} wss: ws: blob:`,
  "worker-src 'self' blob:",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
].join("; ");

function applySecurityHeaders(response: NextResponse): NextResponse {
  response.headers.set("Content-Security-Policy", BASE_CSP);
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(self), geolocation=()");
  return response;
}

// Better Auth session cookie name (includes __Secure- prefix in production)
const SESSION_COOKIE_NAME = getSessionCookieName();

// Protected routes that require authentication
const protectedRoutes = [
  "/",
  "/chat",
  "/projects",
  "/datasets",
  "/schemas",
  "/settings",
];

// Public routes that don't require authentication
const publicRoutes = [
  "/auth/login",
  "/auth/register",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/two-factor",
  "/auth/invitation",
];

// This middleware protects all routes
export async function middleware(request: NextRequest) {
  // Skip authentication if enable auth is set to false
  const isAuthEnabled = String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";
  const isRegistrationAllowed = String(process.env.NEXT_PUBLIC_ALLOW_REGISTRATION).trim() === "true";

  // If auth is not enabled, skip all authentication checks
  if (!isAuthEnabled) {
    return applySecurityHeaders(NextResponse.next());
  }

  const { pathname } = request.nextUrl;

  // Block registration routes if registration is disabled
  if (!isRegistrationAllowed && pathname.startsWith("/auth/register")) {
    // Redirect to login page
    const loginUrl = new URL("/auth/login", request.url);
    return applySecurityHeaders(NextResponse.redirect(loginUrl));
  }

  // Allow public routes
  if (publicRoutes.some((route) => pathname.startsWith(route))) {
    return applySecurityHeaders(NextResponse.next());
  }

  // Allow API routes - Better Auth handles its own authentication via /api/auth/*
  if (pathname.startsWith("/api")) {
    return applySecurityHeaders(NextResponse.next());
  }

  // Check for Better Auth session cookie
  const sessionToken = request.cookies.get(SESSION_COOKIE_NAME)?.value;

  // If no session cookie, redirect to login for protected routes
  if (!sessionToken) {
    if (
      protectedRoutes.some(
        (route) => pathname === route || pathname.startsWith(route + "/")
      )
    ) {
      const url = request.nextUrl.clone();
      const returnUrl = encodeURIComponent(url.pathname + url.search);

      // Redirect to login page with return URL
      const loginUrl = new URL(
        `/auth/login?returnUrl=${returnUrl}`,
        request.url
      );
      return applySecurityHeaders(NextResponse.redirect(loginUrl));
    }
    return applySecurityHeaders(NextResponse.next());
  }

  // Session exists, allow access
  // Note: Better Auth validates sessions server-side via the API route
  // The middleware only checks for cookie presence for routing purposes
  return applySecurityHeaders(NextResponse.next());
}

// Configure which routes to run the middleware on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public assets
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png|.*\\.jpg|.*\\.jpeg|.*\\.gif|.*\\.svg|.*\\.ico|.*\\.wasm|.*\\.worker\\.js).*)",
  ],
};
