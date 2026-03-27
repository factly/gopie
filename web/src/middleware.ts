import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getSessionCookieName } from "@/lib/auth/auth-config";

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
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Block registration routes if registration is disabled
  if (!isRegistrationAllowed && pathname.startsWith("/auth/register")) {
    // Redirect to login page
    const loginUrl = new URL("/auth/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Allow public routes
  if (publicRoutes.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Allow API routes - Better Auth handles its own authentication via /api/auth/*
  if (pathname.startsWith("/api")) {
    return NextResponse.next();
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
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
  }

  // Session exists, allow access
  // Note: Better Auth validates sessions server-side via the API route
  // The middleware only checks for cookie presence for routing purposes
  return NextResponse.next();
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
