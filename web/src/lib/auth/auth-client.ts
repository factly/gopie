import { createAuthClient } from "better-auth/react";
import { organizationClient, twoFactorClient, adminClient } from "better-auth/client/plugins";
import { getBaseUrl } from "./auth-config";

export const authClient = createAuthClient({
  baseURL: getBaseUrl(),
  plugins: [
    organizationClient(),
    twoFactorClient(),
    adminClient(),
  ],
});
