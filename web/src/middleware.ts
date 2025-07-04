import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE_NAME = "zitadel-session";
const SESSION_TOKEN_COOKIE_NAME = "zitadel-session-token";

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
];

async function validateSession(sessionId: string): Promise<boolean> {
  try {
    // Validate session by calling Zitadel's session API
    const sessionResponse = await fetch(
      `${process.env.ZITADEL_AUTHORITY}/v2/sessions/${sessionId}`,
      {
        headers: {
          Authorization: `Bearer ${process.env.ZITADEL_PAT}`,
          "Content-Type": "application/json",
        },
      }
    );

    if (!sessionResponse.ok) {
      return false;
    }

    const sessionData = await sessionResponse.json();

    // Check if session exists and has a valid user
    return !!sessionData.session?.factors?.user?.id;
  } catch (error) {
    console.error("Session validation failed:", error);
    return false;
  }
}

// This middleware protects all routes
export async function middleware(request: NextRequest) {
  // Skip authentication if enable auth is set to false
  const isAuthEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

  // If auth is not enabled, skip all authentication checks
  if (!isAuthEnabled) {
    console.log("Auth is disabled, skipping middleware");
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Allow public routes
  if (publicRoutes.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Allow API routes (except auth routes which handle their own authentication)
  if (pathname.startsWith("/api") && !pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  // Check for session cookies
  const sessionId = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  const sessionToken = request.cookies.get(SESSION_TOKEN_COOKIE_NAME)?.value;

  // If no session cookies, redirect to login for protected routes
  if (!sessionId || !sessionToken) {
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

  // Validate session (only for protected routes)
  if (
    protectedRoutes.some(
      (route) => pathname === route || pathname.startsWith(route + "/")
    )
  ) {
    const isValid = await validateSession(sessionId);

    if (!isValid) {
      // Clear invalid session cookies
      const response = NextResponse.redirect(
        new URL("/auth/login", request.url)
      );
      response.cookies.delete(SESSION_COOKIE_NAME);
      response.cookies.delete(SESSION_TOKEN_COOKIE_NAME);
      return response;
    }
  }

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
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png|.*\\.jpg|.*\\.jpeg|.*\\.gif|.*\\.svg|.*\\.ico).*)",
  ],
};
