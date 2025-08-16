import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // In production, this should be handled by your reverse proxy (nginx)
    // These rewrites are primarily for local development
    const apiUrl = 'http://localhost:8080';
      
    return [
      {
        source: '/fastapi/:path*',
        destination: `${apiUrl}/fastapi/:path*`, // Proxy to FastAPI backend
      },
      {
        source: '/docs',
        destination: `${apiUrl}/fastapi/docs`, // Proxy to FastAPI docs
      },
      {
        source: '/redoc',
        destination: `${apiUrl}/fastapi/redoc`, // Proxy to FastAPI redoc
      },
    ];
  },
};

export default nextConfig;
