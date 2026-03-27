"use client";

let cachedKey: CryptoKey | null = null;
let encryptionDisabled = false;

async function loadKey(): Promise<CryptoKey | null> {
  try {
    const res = await fetch("/api/auth/public-key");
    if (!res.ok) return null;
    const { publicKey } = (await res.json()) as { publicKey: string | null };
    if (!publicKey) return null;

    const keyBytes = Uint8Array.from(atob(publicKey), (c) => c.charCodeAt(0));
    return await crypto.subtle.importKey(
      "raw",
      keyBytes.buffer as ArrayBuffer,
      { name: "AES-GCM" },
      false,
      ["encrypt"]
    );
  } catch {
    return null;
  }
}

async function getKey(): Promise<CryptoKey | null> {
  if (encryptionDisabled) return null;
  if (cachedKey) return cachedKey;
  const key = await loadKey();
  if (!key) {
    encryptionDisabled = true;
    return null;
  }
  cachedKey = key;
  return key;
}

/**
 * Encrypts a password using AES-256-GCM with the server-derived key.
 * Falls back to plaintext if the server has no key configured.
 * Wire format (base64): [12-byte IV] [ciphertext + 16-byte GCM tag]
 */
export async function encryptPassword(password: string): Promise<string> {
  const key = await getKey();
  if (!key) return password;

  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(password);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoded);

  const combined = new Uint8Array(12 + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), 12);

  let binary = "";
  for (let i = 0; i < combined.length; i++) binary += String.fromCharCode(combined[i]);

  return btoa(binary);
}
