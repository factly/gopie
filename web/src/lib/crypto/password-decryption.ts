import { createDecipheriv, hkdfSync } from "crypto";

function deriveAesKey(): Buffer {
  const secret = process.env.PASSWORD_ENCRYPTION_KEY;
  if (!secret) throw new Error("PASSWORD_ENCRYPTION_KEY is not set");
  return Buffer.from(
    hkdfSync("sha256", Buffer.from(secret), Buffer.alloc(32), Buffer.from("password-encryption"), 32)
  );
}

export function isEncryptionEnabled(): boolean {
  return !!process.env.PASSWORD_ENCRYPTION_KEY;
}

/** Returns the derived AES key as base64, exposed to the client via /api/auth/public-key */
export function getDerivedKeyB64(): string {
  return deriveAesKey().toString("base64");
}

/**
 * Decrypts a password encrypted by the client using AES-256-GCM.
 * Wire format (base64): [12-byte IV] [ciphertext + 16-byte GCM tag]
 */
export function decryptPassword(encrypted: string): string {
  const aesKey = deriveAesKey();
  const data = Buffer.from(encrypted, "base64");

  const iv = data.subarray(0, 12);
  const tag = data.subarray(data.length - 16);
  const ciphertext = data.subarray(12, data.length - 16);

  const decipher = createDecipheriv("aes-256-gcm", aesKey, iv);
  decipher.setAuthTag(tag);

  return Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString("utf8");
}
