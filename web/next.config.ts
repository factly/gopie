import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  /* config options here */
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
  hideSourceMaps: true,

  // Automatically instrument Vercel cron jobs
  automaticVercelMonitors: true,

  // Use `SENTRY_AUTH_TOKEN` environment variable
  authToken: process.env.SENTRY_AUTH_TOKEN,
});
