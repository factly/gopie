export interface ZitadelUser {
  id: string;
  loginName: string;
  displayName: string;
  firstName?: string;
  lastName?: string;
  email: string;
  emailVerified: boolean;
  profilePicture?: string;
  organizationId?: string;
}

export interface ZitadelSession {
  sessionId: string;
  sessionToken: string;
  user?: ZitadelUser;
  expiresAt: number;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope?: string;
  refresh_token?: string;
}

export interface AuthRequest {
  id: string;
  creationDate: string;
  clientId: string;
  scope: string[];
  redirectUri: string;
  loginHint?: string;
}

export interface IdpIntent {
  idpIntentId: string;
  authUrl: string;
}

export interface IdpInformation {
  idpId: string;
  userId: string;
  userName: string;
  rawInformation: {
    User: {
      email: string;
      email_verified: boolean;
      family_name?: string;
      given_name?: string;
      name?: string;
      picture?: string;
      sub: string;
    };
  };
}

export class ZitadelClient {
  private authority: string;
  private clientId: string;
  private clientSecret: string;
  private pat: string;
  private idpId: string;

  constructor() {
    this.authority = process.env.ZITADEL_AUTHORITY!;
    this.clientId = process.env.ZITADEL_CLIENT_ID!;
    this.clientSecret = process.env.ZITADEL_CLIENT_SECRET!;
    this.pat = process.env.ZITADEL_PAT!;
    this.idpId = process.env.ZITADEL_IDP_ID!;
  }

