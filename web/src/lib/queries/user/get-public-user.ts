import { createQuery } from "react-query-kit";

interface PublicUser {
  id: string;
  displayName: string;
  firstName?: string;
  lastName?: string;
  profilePicture?: string;
}

interface GetPublicUserVariables {
  userId: string;
}

async function fetchPublicUser({
  userId,
}: GetPublicUserVariables): Promise<{ data: PublicUser }> {
  try {
    const response = await fetch(`/api/users/${userId}/public`);

    if (!response.ok) {
      throw new Error(`Failed to fetch user: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw new Error("Failed to fetch user information: " + error);
  }
}

export const usePublicUser = createQuery<
  { data: PublicUser },
  GetPublicUserVariables,
  Error
>({
  queryKey: ["public-user"],
  fetcher: fetchPublicUser,
});
