import React, { useState, useEffect } from "react";
import { QRCodeCanvas } from "qrcode.react";
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
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Copy, Shield } from "lucide-react";
import { authClient } from "@/lib/auth/auth-client";
import { encryptPassword } from "@/lib/crypto/password-encryption";

interface MfaSetupProps {
  onVerify: (code: string) => Promise<void>;
  onSkip: () => void;
  isLoading: boolean;
  userId: string;
  email: string;
  password: string;
}

const MfaSetup: React.FC<MfaSetupProps> = ({
  onVerify,
  onSkip,
  isLoading,
  password,
}) => {
  const [mfaData, setMfaData] = useState<{
    totpURI: string;
    secret: string;
    backupCodes?: string[];
  } | null>(null);
  const [code, setCode] = useState("");
  const [copySuccess, setCopySuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setupLoading, setSetupLoading] = useState(true);

  useEffect(() => {
    const setupMfa = async () => {
      setSetupLoading(true);
      setError(null);

      try {
        const encryptedPassword = await encryptPassword(password);

        // First enable 2FA - this returns backup codes
        const { data: enableData, error: enableError } = await authClient.twoFactor.enable({
          password: encryptedPassword,
        });

        if (enableError) {
          onSkip();
          return;
        }

        // Then get the TOTP URI for QR code
        const { data: totpData, error: totpError } = await authClient.twoFactor.getTotpUri({
          password: encryptedPassword,
        });

        if (totpError) {
          onSkip();
          return;
        }

        if (totpData) {
          // Extract secret from TOTP URI
          const secretMatch = totpData.totpURI.match(/secret=([^&]+)/);
          const secret = secretMatch ? secretMatch[1] : "";

          setMfaData({
            totpURI: totpData.totpURI,
            secret,
            backupCodes: enableData?.backupCodes,
          });
        }
      } catch (err) {
        console.error("Error setting up MFA:", err);
        onSkip();
        return;
      } finally {
        setSetupLoading(false);
      }
    };

    setupMfa();
  }, [password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await onVerify(code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    }
  };

  const copyToClipboard = async () => {
    if (mfaData?.secret) {
      try {
        await navigator.clipboard.writeText(mfaData.secret);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
      } catch (err) {
        console.error("Failed to copy:", err);
      }
    }
  };

  if (setupLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl text-center flex items-center justify-center gap-2">
              <Shield className="h-6 w-6" />
              Setting up MFA
            </CardTitle>
            <CardDescription className="text-center">
              Preparing your two-factor authentication...
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!mfaData) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center flex items-center justify-center gap-2">
            <Shield className="h-6 w-6" />
            Set up Two-Factor Authentication
          </CardTitle>
          <CardDescription className="text-center">
            Secure your account with an authenticator app
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              Scan this QR code with your authenticator app (Google
              Authenticator, Authy, etc.)
            </p>

            {/* QR Code with theme-aware colors */}
            <div className="flex justify-center p-6 bg-white dark:bg-white rounded-lg border shadow-sm">
              <div className="p-4 bg-white rounded-lg">
                <QRCodeCanvas value={mfaData.totpURI} size={240} />
              </div>
            </div>
          </div>

          <Separator />

          <div className="space-y-3">
            <Label className="text-sm font-medium">Manual Entry Code</Label>
            <div className="flex items-center space-x-2">
              <code className="flex-1 p-2 bg-muted rounded text-sm font-mono break-all">
                {mfaData.secret}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={copyToClipboard}
                className="shrink-0"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            {copySuccess && (
              <p className="text-xs text-green-600">Copied to clipboard!</p>
            )}
          </div>

          {mfaData.backupCodes && mfaData.backupCodes.length > 0 && (
            <>
              <Separator />
              <div className="space-y-3">
                <Label className="text-sm font-medium">Backup Codes</Label>
                <p className="text-xs text-muted-foreground">
                  Save these backup codes in a secure place. You can use them to
                  access your account if you lose your authenticator device.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {mfaData.backupCodes.map((backupCode, index) => (
                    <code
                      key={index}
                      className="p-2 bg-muted rounded text-sm font-mono text-center"
                    >
                      {backupCode}
                    </code>
                  ))}
                </div>
              </div>
            </>
          )}

          <Separator />

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="totp-code">Verification Code</Label>
              <Input
                id="totp-code"
                type="text"
                placeholder="Enter 6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                maxLength={6}
                className="text-center text-lg tracking-widest"
                disabled={isLoading}
                required
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || code.length !== 6}
            >
              {isLoading ? "Verifying..." : "Verify & Complete Setup"}
            </Button>
          </form>
        </CardContent>

        <CardFooter>
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={onSkip}
            disabled={isLoading}
          >
            Skip for now
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default MfaSetup;
