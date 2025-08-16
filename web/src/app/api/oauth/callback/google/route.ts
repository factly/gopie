import { NextRequest, NextResponse } from "next/server";
import { ZitadelClient } from "@/lib/auth/zitadel-client";
import { cookies } from "next/headers";
import {
  AUTH_REQUEST_COOKIE,
  COOKIE_MAX_AGE,
  SESSION_ID_COOKIE,
  SESSION_TOKEN_COOKIE,
} from "@/constants/zitade";

export async function GET(request: NextRequest) {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL;
  try {
    const searchParams = request.nextUrl.searchParams;
    const idpIntentId = searchParams.get("id");
    const idpIntentToken = searchParams.get("token");
    let userId = searchParams.get("userId");

    if (!idpIntentId || !idpIntentToken) {
      return NextResponse.redirect(
        new URL("/auth/login?error=missing_oauth_params", baseUrl)
      );
    }

    const zitadelClient = new ZitadelClient();

    // Get IDP information
    const idpInfo = await zitadelClient.retrieveIdpInformation(
      idpIntentId,
      idpIntentToken
    );

    const userData = idpInfo.rawInformation.User;

    let session: { sessionId: string; sessionToken: string };

    if (userId) {
      session = await zitadelClient.createSessionWithUserAndIdp(
        userId,
        idpIntentId,
        idpIntentToken
      );
    }

    // Check if user exists in Zitadel by searching for their email
    const existingUserId = await zitadelClient.findUserIdByLoginName(
      userData.email
    );

    if (existingUserId) {
      // User exists, add IDP link to their account first (if not already linked)
      console.log("User exists with ID:", existingUserId);

      try {
        // Try to add the IDP link to the existing user
        await zitadelClient.addIdpLinkToUser(existingUserId, {
          idpId: idpInfo.idpId,
          userId: userData.sub, // Use the sub from Google
          userName: userData.name || userData.email,
        });
        console.log("Successfully added IDP link to existing user");
      } catch (linkError) {
        // If the link already exists, that's fine - continue with session creation
        console.log("IDP link may already exist or failed to add:", linkError);
      }

      // Create session with existing user and IDP intent
      session = await zitadelClient.createSessionWithUserAndIdp(
        existingUserId,
        idpIntentId,
        idpIntentToken
      );
    } else {
      // User doesn't exist, register them first
      console.log("User not found, registering new user");

      const { userId: newUserId } = await zitadelClient.registerUserWithIdp({
        username: userData.email,
        email: userData.email,
        firstName:
          userData.given_name || userData.name?.split(" ")[0] || "User",
        lastName:
          userData.family_name ||
          userData.name?.split(" ").slice(1).join(" ") ||
          "",
        idpLinks: [
          {
            idpId: idpInfo.idpId,
            userId: userData.sub, // Use the sub from Google
            userName: userData.name || userData.email,
          },
        ],
      });

      // Create session with new user and IDP intent
      session = await zitadelClient.createSessionWithUserAndIdp(
        newUserId,
        idpIntentId,
        idpIntentToken
      );

      userId = newUserId;
    }
    // Set session cookies properly - match what auth utils expects
    const cookieStore = await cookies();
    const cookieOptions: {
      httpOnly: boolean;
      secure: boolean;
      sameSite: "lax" | "strict" | "none" | boolean;
      maxAge: number;
      path: string;
    } = {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: COOKIE_MAX_AGE, // 24 hours
      path: "/",
    };

    cookieStore.set(SESSION_ID_COOKIE, session.sessionId, cookieOptions);
    cookieStore.set(SESSION_TOKEN_COOKIE, session.sessionToken, cookieOptions);

    if (!userId) {
      return NextResponse.redirect(
        new URL("/auth/login?error=missing_user_id", baseUrl)
      );
    }

    // Check auth Methods
    const authMethods = await zitadelClient.getAuthMethods(
      userId,
      session.sessionToken
    );

    if (
      !authMethods.authMethodTypes?.includes("AUTHENTICATION_METHOD_TYPE_TOTP")
    ) {
      return NextResponse.redirect(new URL("/auth/login/mfa"));
    } else {
      const authRequestId = cookieStore.get(AUTH_REQUEST_COOKIE)?.value;
      if (!authRequestId) {
        return NextResponse.redirect(
          new URL("/auth/login?error=missing_auth_request_id", baseUrl)
        );
      }

      const authRequestResponse = await zitadelClient.finalizeAuthRequest(
        authRequestId,
        session.sessionId,
        session.sessionToken
      );

      return NextResponse.json({
        success: true,
        callbackUrl: authRequestResponse.callbackUrl,
      });
    }
  } catch (error) {
    console.error("OAuth callback error:", error);
    return NextResponse.redirect(
      new URL("/auth/login?error=oauth_callback_failed", baseUrl)
    );
  }
}
