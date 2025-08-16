// API configuration utility
export function getApiUrl(): string {
  if (typeof window !== 'undefined') {
    // Client-side
    const host = window.location.hostname
    
    // Development: localhost
    if (host === 'localhost') {
      return 'http://localhost:8080/fastapi'
    }
    
    // Production: use /fastapi path (Nginx will route this)
    return '/fastapi'
  }
  
  // Server-side fallback
  return '/fastapi'
}

export async function apiRequest(endpoint: string, options?: RequestInit) {
  const apiUrl = getApiUrl()
  // Ensure endpoint starts with /
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const url = `${apiUrl}${path}`
  
  console.log('API Request:', url) // Debug logging
  
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
}