import React, { useState } from 'react';
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

interface TotpInputProps {
  onSubmit: (code: string) => void;
  isLoading: boolean;
  error?: string;
}

const TotpInput: React.FC<TotpInputProps> = ({ onSubmit, isLoading, error }) => {
  const [code, setCode] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(code);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center">Two-Factor Authentication</CardTitle>
          <CardDescription className="text-center">
            Enter the verification code from your authenticator app
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="totp-code">Authenticator Code</Label>
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

            <Button type="submit" className="w-full" disabled={isLoading || code.length !== 6}>
              {isLoading ? 'Verifying...' : 'Verify Code'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default TotpInput;
