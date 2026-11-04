import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // In development, proxy API calls to the local FastAPI server (same-origin cookies).
  // In production Nginx routes /api to the API container.
  async rewrites() {
    return process.env.NODE_ENV === "development"
      ? [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }]
      : [];
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
