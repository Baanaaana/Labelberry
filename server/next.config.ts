import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // In production, this should be handled by your reverse proxy (nginx)
    // These rewrites are primarily for local development
    const apiUrl = 'http://localhost:8080';
      
    return [
      {
        source: '/api/:path((?!auth).*)',  // Match /api/* except /api/auth
        destination: `${apiUrl}/:path*`, // Proxy to FastAPI backend (without /api prefix)
      },
      {
        source: '/docs',
        destination: `${apiUrl}/docs`, // Proxy to FastAPI docs
      },
      {
        source: '/redoc',
        destination: `${apiUrl}/redoc`, // Proxy to FastAPI redoc
      },
    ];
  },
};

export default nextConfig;
