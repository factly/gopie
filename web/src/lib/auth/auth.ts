import { betterAuth } from "better-auth";
import { organization, admin, twoFactor } from "better-auth/plugins";
import { nextCookies } from "better-auth/next-js";
import { getBaseUrl, getCookieDomain } from "./auth-config";
import { getPool } from "@/lib/db/pool";
import {
  sendVerificationEmail as sendVerificationEmailService,
  sendPasswordResetEmail,
  sendInvitationEmail,
  isEmailConfigured,
} from "@/lib/email/sendgrid";
import { APIError } from "better-auth/api";


// Check if we're in development mode
const isDevelopment = process.env.NODE_ENV === "development";

// Lazy initialization for auth instance to avoid build-time errors
// During Next.js build "Collecting page data" phase, this module gets imported
// which would fail if Better Auth tries to validate URLs with placeholder values
let _auth: ReturnType<typeof createAuth> | null = null;

/**
 * Auto-verify a user's email in development mode
 */
async function autoVerifyEmail(userId: string) {
  if (!isDevelopment) return;

  try {
    await getPool().query(
      `UPDATE "user" SET "emailVerified" = true WHERE id = $1`,
      [userId]
    );
    console.log(`[DEV] Auto-verified email for user ${userId}`);
  } catch (error) {
    console.error("[DEV] Failed to auto-verify email:", error);
  }
}

