import type { NextConfig } from "next";

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

export default nextConfig;
