export interface ZitadelUser {
  id: string;
  displayName: string;
  firstName?: string;
  lastName?: string;
  email: string;
  emailVerified: boolean;
  roles?: Record<string, string[]>;
  organisationId: string;
}

export interface ZitadelUserInfo {
  [key: string]: any;
  sub: string;
  name: string;
  given_name: string;
  family_name: string;
  email: string;
  email_verified: boolean;
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

export interface CodeVerifierParams {
  codeVerifier: string;
  codeChallenge: string;
  state: string;
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
  private pat: string;
  private idpId: string;
  private redirectUri: string;
  private serviceUserId: string;
  private projectId: string;

  // code verifier utility functions
  private generateRandomString(length: number): string {
    const charset =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    let result = "";
    for (let i = 0; i < length; i++) {
      result += charset.charAt(Math.floor(Math.random() * charset.length));
    }
    return result;
  }

  private async sha256(plain: string): Promise<ArrayBuffer> {
    const encoder = new TextEncoder();
    const data = encoder.encode(plain);
    return await crypto.subtle.digest("SHA-256", data);
  }

  private base64URLEncode(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary)
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=/g, "");
  }

  private isEmailFormat(input: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(input);
  }

  async generateCodeVerifier(): Promise<CodeVerifierParams> {
    const codeVerifier = this.generateRandomString(128);
    const hashed = await this.sha256(codeVerifier);
    const codeChallenge = this.base64URLEncode(hashed);
    const state = this.generateRandomString(32);

    return {
      codeVerifier,
      codeChallenge,
      state,
    };
  }

  constructor() {
    this.authority = process.env.ZITADEL_AUTHORITY!;
    this.clientId = process.env.ZITADEL_CLIENT_ID!;
    this.pat = process.env.ZITADEL_PAT!;
    this.idpId = process.env.ZITADEL_IDP_ID!;
    this.redirectUri = process.env.ZITADEL_REDIRECT_URI!;
    this.serviceUserId = process.env.ZITADEL_SERVICE_USER_ID!;
    this.projectId = process.env.ZITADEL_PROJECT_ID!;
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

  async makeOAuthRequest(
    endpoint: string,
    codeVerifierParams: CodeVerifierParams
  ) {
    const params = new URLSearchParams({
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      response_type: "code",
      scope:
        "openid profile email urn:zitadel:iam:user:metadata urn:zitadel:iam:user:resourceowner urn:zitadel:iam:org:project:id:zitadel:aud urn:zitadel:iam:org:project:" +
        this.projectId +
        ":roles",
      code_challenge: codeVerifierParams.codeChallenge,
      code_challenge_method: "S256",
      state: codeVerifierParams.state,
    });

    const url = `${this.authority}${endpoint}?${params.toString()}`;

    const response = await fetch(url, {
      redirect: "manual",
      headers: {
        "X-Zitadel-Login-Client": this.serviceUserId,
      },
    });

    if (response.status >= 300 && response.status < 405) {
      const location = response.headers.get("Location");

      if (location) {
        return location;
      }
    }

    if (!response.ok) {
      throw new Error(`Zitadel OAuth error: ${response.status}`);
    }

    return response.json();
  }

  async getAuthRequest(authRequestId: string): Promise<AuthRequest> {
    const response = await this.makeRequest(
      `/v2/oidc/auth_requests/${authRequestId}`
    );
    return response.authRequest;
  }

  //TODO: handle auth grant request failure
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

  async getUserInfo(accessToken: string): Promise<ZitadelUser> {
    // Get session info which includes user data
    const userResponse: ZitadelUserInfo = await this.makeRequest(
      "/oidc/v1/userinfo",
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    const mappedUser = {
      id: userResponse.sub,
      displayName: userResponse.name,
      firstName: userResponse.given_name,
      lastName: userResponse.family_name,
      email: userResponse.email,
      emailVerified: userResponse.email_verified,
      roles: {},
      organisationId: userResponse['urn:zitadel:iam:user:resourceowner:id'],
    };

    const projectRoles = userResponse[`urn:zitadel:iam:org:project:${this.projectId}:roles`];
    if (projectRoles) {
      const rolesByOrg = Object.entries(projectRoles).reduce((acc: Record<string, string[]>, [role, orgs]) => {
        Object.keys(orgs as Record<string, unknown>).forEach(orgId => {
          acc[orgId] = acc[orgId] ? [...acc[orgId], role] : [role];
        });
        return acc;
      }, {});

      mappedUser.roles = rolesByOrg;
      const orgIds = Object.keys(rolesByOrg);
      if (orgIds.length > 0) {
        mappedUser.organisationId = orgIds[0];
      }
    }

    return mappedUser;
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

  async getSession(sessionId: string): Promise<ZitadelSession> {
    const response = await this.makeRequest(`/v2/sessions/${sessionId}`, {
      method: "GET",
    });

    return {
      sessionId: response.session.id,
      sessionToken: "", //TODO: get session token from response
      user: response.session.factors?.user,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  }

  // Exchange authorization code for access token using PKCE OIDC flow
  async getAccessToken(
    authorizationCode: string,
    codeVerifier: string
  ): Promise<AccessTokenResponse> {
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      code: authorizationCode,
      redirect_uri: this.redirectUri,
      client_id: this.clientId,
      code_verifier: codeVerifier,
    });

    const response = await fetch(`${this.authority}/oauth/v2/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
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

  async getAuthMethods(userId: string, sessionToken: string) {
    const response = await this.makeRequest(
      `/v2/users/${userId}/authentication_methods`,
      {
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${sessionToken}`,
        },
      }
    );
    return response;
  }

  async startTOTPRegistration(userId: string, token: string, data = {}) {
    const response = await this.makeRequest(`/v2/users/${userId}/totp`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    return {
      uri: response.uri,
      secret: response.secret,
    };
  }

  async verifyTOTPRegistration(userId: string, token: string, code: string) {
    const response = await this.makeRequest(`/v2/users/${userId}/totp/verify`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ code }),
    });

    return response;
  }

  async checkTOTP(sessionId: string, sessionToken: string, code: string) {
    const response = await this.makeRequest(`/v2/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify({
        sessionToken,
        checks: {
          totp: {
            code,
          },
        },
      }),
    });

    return response;
  }
}

export const zitadelClient = new ZitadelClient();
