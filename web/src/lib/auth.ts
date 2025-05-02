import NextAuth from "next-auth";
import { JWT } from "next-auth/jwt";
import ZitadelProvider from "next-auth/providers/zitadel";
import * as openidClient from "openid-client";

async function refreshAccessToken(token: JWT): Promise<JWT | null> {
  try {
    const config = await openidClient.discovery(
      new URL(process.env.ZITADEL_ISSUER ?? ""),
      process.env.ZITADEL_CLIENT_ID || "",
      process.env.ZITADEL_CLIENT_SECRET
    );

    const output = await openidClient.refreshTokenGrant(
      config,
      token.refreshToken as string
    );

    return {
      ...token,
      accessToken: output.access_token,
      expiresAt:
        typeof output.expires_at === "number" ? output.expires_at * 1000 : 0,
      refreshToken: output.refresh_token ?? token.refreshToken, // Fall back to old refresh token
    };
  } catch (error) {
    console.error("Error during refreshAccessToken", error);
    // Return null so JWT callback will understand the session is invalid
    return null;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    ZitadelProvider({
      issuer: process.env.ZITADEL_ISSUER,
      clientId: process.env.ZITADEL_CLIENT_ID,
      clientSecret: process.env.ZITADEL_CLIENT_SECRET,
      authorization: {
        params: {
          scope:
            "openid profile email offline_access urn:zitadel:iam:user:metadata urn:zitadel:iam:user:resourceowner urn:zitadel:iam:org:project:id:zitadel:aud urn:zitadel:iam:org:project:" +
            process.env.NEXT_PUBLIC_ZITADEL_PROJECT_ID +
            ":roles",
        },
      },

      async profile(profile) {
        return {
          id: profile.sub,
          name: profile.name,
          firstName: profile.given_name,
          lastName: profile.family_name,
          email: profile.email,
          loginName: profile.preferred_username,
          image: profile.picture,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      token.user ??= user;
      token.accessToken ??= account?.access_token;
      token.refreshToken ??= account?.refresh_token;
      token.expiresAt ??= (account?.expires_at ?? 0) * 1000;
      token.error = undefined;

      let finalToken = token;
      if (Date.now() < (token.expiresAt as number)) {
        finalToken = token;
      } else {
        if (token.refreshToken) {
          const refreshedToken = await refreshAccessToken(token);
          if (!refreshedToken) {
            // If refresh token is invalid, sign the user out
            return null;
          }
          finalToken = refreshedToken;
        } else {
          return null;
        }
      }

      try {
        const userInfoEndpoint = `${process.env.ZITADEL_ISSUER}/oidc/v1/userinfo`;
        const userInfoResponse = await fetch(userInfoEndpoint, {
          headers: {
            Authorization: `Bearer ${finalToken.accessToken}`,
          },
        });

        if (!userInfoResponse.ok) {
          // If userinfo endpoint fails, the token is invalid
          return null;
        }

        const userInfo = await userInfoResponse.json();
        finalToken.user = userInfo;

        return finalToken;
      } catch (error) {
        console.error("Error fetching user info:", error);
        // If we can't fetch user info, invalidate the session
        return null;
      }
    },
    async session({ session, token }) {
      // If token is null, return session with proper error
      if (!token) {
        return {
          ...session,
          user: undefined,
          error: "RefreshAccessTokenError",
        };
      }

      session.user = {
        // @ts-expect-error type issue
        id: token.user?.id,
        // @ts-expect-error type issue
        email: token.user?.email,
        // @ts-expect-error type issue
        image: token.user?.image,
        // @ts-expect-error type issue
        name: token.user?.name,
        // @ts-expect-error type issue
        loginName: token.user?.loginName,
      };
      // @ts-expect-error type issue
      session.clientId = process.env.ZITADEL_CLIENT_ID;
      // @ts-expect-error type issue
      session.error = token.error;
      if (token.accessToken) {
        // @ts-expect-error type issue
        session.accessToken = token.accessToken;
      }
      return session;
    },
  },
  trustHost: true,
});
