"use client";

import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

export function AccessTokenDemo() {
  const { accessToken, isAuthenticated } = useAuth();
  const [response, setResponse] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);

  const makeAuthenticatedRequest = async () => {
    setIsLoading(true);
    setResponse("");

    try {
      // Example: Make an authenticated request to your backend API
      // Replace with your actual API endpoint
      // No need to pass requireAuth - authentication is now automatic
      const result = await apiClient.get("/api/protected-route").json();
      setResponse(JSON.stringify(result, null, 2));
    } catch (error) {
      setResponse(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Access Token Demo</CardTitle>
          <CardDescription>
            Please log in to see the access token demo
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Access Token Demo</CardTitle>
        <CardDescription>
          Your access token is automatically used for all API requests
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h4 className="font-medium mb-2">Access Token Status:</h4>
          <Badge variant={accessToken ? "default" : "destructive"}>
            {accessToken ? "Available" : "Not Available"}
          </Badge>
        </div>

        {accessToken && (
          <div>
            <h4 className="font-medium mb-2">Token Preview:</h4>
            <code className="text-xs bg-muted p-2 rounded block overflow-hidden">
              {`${accessToken.substring(0, 20)}...${accessToken.substring(
                accessToken.length - 10
              )}`}
            </code>
          </div>
        )}

        <div className="space-y-2">
          <h4 className="font-medium">Usage Example:</h4>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>• Use the `useAuth()` hook to get the access token</p>
            <p>• Use the `apiClient` directly - authentication is automatic</p>
            <p>
              • All API requests will include the Authorization header
              automatically
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <Button
            onClick={makeAuthenticatedRequest}
            disabled={isLoading || !accessToken}
            className="w-full"
          >
            {isLoading ? "Making Request..." : "Test Authenticated Request"}
          </Button>

          {response && (
            <div>
              <h4 className="font-medium mb-2">Response:</h4>
              <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
                {response}
              </pre>
            </div>
          )}
        </div>

        <div className="text-xs text-muted-foreground bg-muted p-3 rounded">
          <strong>Code Example:</strong>
          <pre className="mt-2 text-xs">{`import { apiClient } from '@/lib/api-client';

// Make authenticated request - automatic auth headers
const data = await apiClient.get('/api/data').json();

// POST request with data
const result = await apiClient.post('/api/create', { 
  json: { name: 'example' } 
}).json();`}</pre>
        </div>
      </CardContent>
    </Card>
  );
}
