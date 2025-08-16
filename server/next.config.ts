import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // In production, this should be handled by your reverse proxy (nginx)
    // These rewrites are primarily for local development
    const apiUrl = process.env.NEXT_PUBLIC_API_URL === '/api' 
      ? 'http://localhost:8080'  // Local backend server
      : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`, // Proxy to FastAPI backend
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
