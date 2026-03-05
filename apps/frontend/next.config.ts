import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Prevent webpack from trying to bundle undici — it is a transitive
  // dependency of Next.js and is available at runtime, but is not listed in
  // the app's package.json, so the bundler cannot resolve it at compile time.
  // Used by instrumentation.ts to set up an HTTP proxy for Node.js fetch.
  serverExternalPackages: ["undici"],
};

export default nextConfig;
