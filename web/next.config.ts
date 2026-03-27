import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

// Allowed external origins derived from env vars — avoids hardcoding URLs per environment.
const API_URL = process.env.NEXT_PUBLIC_GOPIE_API_URL ?? "http://localhost:8000";
const COMPANION_URL = process.env.NEXT_PUBLIC_COMPANION_URL ?? "http://localhost:3020";
const STORAGE_URL = process.env.NEXT_PUBLIC_STORAGE_URL ?? "http://localhost:9000";

// Global Content Security Policy applied to all routes.
//
// Directive notes:
//   script-src    'unsafe-inline'     — Next.js App Router inline hydration scripts
//                 'wasm-unsafe-eval'  — DuckDB WASM execution
//                 'unsafe-eval'       — Monaco Editor worker bootstrap
//   worker-src    blob:               — DuckDB & Monaco spin up workers via blob: URLs
//   connect-src   API_URL             — Gopie backend API (may be a different origin/port)
//                 COMPANION_URL       — Uppy companion for file uploads
//                 wss: ws:            — LiveKit voice interface (WebRTC signalling)
//                 blob:               — DuckDB WASM streaming fetches
//   img-src       blob: data: https:  — QR codes (data:), avatars (https:), DuckDB previews (blob:)
//   frame-ancestors 'none'            — prevents clickjacking across all pages
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  `connect-src 'self' ${API_URL} ${COMPANION_URL} ${STORAGE_URL} wss: ws: blob:`,
  "worker-src 'self' blob:",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // microphone=self — required for LiveKit voice interface
  // camera/geolocation are not used anywhere in the app so remain blocked
  { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=()" },
];

const nextConfig: NextConfig = {
  serverExternalPackages: ["pg", "pg-native"],
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: SECURITY_HEADERS,
      },
    ];
  },
  webpack: (config) => {
    // Enable WebAssembly
    config.experiments = {
      ...config.experiments,
      asyncWebAssembly: true,
      layers: true,
    };

    // Add proper WASM handling
    config.module.rules.push({
      test: /\.wasm$/,
      type: "asset/resource",
      generator: {
        filename: "static/wasm/[name][ext]",
      },
    });

    // Add proper Worker handling
    config.module.rules.push({
      test: /\.worker\.js$/,
      type: "asset/resource",
      generator: {
        filename: "static/workers/[name][ext]",
      },
    });

    return config;
  },
};

// Wrap the config with Sentry
export default withSentryConfig(nextConfig, {
  // Organization and project from environment variables
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT_WEB,

  // Only print logs for uploading source maps in CI
  silent: !process.env.CI,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Upload a larger set of source maps for prettier stack traces
  widenClientFileUpload: true,

  // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers
  tunnelRoute: "/monitoring",

  // Hide source maps from generated client bundles
  sourcemaps: {
    disable: true,
  },

  // Automatically instrument Vercel cron jobs
  automaticVercelMonitors: true,

  // Use `SENTRY_AUTH_TOKEN` environment variable
  authToken: process.env.SENTRY_AUTH_TOKEN,
});
