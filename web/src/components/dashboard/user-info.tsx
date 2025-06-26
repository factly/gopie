"use client";

import { useAuthStore } from "@/lib/stores/auth-store";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

export function UserInfo() {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated || !user) {
    return null;
  }

  const getInitials = (name: string) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .substring(0, 2);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>User Information</CardTitle>
        <CardDescription>Your account details from Zitadel</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-4">
          <Avatar className="h-16 w-16">
            <AvatarImage
              src={user.profilePicture || ""}
              alt={user.displayName || "User"}
            />
            <AvatarFallback className="text-lg">
              {getInitials(user.displayName || "")}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            <h3 className="text-lg font-semibold">{user.displayName}</h3>
            <p className="text-sm text-muted-foreground">@{user.loginName}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">
              Email
            </label>
            <div className="flex items-center space-x-2">
              <p className="text-sm">{user.email}</p>
              {user.emailVerified && (
                <Badge variant="secondary" className="text-xs">
                  Verified
                </Badge>
              )}
            </div>
          </div>

          {user.firstName && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                First Name
              </label>
              <p className="text-sm">{user.firstName}</p>
            </div>
          )}

          {user.lastName && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Last Name
              </label>
              <p className="text-sm">{user.lastName}</p>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-muted-foreground">
              User ID
            </label>
            <p className="text-sm font-mono break-all select-all bg-muted p-2 rounded">
              {user.id || "Not available"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