function createAuth() {
  return betterAuth({
    appName: "GoPie",
    baseURL: getBaseUrl(),
    database: getPool(),
    secret: process.env.BETTER_AUTH_SECRET,
    onAPIError: {
      errorURL: "/auth/error",
    },
    emailAndPassword: {
      enabled: true,
      // Require email verification for registration
      requireEmailVerification: true,
      // Password reset configuration
      sendResetPassword: async ({ user, url, token }) => {
        if (isDevelopment) {
          // In development, log the reset URL
          console.log(`[DEV] Password reset for ${user.email}:`);
          console.log(`  Reset URL: ${url}`);
          console.log(`  Token: ${token}`);
          return;
        }

        // In production, send via SendGrid
        if (isEmailConfigured()) {
          // Don't await to prevent timing attacks
          void sendPasswordResetEmail({
            email: user.email,
            resetUrl: url,
            token,
          });
        } else {
          console.log(`[Email] Password reset for ${user.email}: ${url}`);
        }
      },
    },
    emailVerification: {
      // Send verification email on sign up
      sendOnSignUp: true,
      // Auto sign in after verification
      autoSignInAfterVerification: true,
      // Verification token expires in 7 days
      expiresIn: 60 * 60 * 168,
      // Send verification email callback
      sendVerificationEmail: async ({ user, url, token }) => {
        if (isDevelopment) {
          // In development, log the verification URL
          console.log(`[DEV] Email verification for ${user.email}:`);
          console.log(`  Verification URL: ${url}`);
          console.log(`  Token: ${token}`);
          console.log(`  Note: Email will be auto-verified in development mode.`);
          return;
        }

        // In production, send via SendGrid
        if (isEmailConfigured()) {
          // Don't await to prevent timing attacks
          void sendVerificationEmailService({
            email: user.email,
            verificationUrl: url,
            token,
          });
        } else {
          console.log(`[Email] Verification email for ${user.email}: ${url}`);
        }
      },
    },
    socialProviders: {
      google: {
        clientId: process.env.GOOGLE_CLIENT_ID ?? "",
        clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
      },
    },
    // Session configuration
    session: {
      // Cookie-based sessions
      cookieCache: {
        enabled: true,
        maxAge: 60 * 60 * 24 * 7, // 7 days
      },
      expiresIn: 60 * 60 * 24 * 7, // 7 days
      updateAge: 60 * 60 * 24, // 1 day - update session if older than this
    },
    advanced: {
      // Use secure cookies in production (HTTPS)
      // This automatically adds __Secure- prefix to cookie names in production
      useSecureCookies: process.env.NODE_ENV === "production",
      crossSubDomainCookies: process.env.NODE_ENV === "production"
        ? { enabled: true, domain: getCookieDomain()! }
        : undefined,
      // Default cookie attributes for cross-origin requests
      // SameSite=None is required for cross-origin cookies (with Secure attribute)
      defaultCookieAttributes: getCookieDomain()
        ? {
          sameSite: "none" as const,
          secure: true,
          httpOnly: true,
        }
        : undefined,
    },
    plugins: [
      organization({
        allowUserToCreateOrganization: false,
        // Invitation expiry in seconds (default: 48 hours)
        invitationExpiresIn: 60 * 60 * 48,
        // Send invitation email callback
        sendInvitationEmail: async ({ email, inviter, organization, invitation }) => {
          // Build the invitation URL
          const baseUrl = getBaseUrl();
          const invitationUrl = `${baseUrl}/auth/invitation?id=${invitation.id}`;

          // Get inviter details from nested user object
          const inviterName = inviter.user?.name;

          if (isDevelopment) {
            // In development, log the invitation URL
            console.log(`[DEV] Invitation email for ${email}:`);
            console.log(`  Organization: ${organization.name}`);
            console.log(`  Invited by: ${inviterName}`);
            console.log(`  Accept URL: ${invitationUrl}`);
            return;
          }

          // In production, send via SendGrid
          if (isEmailConfigured()) {
            // Don't await to prevent timing attacks
            void sendInvitationEmail({
              email,
              inviterName,
              organizationName: organization.name,
              invitationUrl,
            });
          } else {
            console.log(`[Email] Invitation for ${email} to ${organization.name}: ${invitationUrl}`);
          }
        },
      }),
      admin({
        // Default role for new users
        defaultRole: "user",
      }),
      twoFactor({
        // TOTP issuer name shown in authenticator apps
        issuer: "GoPie",
        // Backup codes configuration
        backupCodes: {
          length: 10,
          characters: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        },
      }),
      nextCookies(),
    ],
    // Trust host for production
    trustedOrigins: process.env.BETTER_AUTH_TRUSTED_ORIGINS?.split(",") || [
      getBaseUrl(),
    ],
    // Database hooks for custom logic
    databaseHooks: {
      session: {
        create: {
          before: async (session) => {
            const result = await getPool().query<{ organizationId: string }>(
              `SELECT "organizationId" FROM member WHERE "userId" = $1 LIMIT 1`,
              [session.userId]
            );
            const orgId = result.rows[0]?.organizationId;
            if (orgId) {
              return { data: { ...session, activeOrganizationId: orgId } };
            }
            return { data: session };
          },
        },
      },
      user: {
        create: {
          // Before a new user is created, check if registration is allowed
          before: async (user, ctx) => {
            const isRegistrationAllowed = String(process.env.NEXT_PUBLIC_ALLOW_REGISTRATION).trim() === "true";

            // If registration is disabled, block new user creation
            if (!isRegistrationAllowed) {
              // Check if this is coming from a social OAuth callback
              // OAuth callbacks include "/callback/" in the path
              const isSocialOAuth = ctx?.path?.includes("/callback/");

              if (isSocialOAuth) {
                throw new APIError("FORBIDDEN", {
                  message: "registration_disabled",
                });
              }

              // Also block direct email registration as a safety net
              throw new APIError("FORBIDDEN", {
                message: "registration_disabled",
              });
            }

            // Allow user creation to proceed normally
            return { data: user };
          },
          // After a new user is created, auto verify in default mode.
          after: async (user) => {
            // In development mode, auto-verify the email
            await autoVerifyEmail(user.id);

            // Add user to the first organization as a member
            try {
              const orgResult = await getPool().query<{ id: string }>(
                `SELECT id FROM organization ORDER BY "createdAt" ASC LIMIT 1`
              );
              const orgId = orgResult.rows[0]?.id;
              if (orgId) {
                const existing = await getPool().query(
                  `SELECT id FROM member WHERE "organizationId" = $1 AND "userId" = $2 LIMIT 1`,
                  [orgId, user.id]
                );
                if (existing.rowCount === 0) {
                  await getPool().query(
                    `INSERT INTO member (id, "organizationId", "userId", role, "createdAt")
                     VALUES (gen_random_uuid()::text, $1, $2, 'member', NOW())`,
                    [orgId, user.id]
                  );
                }
                console.log(`Added user ${user.id} to organization ${orgId} as member`);
              }
            } catch (error) {
              console.error("Failed to add user to organization:", error);
            }
          },
        },
      },
    },
  })
};

/**
 * Get the auth instance (lazy initialization)
 * This prevents Better Auth from being instantiated during Next.js build
 */
export function getAuth(): ReturnType<typeof createAuth> {
  if (!_auth) {
    _auth = createAuth();
  }
  return _auth;
}

// For backwards compatibility - this getter ensures lazy initialization
export const auth = new Proxy({} as ReturnType<typeof createAuth>, {
  get(_, prop) {
    return getAuth()[prop as keyof ReturnType<typeof createAuth>];
  },
});

// Export types for use in the application
export type Session = ReturnType<typeof getAuth>["$Infer"]["Session"];
export type User = ReturnType<typeof getAuth>["$Infer"]["Session"]["user"];
