import { getDerivedKeyB64 } from "@/lib/crypto/password-decryption";

export function GET() {
  try {
    const publicKey = getDerivedKeyB64();
    return Response.json({ publicKey });
  } catch {
    // Key not configured — encryption disabled
    return Response.json({ publicKey: null });
  }
}
