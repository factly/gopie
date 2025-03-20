import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { auth } from "@/lib/auth";

// This middleware protects all routes
export async function middleware(request: NextRequest) {
  const session = await auth();

  // If the user is not authenticated and trying to access a protected route
  if (!session) {
    // Store the original URL to redirect back after login
    const url = request.nextUrl.clone();
    const returnUrl = encodeURIComponent(url.pathname + url.search);

    // Redirect to login page with return URL
    const loginUrl = new URL(
      `/api/auth/signin?callbackUrl=${returnUrl}`,
      request.url
    );
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Configure which routes to run the middleware on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/auth (Auth API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
};
