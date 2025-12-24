// lib/s3-signer.ts
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";


const s3 = new S3Client({
  region: process.env.S3_REGION || "us-east-1",
  endpoint: process.env.S3_ENDPOINT,         
  credentials: {
    accessKeyId: process.env.S3_ACCESS_KEY!,
    secretAccessKey: process.env.S3_SECRET_KEY!,
  },
  forcePathStyle: true,                      // for MinIO
});

function normalizePath(raw: string): string {
  // If it's a full URL, extract only the path
  try {
    const url = new URL(raw);
    return url.pathname; // e.g. "/gopie/visualizations/file.json"
  } catch {
    // Not a URL — return as-is
    return raw;
  }
}

// ---- Signs a single path (e.g. `/mybucket/reports/viz.png`) ----
export async function signUrl(rawPath: string): Promise<string> {
  try {
    if (!rawPath) return rawPath;

    // Strip host if present
    const normalized = normalizePath(rawPath);

    // Ensure no leading slash
    const cleaned = normalized.startsWith("/") ? normalized.slice(1) : normalized;

    const slashIndex = cleaned.indexOf("/");
    if (slashIndex === -1) {
      console.error("signUrl error: Invalid path, no bucket/key", cleaned);
      return rawPath;
    }

    const bucket = cleaned.substring(0, slashIndex);
    const key    = cleaned.substring(slashIndex + 1);

    const command = new GetObjectCommand({
      Bucket: bucket,
      Key: key,
    });

    return await getSignedUrl(s3, command, { expiresIn: 86400 });
  } catch (err) {
    console.error("signUrl error:", err);
    return rawPath;
  }
}
