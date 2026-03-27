import { getAuth } from "@/lib/auth/auth";
import { toNextJsHandler } from "better-auth/next-js";
import { NextRequest } from "next/server";
import { isEncryptionEnabled, decryptPassword } from "@/lib/crypto/password-decryption";

let _handlers: {
  GET: (req: NextRequest) => Promise<Response>;
  POST: (req: NextRequest) => Promise<Response>;
} | null = null;

function getHandlers() {
  return (_handlers ??= (() => {
    const handlers = toNextJsHandler(getAuth());
    return {
      GET: handlers.GET as (req: NextRequest) => Promise<Response>,
      POST: handlers.POST as (req: NextRequest) => Promise<Response>,
    };
  })());
}

// Password field names that may contain encrypted values
const PASSWORD_FIELDS = ["password", "newPassword", "currentPassword"] as const;

// Endpoints that carry password fields
const PASSWORD_ENDPOINTS = [
  "/sign-in/email",
  "/sign-up/email",
  "/reset-password",
  "/change-password",
  "/two-factor/enable",
  "/two-factor/disable",
  "/two-factor/get-totp-uri",
];

async function withDecryptedPasswords(request: NextRequest): Promise<NextRequest> {
  if (!isEncryptionEnabled()) return request;

  const pathname = request.nextUrl.pathname;
  if (!PASSWORD_ENDPOINTS.some((ep) => pathname.includes(ep))) return request;

  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return request;

  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return request;
  }

  for (const field of PASSWORD_FIELDS) {
    const value = body[field];
    if (typeof value === "string") {
      try {
        body[field] = decryptPassword(value);
      } catch (err) {
        console.error(`[Auth] Password decryption failed for field "${field}":`, err);
        // Keep the original value — field may not be encrypted on this endpoint
      }
    }
  }

  // Always reconstruct — body stream is consumed after request.json()
  const newBody = JSON.stringify(body);
  const newHeaders = new Headers(request.headers);
  newHeaders.set("content-length", String(Buffer.byteLength(newBody)));

  return new NextRequest(request.url, {
    method: request.method,
    headers: newHeaders,
    body: newBody,
  });
}

export const GET = async (request: NextRequest): Promise<Response> => {
  return getHandlers().GET(request);
};

export const POST = async (request: NextRequest): Promise<Response> => {
  // Block email registration if disabled
  const isRegistrationAllowed =
    String(process.env.NEXT_PUBLIC_ALLOW_REGISTRATION).trim() === "true";
  const pathname = request.nextUrl.pathname;

  if (!isRegistrationAllowed && pathname.includes("/sign-up/email")) {
    return new Response(
      JSON.stringify({
        error: "Registration is currently disabled",
        message:
          "New user registration is not allowed at this time. Please contact administrator.",
      }),
      { status: 403, headers: { "Content-Type": "application/json" } }
    );
  }

  const decryptedRequest = await withDecryptedPasswords(request);
  return getHandlers().POST(decryptedRequest);
};
