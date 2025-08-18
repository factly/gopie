import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { ACCESS_TOKEN_COOKIE, SESSION_ID_COOKIE, SESSION_TOKEN_COOKIE } from "@/constants/zitade";
import { zitadelClient } from "@/lib/auth/zitadel-client";

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

// This middleware protects all routes
export async function middleware(request: NextRequest) {
  // Skip authentication if enable auth is set to false
  const isAuthEnabled = String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";

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
  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;

  // If no session cookies, redirect to login for protected routes
  if (!accessToken) {
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
    const user = await zitadelClient.getUserInfo(accessToken);

    if (!user) {
      // Clear invalid session cookies
      const response = NextResponse.redirect(
        new URL("/auth/login", request.url)
      );
      response.cookies.delete(ACCESS_TOKEN_COOKIE);
      response.cookies.delete(SESSION_TOKEN_COOKIE);
      response.cookies.delete(SESSION_ID_COOKIE);
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
