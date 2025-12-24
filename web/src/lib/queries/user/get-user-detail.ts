import { createQuery } from "react-query-kit";

interface UserDetail {
  id: string;
  human?: {
    profile: {
      givenName?: string;
      familyName?: string;
      nickName?: string;
      displayName?: string;
      preferredLanguage?: string;
      gender?: string;
      avatarUrl?: string;
    };
    email: {
      email: string;
      isVerified: boolean;
    }
  };
}

interface GetUserDetailVariables {
  userId: string;
}

async function fetchUserDetail({
  userId,
}: GetUserDetailVariables): Promise<{ user: UserDetail }> {
  try {
    const response = await fetch(`/api/users/${userId}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch user: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw new Error("Failed to fetch user information: " + error);
  }
}

export const useUserDetail = createQuery<
  { user: UserDetail },
  GetUserDetailVariables,
  Error
>({
  queryKey: ["user-detail"],
  fetcher: fetchUserDetail,
});