  private async makeRequest(endpoint: string, options: RequestInit = {}) {
    const url = `${this.authority}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.pat}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Zitadel API error: ${response.status} - ${error}`);
    }

    return response.json();
  }

  private async makeOAuthRequest(endpoint: string, options: RequestInit = {}) {
    const url = `${this.authority}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Zitadel OAuth error: ${response.status} - ${error}`);
    }

    return response.json();
  }

  async createSession(loginName: string): Promise<ZitadelSession> {
    const response = await this.makeRequest("/v2/sessions", {
      method: "POST",
      body: JSON.stringify({
        checks: {
          user: {
            loginName: loginName,
          },
        },
      }),
    });

    return {
      sessionId: response.sessionId,
      sessionToken: response.sessionToken,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  }

  private isEmailFormat(input: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(input);
  }

  async updateSession(
    sessionId: string,
    password: string
  ): Promise<ZitadelSession> {
    const response = await this.makeRequest(`/v2/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify({
        checks: {
          password: {
            password: password,
          },
        },
      }),
    });

    return {
      sessionId: sessionId,
      sessionToken: response.sessionToken,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  }

  async getAccessToken(userId: string): Promise<AccessTokenResponse> {
    // Exchange the PAT (actor_token) together with the target userId to
    // obtain a user-scoped opaque access_token via the Token Exchange grant.

    const body = new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
      // The subject we want a token for is the user identified by their ID.
      subject_token: userId,
      subject_token_type: "urn:zitadel:params:oauth:token-type:user_id",
      // Our service-user PAT acts as the actor_token performing the impersonation.
      actor_token: this.pat,
      actor_token_type: "urn:ietf:params:oauth:token-type:access_token",
      scope: "openid profile email",
    });

    const basicAuth = Buffer.from(
      `${this.clientId}:${this.clientSecret}`
    ).toString("base64");

    const response = await fetch(`${this.authority}/oauth/v2/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Authorization: `Basic ${basicAuth}`,
      },
      body: body.toString(),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to exchange access token: ${response.status} – ${errorText}`
      );
    }

    return (await response.json()) as AccessTokenResponse;
  }

  async getUserInfo(sessionId: string): Promise<ZitadelUser> {
    // Get session info which includes user data
    const sessionResponse = await this.makeRequest(`/v2/sessions/${sessionId}`);

    if (!sessionResponse.session?.factors?.user?.id) {
      throw new Error("No user found in session");
    }

    const userId = sessionResponse.session.factors.user.id;

    // Get detailed user information
    const userResponse = await this.makeRequest(`/v2/users/${userId}`);

    const user = userResponse.user;

    const mappedUser = {
      id: user.id || userId, // Use the userId from session if user.id is not available
      loginName:
        user.preferredLoginName ||
        user.username ||
        sessionResponse.session.factors.user.loginName,
      displayName:
        user.human?.profile?.displayName ||
        user.username ||
        sessionResponse.session.factors.user.displayName,
      firstName: user.human?.profile?.givenName,
      lastName: user.human?.profile?.familyName,
      email: user.human?.email?.email,
      emailVerified: user.human?.email?.isVerified || false,
      profilePicture: user.human?.profile?.avatarUrl,
      organizationId: user.details?.resourceOwner,
    };

    return mappedUser;
  }

  async getAuthRequest(authRequestId: string): Promise<AuthRequest> {
    const response = await this.makeRequest(
      `/v2/oidc/auth_requests/${authRequestId}`
    );
    return response.authRequest;
  }

  async finalizeAuthRequest(
    authRequestId: string,
    sessionId: string,
    sessionToken: string
  ): Promise<{ callbackUrl: string }> {
    const response = await this.makeRequest(
      `/v2/oidc/auth_requests/${authRequestId}`,
      {
        method: "POST",
        body: JSON.stringify({
          session: {
            sessionId: sessionId,
            sessionToken: sessionToken,
          },
        }),
      }
    );

    return { callbackUrl: response.callbackUrl };
  }

  async registerUser(userData: {
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    password: string;
  }): Promise<{ userId: string }> {
    // Use email as username if the provided username is an email format
    // This enables email-based login
    const isUsernameEmail = this.isEmailFormat(userData.username);
    const actualUsername = isUsernameEmail ? userData.email : userData.username;

    const response = await this.makeRequest("/v2/users/human", {
      method: "POST",
      body: JSON.stringify({
        username: actualUsername,
        profile: {
          givenName: userData.firstName,
          familyName: userData.lastName,
          displayName: `${userData.firstName} ${userData.lastName}`,
          preferredLanguage: "en",
        },
        email: {
          email: userData.email,
          isVerified: true,
        },
        password: {
          password: userData.password,
          changeRequired: false,
        },
      }),
    });

    return { userId: response.userId };
  }

  async requestPasswordReset(loginName: string): Promise<void> {
    // First, we need to find the user ID by searching for users
    const userId = await this.findUserIdByLoginName(loginName);

    if (!userId) {
      throw new Error("User not found");
    }

    // Now make the password reset request with the correct endpoint
    await this.makeRequest(`/v2/users/${userId}/password_reset`, {
      method: "POST",
      body: JSON.stringify({
        sendLink: {
          notificationType: "NOTIFICATION_TYPE_Email",
          urlTemplate: `${
            process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"
          }/auth/reset-password?userID={{.UserID}}&orgID={{.OrgID}}&codeID={{.CodeID}}&code={{.Code}}`,
        },
      }),
    });
  }

  async findUserIdByLoginName(loginName: string): Promise<string | null> {
    try {
      // Use the Management API v1 to search for users by login name
      const response = await this.makeRequest("/management/v1/users/_search", {
        method: "POST",
        body: JSON.stringify({
          query: {
            offset: "0",
            limit: 100,
            asc: true,
          },
          queries: [
            {
              or_query: {
                queries: [
                  {
                    user_name_query: {
                      user_name: loginName,
                      method: "TEXT_QUERY_METHOD_EQUALS",
                    },
                  },
                  {
                    login_name_query: {
                      login_name: loginName,
                      method: "TEXT_QUERY_METHOD_EQUALS",
                    },
                  },
                  {
                    email_query: {
                      email_address: loginName,
                      method: "TEXT_QUERY_METHOD_EQUALS",
                    },
                  },
                ],
              },
            },
          ],
        }),
      });

      if (response.result && response.result.length > 0) {
        // Return the first matching user's ID
        return response.result[0].id;
      }

      return null;
    } catch (error) {
      console.error("Error searching for user:", error);
      return null;
    }
  }

  async getPublicUserInfo(userId: string): Promise<{
    id: string;
    displayName: string;
    firstName?: string;
    lastName?: string;
    profilePicture?: string;
  } | null> {
    try {
      // Get user information from Zitadel
      const userResponse = await this.makeRequest(`/v2/users/${userId}`);
      const user = userResponse.user;

      if (!user) {
        return null;
      }

      // Return only public information
      return {
        id: user.id || userId,
        displayName:
          user.human?.profile?.displayName ||
          user.username ||
          `${user.human?.profile?.givenName || ""} ${
            user.human?.profile?.familyName || ""
          }`.trim() ||
          "User",
        firstName: user.human?.profile?.givenName,
        lastName: user.human?.profile?.familyName,
        profilePicture: user.human?.profile?.avatarUrl,
      };
    } catch (error) {
      console.error("Error fetching public user info:", error);
      return null;
    }
  }

  async resetPassword(
    userId: string,
    code: string,
    newPassword: string
  ): Promise<void> {
    await this.makeRequest(`/v2/users/${userId}/password`, {
      method: "POST",
      body: JSON.stringify({
        newPassword: {
          password: newPassword,
          changeRequired: false,
        },
        currentPassword: {
          verificationCode: code,
        },
      }),
    });
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.makeRequest(`/v2/sessions/${sessionId}`, {
      method: "DELETE",
    });
  }

  async initiateOAuth(
    successUrl: string,
    failureUrl: string
  ): Promise<IdpIntent> {
    const response = await this.makeRequest("/v2/idp_intents", {
      method: "POST",
      body: JSON.stringify({
        idpId: this.idpId,
        urls: {
          successUrl,
          failureUrl,
        },
      }),
    });

    return {
      idpIntentId: response.details.sequence,
      authUrl: response.authUrl,
    };
  }

  async retrieveIdpInformation(
    idpIntentId: string,
    idpIntentToken: string
  ): Promise<IdpInformation> {
    const response = await this.makeRequest(`/v2/idp_intents/${idpIntentId}`, {
      method: "POST",
      body: JSON.stringify({
        idpIntentToken,
      }),
    });

    return response.idpInformation;
  }

  async createSessionWithIdp(
    idpIntentId: string,
    idpIntentToken: string
  ): Promise<ZitadelSession> {
    const response = await this.makeRequest("/v2/sessions", {
      method: "POST",
      body: JSON.stringify({
        checks: {
          idpIntent: {
            idpIntentId,
            idpIntentToken,
          },
        },
      }),
    });

    return {
      sessionId: response.sessionId,
      sessionToken: response.sessionToken,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  }

  async createSessionWithUserAndIdp(
    userId: string,
    idpIntentId: string,
    idpIntentToken: string
  ): Promise<ZitadelSession> {
    const response = await this.makeRequest("/v2/sessions", {
      method: "POST",
      body: JSON.stringify({
        checks: {
          user: {
            userId,
          },
          idpIntent: {
            idpIntentId,
            idpIntentToken,
          },
        },
      }),
    });

    return {
      sessionId: response.sessionId,
      sessionToken: response.sessionToken,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  }

  async registerUserWithIdp(userData: {
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    idpLinks: Array<{
      idpId: string;
      userId: string;
      userName: string;
    }>;
  }): Promise<{ userId: string }> {
    const response = await this.makeRequest("/v2/users/human", {
      method: "POST",
      body: JSON.stringify({
        username: userData.username,
        profile: {
          givenName: userData.firstName,
          familyName: userData.lastName,
          displayName: `${userData.firstName} ${userData.lastName}`,
        },
        email: {
          email: userData.email,
          isVerified: true,
        },
        idpLinks: userData.idpLinks,
      }),
    });

    return { userId: response.userId };
  }

  async addIdpLinkToUser(
    userId: string,
    idpLink: {
      idpId: string;
      userId: string;
      userName: string;
    }
  ): Promise<void> {
    await this.makeRequest(`/v2/users/${userId}/links`, {
      method: "POST",
      body: JSON.stringify({
        idpLink: {
          idpId: idpLink.idpId,
          userId: idpLink.userId,
          userName: idpLink.userName,
        },
      }),
    });
  }
}

export const zitadelClient = new ZitadelClient();
