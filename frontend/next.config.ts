import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      // The MCP JSON-RPC server is mounted at the backend root, outside /api.
      { source: "/mcp", destination: `${api}/mcp` },
      { source: "/backend/:path*", destination: `${api}/:path*` },
    ];
  },
};

export default nextConfig;
