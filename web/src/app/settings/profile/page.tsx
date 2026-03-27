"use client";

import { useState, useEffect, useCallback } from "react";
import { authClient } from "@/lib/auth/auth-client";
import { PasswordRules } from "@/components/auth/password-rules";
import { validatePassword } from "@/lib/validation/password";
import { encryptPassword } from "@/lib/crypto/password-encryption";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { QRCodeCanvas } from "qrcode.react";
import {
  KeyRound,
  Shield,
  Link2,
  User,
  Eye,
  EyeOff,
  Pencil,
  Check,
  X,
  Mail,
  Unlink,
} from "lucide-react";

type LinkedAccount = {
  providerId: string;
  accountId: string;
};

export default function ProfilePage() {
  const { data: session, isPending } = authClient.useSession();
  type SessionUser = NonNullable<typeof session>["user"] & {
    twoFactorEnabled?: boolean;
  };
  const user: SessionUser | undefined = session?.user as SessionUser | undefined;

  // --- Profile edit ---
  const [editingName, setEditingName] = useState(false);
  const [name, setName] = useState("");
  const [nameLoading, setNameLoading] = useState(false);
  const [nameError, setNameError] = useState("");

  useEffect(() => {
    if (user) setName(user.name ?? "");
  }, [user]);

  const getInitials = (n?: string | null) =>
    n
      ?.split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) ?? "?";

  const handleUpdateName = async () => {
    if (!name.trim()) return;
    setNameLoading(true);
    setNameError("");
    const { error } = await authClient.updateUser({ name: name.trim() });
    if (error) {
      setNameError(error.message ?? "Failed to update name");
    } else {
      setEditingName(false);
    }
    setNameLoading(false);
  };

  // --- Change password ---
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess(false);
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match");
      return;
    }
    const { valid, errors } = validatePassword(newPassword);
    if (!valid) {
      setPasswordError(errors[0]);
      return;
    }
    setPasswordLoading(true);
    const [encCurrentPassword, encNewPassword] = await Promise.all([
      encryptPassword(currentPassword),
      encryptPassword(newPassword),
    ]);
    const { error } = await authClient.changePassword({
      currentPassword: encCurrentPassword,
      newPassword: encNewPassword,
      revokeOtherSessions: false,
    });
    if (error) {
      setPasswordError(error.message ?? "Failed to change password");
    } else {
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    }
    setPasswordLoading(false);
  };

  // --- Two-Factor Authentication ---
  type TwoFAStep = "idle" | "enter-password" | "setup" | "disable-confirm";
  const [twoFAStep, setTwoFAStep] = useState<TwoFAStep>("idle");
  const [twoFAPassword, setTwoFAPassword] = useState("");
  const [twoFAData, setTwoFAData] = useState<{
    totpURI: string;
    secret: string;
    backupCodes?: string[];
  } | null>(null);
  const [twoFALoading, setTwoFALoading] = useState(false);
  const [twoFAError, setTwoFAError] = useState("");

  const resetTwoFA = () => {
    setTwoFAStep("idle");
    setTwoFAPassword("");
    setTwoFAData(null);
    setTwoFAError("");
  };

  const handleTwoFASetup = async () => {
    setTwoFALoading(true);
    setTwoFAError("");
    const encTwoFAPassword = await encryptPassword(twoFAPassword);
    const [enableResult, totpResult] = await Promise.all([
      authClient.twoFactor.enable({ password: encTwoFAPassword }),
      authClient.twoFactor.getTotpUri({ password: encTwoFAPassword }),
    ]);
    if (enableResult.error || totpResult.error) {
      setTwoFAError(
        enableResult.error?.message ??
        totpResult.error?.message ??
        "Failed to set up 2FA"
      );
      setTwoFALoading(false);
      return;
    }
    const totpURI = totpResult.data?.totpURI ?? "";
    const secretMatch = totpURI.match(/secret=([^&]+)/);
    setTwoFAData({
      totpURI,
      secret: secretMatch ? secretMatch[1] : "",
      backupCodes: enableResult.data?.backupCodes,
    });
    setTwoFAStep("setup");
    setTwoFALoading(false);
  };

  const handleTwoFADisable = async () => {
    setTwoFALoading(true);
    setTwoFAError("");
    const { error } = await authClient.twoFactor.disable({
      password: await encryptPassword(twoFAPassword),
    });
    if (error) {
      setTwoFAError(error.message ?? "Failed to disable 2FA");
    } else {
      resetTwoFA();
    }
    setTwoFALoading(false);
  };

  const twoFactorEnabled = user?.twoFactorEnabled ?? false;

  // --- Linked accounts ---
  const [accounts, setAccounts] = useState<LinkedAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [linkError, setLinkError] = useState("");

  const loadAccounts = useCallback(async () => {
    setAccountsLoading(true);
    const { data } = await authClient.listAccounts();
    if (data) setAccounts(data as LinkedAccount[]);
    setAccountsLoading(false);
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const isGoogleLinked = accounts.some((a) => a.providerId === "google");

  const handleLinkGoogle = async () => {
    setLinkError("");
    await authClient.linkSocial({
      provider: "google",
      callbackURL: window.location.href,
    });
  };

  const handleUnlinkGoogle = async () => {
    setLinkError("");
    const { error } = await authClient.unlinkAccount({ providerId: "google" });
    if (error) {
      setLinkError(error.message ?? "Failed to unlink Google account");
    } else {
      await loadAccounts();
    }
  };

  if (isPending) {
    return (
      <div className="py-10 text-center text-muted-foreground text-sm">
        Loading...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Profile Information ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile Information
          </CardTitle>
          <CardDescription>Update your personal details.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Avatar className="h-14 w-14 rounded-md">
              {user?.image && <AvatarImage src={user.image} />}
              <AvatarFallback className="rounded-md text-base font-semibold">
                {getInitials(user?.name)}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              {editingName ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="h-8 max-w-xs"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleUpdateName();
                      if (e.key === "Escape") {
                        setEditingName(false);
                        setName(user?.name ?? "");
                      }
                    }}
                  />
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={handleUpdateName}
                    disabled={nameLoading}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={() => {
                      setEditingName(false);
                      setName(user?.name ?? "");
                      setNameError("");
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold">{user?.name}</span>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-6 w-6"
                    onClick={() => setEditingName(true)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
              {nameError && (
                <p className="text-xs text-destructive mt-1">{nameError}</p>
              )}
              <p className="text-sm text-muted-foreground flex items-center gap-1.5 mt-0.5">
                <Mail className="h-3.5 w-3.5" />
                {user?.email}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Change Password ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            Change Password
          </CardTitle>
          <CardDescription>
            Update your password to keep your account secure.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleChangePassword}
            className="space-y-4 max-w-sm"
          >
            <div className="space-y-1.5">
              <Label>Current Password</Label>
              <div className="relative">
                <Input
                  type={showCurrent ? "text" : "password"}
                  placeholder="Enter current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  onClick={() => setShowCurrent((v) => !v)}
                >
                  {showCurrent ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>New Password</Label>
              <div className="relative">
                <Input
                  type={showNew ? "text" : "password"}
                  placeholder="Enter new password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  onClick={() => setShowNew((v) => !v)}
                >
                  {showNew ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              <PasswordRules password={newPassword} />
            </div>

            <div className="space-y-1.5">
              <Label>Confirm New Password</Label>
              <Input
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>

            {passwordError && (
              <Alert variant="destructive">
                <AlertDescription>{passwordError}</AlertDescription>
              </Alert>
            )}
            {passwordSuccess && (
              <Alert>
                <AlertDescription>
                  Password changed successfully.
                </AlertDescription>
              </Alert>
            )}

            <Button type="submit" disabled={passwordLoading}>
              {passwordLoading ? "Changing..." : "Change Password"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* ── Two-Factor Authentication ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Add an extra layer of security to your account.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-muted rounded-md">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-sm">Authenticator App</p>
                <p className="text-xs text-muted-foreground">
                  Use an authenticator app for verification codes
                </p>
              </div>
            </div>
            {twoFAStep === "idle" && (
              <Button
                size="sm"
                variant={twoFactorEnabled ? "destructive" : "outline"}
                onClick={() => {
                  setTwoFAError("");
                  setTwoFAStep(
                    twoFactorEnabled ? "disable-confirm" : "enter-password"
                  );
                }}
              >
                <Shield className="h-4 w-4 mr-1.5" />
                {twoFactorEnabled ? "Disable 2FA" : "Enable 2FA"}
              </Button>
            )}
          </div>

          {/* Step: enter password to enable */}
          {twoFAStep === "enter-password" && (
            <div className="p-4 border rounded-lg space-y-3">
              <p className="text-sm font-medium">
                Confirm your password to continue
              </p>
              <Input
                type="password"
                placeholder="Enter your password"
                value={twoFAPassword}
                onChange={(e) => setTwoFAPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTwoFASetup()}
                autoFocus
              />
              {twoFAError && (
                <p className="text-xs text-destructive">{twoFAError}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleTwoFASetup}
                  disabled={twoFALoading || !twoFAPassword}
                >
                  {twoFALoading ? "Loading..." : "Continue"}
                </Button>
                <Button size="sm" variant="outline" onClick={resetTwoFA}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Step: show QR code + backup codes */}
          {twoFAStep === "setup" && twoFAData && (
            <div className="p-4 border rounded-lg space-y-4">
              <p className="text-sm text-muted-foreground">
                Scan this QR code with your authenticator app (Google
                Authenticator, Authy, etc.), then save your backup codes.
              </p>
              <div className="flex justify-center">
                <div className="p-4 bg-white rounded-lg border w-fit">
                  <QRCodeCanvas value={twoFAData.totpURI} size={180} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">
                  Manual entry code
                </Label>
                <code className="block p-2 bg-muted rounded text-xs font-mono break-all">
                  {twoFAData.secret}
                </code>
              </div>
              {twoFAData.backupCodes && twoFAData.backupCodes.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">
                      Backup codes — save these in a secure place
                    </Label>
                    <div className="grid grid-cols-2 gap-1.5">
                      {twoFAData.backupCodes.map((code, i) => (
                        <code
                          key={i}
                          className="p-1.5 bg-muted rounded text-xs font-mono text-center"
                        >
                          {code}
                        </code>
                      ))}
                    </div>
                  </div>
                </>
              )}
              <Button size="sm" onClick={resetTwoFA}>
                Done
              </Button>
            </div>
          )}

          {/* Step: confirm password to disable */}
          {twoFAStep === "disable-confirm" && (
            <div className="p-4 border rounded-lg space-y-3">
              <p className="text-sm font-medium">
                Enter your password to disable 2FA
              </p>
              <Input
                type="password"
                placeholder="Enter your password"
                value={twoFAPassword}
                onChange={(e) => setTwoFAPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTwoFADisable()}
                autoFocus
              />
              {twoFAError && (
                <p className="text-xs text-destructive">{twoFAError}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={handleTwoFADisable}
                  disabled={twoFALoading || !twoFAPassword}
                >
                  {twoFALoading ? "Disabling..." : "Disable 2FA"}
                </Button>
                <Button size="sm" variant="outline" onClick={resetTwoFA}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Linked Accounts ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Linked Accounts
          </CardTitle>
          <CardDescription>
            Connect external accounts for easier sign-in.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 flex items-center justify-center rounded border bg-white shrink-0">
                <svg viewBox="0 0 24 24" className="w-5 h-5">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
              </div>
              <div>
                <p className="font-medium text-sm">Google</p>
                <p className="text-xs text-muted-foreground">
                  {accountsLoading
                    ? "Checking..."
                    : isGoogleLinked
                      ? "Connected"
                      : "Not connected"}
                </p>
              </div>
            </div>
            {!accountsLoading && (
              <Button
                size="sm"
                variant="outline"
                onClick={isGoogleLinked ? handleUnlinkGoogle : handleLinkGoogle}
              >
                {isGoogleLinked ? (
                  <>
                    <Unlink className="h-4 w-4 mr-1.5" />
                    Unlink
                  </>
                ) : (
                  <>
                    <Link2 className="h-4 w-4 mr-1.5" />
                    Link
                  </>
                )}
              </Button>
            )}
          </div>
          {linkError && (
            <p className="text-xs text-destructive">{linkError}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
