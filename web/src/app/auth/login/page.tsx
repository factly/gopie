"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/lib/stores/auth-store";

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    login,
    loginWithOAuth,
    isLoading,
    error,
    isAuthenticated,
    checkSession,
    setError,
  } = useAuthStore();
  const returnUrl = searchParams.get("returnUrl") || "/";

  const [formData, setFormData] = useState({
    loginName: "",
    password: "",
  });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // Check if user is already authenticated
    checkSession();
  }, [checkSession]);

  useEffect(() => {
    // Redirect if already authenticated
    if (isAuthenticated) {
      router.push(returnUrl);
    }
  }, [isAuthenticated, router, returnUrl]);

  useEffect(() => {
    // Handle OAuth errors from URL params
    const oauthError = searchParams.get("error");
    if (oauthError) {
      switch (oauthError) {
        case "oauth_failed":
          setError("Google OAuth login failed. Please try again.");
          break;
        case "oauth_callback_failed":
          setError("OAuth callback failed. Please try again.");
          break;
        case "missing_oauth_params":
          setError("OAuth parameters missing. Please try again.");
          break;
        default:
          setError("An error occurred during login. Please try again.");
      }
    }
  }, [searchParams, setError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.loginName || !formData.password) {
      setError("Please fill in all fields");
      return;
    }

    const success = await login(formData.loginName, formData.password);

    if (success) {
      router.push(returnUrl);
    }
  };

  const handleGoogleLogin = async () => {
    await loginWithOAuth(returnUrl);
  };

  const handleInputChange =
    (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setFormData((prev) => ({
        ...prev,
        [field]: e.target.value,
      }));
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
          <CardTitle className="text-xl text-center">Log in to your account</CardTitle>
          <CardDescription className="text-center">
            <div>
              <Link
                href="/auth/register"
                className="text-primary hover:underline"
              >
                Don&apos;t have an account? Sign up
              </Link>
            </div>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Google OAuth Button */}
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={handleGoogleLogin}
            disabled={isLoading}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Continue with Google
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator className="w-full" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or continue with email
              </span>
            </div>
          </div>

          {mounted ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="loginName">Email</Label>
                <Input
                  id="loginName"
                  type="text"
                  placeholder="Enter your email"
                  value={formData.loginName}
                  onChange={handleInputChange("loginName")}
                  disabled={isLoading}
                  required
                  autoComplete="username"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleInputChange("password")}
                  disabled={isLoading}
                  required
                  autoComplete="current-password"
                />
              </div>

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Signing In..." : "Sign In"}
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="h-[180px] flex items-center justify-center">
                <div className="text-muted-foreground">Loading form...</div>
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <div className="text-sm text-center space-y-2">
            <div>
              <Link
                href="/auth/forgot-password"
                className="text-primary hover:underline"
              >
                Forgot your password?
              </Link>
            </div>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center p-4">
          Loading...
        </div>
      }
    >
      <LoginPageInner />
    </Suspense>
  );
}
