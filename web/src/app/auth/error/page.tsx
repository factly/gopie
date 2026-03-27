"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AlertCircle, Home } from "lucide-react";

// Error code to message mapping
const ERROR_MESSAGES: Record<string, { title: string; description: string; helpText?: string }> = {
  registration_disabled: {
    title: "Registration Disabled",
    description: "New user registration is currently disabled.",
    helpText: "If you already have an account, please try logging in. If you need access, please contact support at gopie@factly.in.",
  },
  oauth_failed: {
    title: "OAuth Login Failed",
    description: "Unable to complete Google sign-in.",
    helpText: "Please try again or use email login instead.",
  },
  oauth_callback_failed: {
    title: "OAuth Callback Failed",
    description: "There was an error processing your Google login.",
    helpText: "Please try logging in again.",
  },
  email_not_verified: {
    title: "Email Not Verified",
    description: "Your email address has not been verified yet.",
    helpText: "Please check your inbox for the verification email and click the link to activate your account.",
  },
  unauthorized: {
    title: "Unauthorized Access",
    description: "You don't have permission to access this resource.",
    helpText: "Please contact your administrator if you believe this is an error.",
  },
};

function AuthErrorPageInner() {
  const searchParams = useSearchParams();
  const errorCode = searchParams.get("error") || "unknown";

  // Get error details from mapping, or use defaults for unknown errors
  const errorInfo = ERROR_MESSAGES[errorCode] || {
    title: "Authentication Error",
    description: decodeURIComponent(errorCode).replace(/_/g, " "),
    helpText: "Please try again or contact support if the problem persists.",
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-2">
            <Image
              src="/GoPie_Logo.svg"
              alt="GoPie Logo"
              width={150}
              height={40}
              className="dark:hidden"
              priority
            />
            <Image
              src="/GoPie_Logo_Dark.svg"
              alt="GoPie Logo"
              width={150}
              height={40}
              className="hidden dark:block"
              priority
            />
          </div>
          <div className="flex justify-center">
            <AlertCircle className="h-12 w-12 text-destructive" />
          </div>
          <CardTitle className="text-xl text-center">
            {errorInfo.title}
          </CardTitle>
          <CardDescription className="text-center">
            {errorInfo.description}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {errorInfo.helpText && (
            <div className="text-sm text-center text-muted-foreground">
              <p>{errorInfo.helpText}</p>
            </div>
          )}

          <div className="space-y-2">
            <Button
              className="w-full"
              asChild
            >
              <Link href="/auth/login">
                <Home className="mr-2 h-4 w-4" />
                Back to Login
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      }
    >
      <AuthErrorPageInner />
    </Suspense>
  );
}
