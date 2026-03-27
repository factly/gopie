"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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
import { authClient } from "@/lib/auth/auth-client";
import { useAuthStore } from "@/lib/stores/auth-store";
import MfaSetup from "@/components/auth/MfaSetup";
import { PasswordRules } from "@/components/auth/password-rules";
import { validatePassword } from "@/lib/validation/password";
import { encryptPassword } from "@/lib/crypto/password-encryption";

export default function RegisterPage() {
  const router = useRouter();
  const { checkSession } = useAuthStore();
  const { data: session, isPending: sessionLoading } = authClient.useSession();
  const [isLoading, setIsLoading] = useState(false);
  const [mfaLoading, setMfaLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    email: "",
    firstName: "",
    lastName: "",
    password: "",
    confirmPassword: "",
  });

  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [emailVerificationPending, setEmailVerificationPending] = useState(false);

  useEffect(() => {
    if (!sessionLoading && session?.user && !registrationSuccess) {
      router.push("/");
    }
  }, [session, sessionLoading, router, registrationSuccess]);

  if (sessionLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (
      !formData.email ||
      !formData.firstName ||
      !formData.lastName ||
      !formData.password ||
      !formData.confirmPassword
    ) {
      setError("Please fill in all fields");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    const { valid, errors } = validatePassword(formData.password);
    if (!valid) {
      setError(`Password must include: ${errors.join(", ").toLowerCase()}`);
      return;
    }

    setIsLoading(true);
    try {
      const name = `${formData.firstName} ${formData.lastName}`.trim();
      const encryptedPassword = await encryptPassword(formData.password);
      const { error: apiError } = await authClient.signUp.email({
        email: formData.email,
        password: encryptedPassword,
        name,
      });
      if (apiError) {
        setError(apiError.message || "Registration failed");
        return;
      }

      // Sign in immediately after registration (succeeds in dev where email is auto-verified)
      const { error: signInError } = await authClient.signIn.email({
        email: formData.email,
        password: encryptedPassword,
      });

      if (signInError) {
        // Email verification is required before signing in (production)
        setEmailVerificationPending(true);
        return;
      }

      setRegistrationSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthLogin = async () => {
    setIsLoading(true);
    try {
      await authClient.signIn.social({ provider: "google", callbackURL: "/" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "OAuth login failed");
      setIsLoading(false);
    }
  };

  const handleInputChange =
    (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setFormData((prev) => ({
        ...prev,
        [field]: e.target.value,
      }));
    };

  if (emailVerificationPending) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl text-center">Check your email</CardTitle>
            <CardDescription className="text-center">
              We sent a verification link to <strong>{formData.email}</strong>.
              Please verify your email to complete registration.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Link href="/auth/login" className="w-full">
              <Button variant="outline" className="w-full">Back to login</Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (registrationSuccess) {
    return (
      <MfaSetup
        userId=""
        email={formData.email}
        password={formData.password}
        isLoading={mfaLoading}
        onVerify={async (code) => {
          setMfaLoading(true);
          try {
            const { error: apiError } = await authClient.twoFactor.verifyTotp({ code });
            if (apiError) {
              throw new Error(apiError.message || "Invalid verification code");
            }
            await checkSession();
            router.push("/");
          } catch (err) {
            throw err;
          } finally {
            setMfaLoading(false);
          }
        }}
        onSkip={async () => {
          await checkSession();
          router.push("/");
        }}
      />
    );
  }

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
          <CardTitle className="text-xl text-center">Create Account</CardTitle>
          <CardDescription className="text-center">
            Enter your information to create your account
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={handleOAuthLogin}
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
            Sign up with Google
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator className="w-full" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or sign up with email
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  type="text"
                  placeholder="John"
                  value={formData.firstName}
                  onChange={handleInputChange("firstName")}
                  disabled={isLoading}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  type="text"
                  placeholder="Doe"
                  value={formData.lastName}
                  onChange={handleInputChange("lastName")}
                  disabled={isLoading}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="john@example.com"
                value={formData.email}
                onChange={handleInputChange("email")}
                disabled={isLoading}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter a password"
                value={formData.password}
                onChange={handleInputChange("password")}
                disabled={isLoading}
                required
              />
              <PasswordRules password={formData.password} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={formData.confirmPassword}
                onChange={handleInputChange("confirmPassword")}
                disabled={isLoading}
                required
              />
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Creating Account..." : "Create Account"}
            </Button>
          </form>
        </CardContent>

        <CardFooter>
          <div className="text-sm text-center w-full">
            <Link href="/auth/login" className="text-primary hover:underline">
              Already have an account? Sign in
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
