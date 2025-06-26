import { NextRequest, NextResponse } from "next/server";
import { ZitadelClient } from "@/lib/auth/zitadel-client";
import { cookies } from "next/headers";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const idpIntentId = searchParams.get("id");
    const idpIntentToken = searchParams.get("token");
    const error = searchParams.get("error");

    if (error) {
      const failureUrl =
        searchParams.get("state") || "/auth/login?error=oauth_failed";
      return NextResponse.redirect(new URL(failureUrl, request.url));
    }

    if (!idpIntentId || !idpIntentToken) {
      return NextResponse.redirect(
        new URL("/auth/login?error=missing_oauth_params", request.url)
      );
    }

    const zitadelClient = new ZitadelClient();

    // Get IDP information
    const idpInfo = await zitadelClient.retrieveIdpInformation(
      idpIntentId,
      idpIntentToken
    );

    console.log("IDP Information:", JSON.stringify(idpInfo, null, 2));

    const userData = idpInfo.rawInformation.User;

    // Check if user exists in Zitadel by searching for their email
    const existingUserId = await zitadelClient.findUserIdByLoginName(
      userData.email
    );

    let session: { sessionId: string; sessionToken: string };

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
    }

    // Set session cookies properly - match what auth utils expects
    const cookieStore = await cookies();

    // Store session ID under 'zitadel-session'
    cookieStore.set("zitadel-session", session.sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 24 * 60 * 60, // 24 hours
      path: "/",
    });

    // Store session token under 'zitadel-session-token'
    cookieStore.set("zitadel-session-token", session.sessionToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 24 * 60 * 60, // 24 hours
      path: "/",
    });

    // Redirect to dashboard or original destination
    const returnUrl = searchParams.get("returnUrl") || "/";
    return NextResponse.redirect(new URL(returnUrl, request.url));
  } catch (error) {
    console.error("OAuth callback error:", error);
    return NextResponse.redirect(
      new URL("/auth/login?error=oauth_callback_failed", request.url)
    );
  }
}
