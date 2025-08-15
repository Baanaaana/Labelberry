// API configuration utility
export function getApiUrl(): string {
  // In production with Nginx path-based routing, the API is at /api
  // The browser will automatically use the current domain
  if (typeof window !== 'undefined') {
    // Client-side: use relative path for Nginx routing
    const baseUrl = window.location.origin
    
    // If we're using path-based routing (production), use /api
    // If we're in development (localhost:3000), use the backend URL
    if (baseUrl.includes('localhost:3000')) {
      return 'http://localhost:8080/api'
    }
    
    // Production: use relative path which Nginx will route
    return '/api'
  }
  
  // Server-side: use environment variable or default
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api'
}

export async function apiRequest(endpoint: string, options?: RequestInit) {
  const apiUrl = getApiUrl()
  const url = `${apiUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`
  
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
}