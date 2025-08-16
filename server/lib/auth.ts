import { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null
        }

        try {
          // For server-side auth, we need to call the FastAPI backend directly
          // Using localhost since both services run on the same server
          const apiUrl = 'http://localhost:8080'
          const loginUrl = `${apiUrl}/auth/login`
          
          console.log('[Auth] Attempting login to:', loginUrl)
          
          const response = await fetch(loginUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
            }),
          })

          console.log('[Auth] Response status:', response.status)

          if (!response.ok) {
            const errorText = await response.text()
            console.error('[Auth] Failed:', response.status, response.statusText, errorText)
            return null
          }

          const data = await response.json()
          console.log('[Auth] Response data:', data)
          
          if (data.success && data.data?.user) {
            return {
              id: data.data.user.id || '1',
              name: data.data.user.username,
              email: data.data.user.email || `${data.data.user.username}@labelberry.local`,
            }
          }

          return null
        } catch (error) {
          console.error('[Auth] Exception:', error)
          console.error('[Auth] Error details:', {
            message: error instanceof Error ? error.message : 'Unknown error',
            stack: error instanceof Error ? error.stack : undefined
          })
          return null
        }
      }
    })
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  pages: {
    signIn: "/login",
    error: "/login", // Redirect errors to login page
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.name = user.name
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string
        session.user.name = token.name as string
      }
      return session
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
}