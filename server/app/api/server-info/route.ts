import { NextResponse } from 'next/server'
import os from 'os'

export async function GET() {
  try {
    const networkInterfaces = os.networkInterfaces()
    const addresses: string[] = []

    // Get all IPv4 addresses that are not internal
    for (const name of Object.keys(networkInterfaces)) {
      const interfaces = networkInterfaces[name]
      if (interfaces) {
        for (const iface of interfaces) {
          // Skip internal (i.e., 127.0.0.1) and non-IPv4 addresses
          if (iface.family === 'IPv4' && !iface.internal) {
            addresses.push(iface.address)
          }
        }
      }
    }

    // Return the first non-internal IP address found
    const serverIp = addresses[0] || 'localhost'

    return NextResponse.json({
      ip: serverIp,
      allIps: addresses,
      hostname: os.hostname()
    })
  } catch (error) {
    console.error('Failed to get server IP:', error)
    return NextResponse.json({ 
      ip: 'localhost',
      error: 'Failed to determine server IP'
    })
  }
}