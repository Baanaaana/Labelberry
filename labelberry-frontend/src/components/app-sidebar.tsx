"use client"

import {
  Home,
  Printer,
  Settings,
  List,
  Key,
  BarChart,
  LogOut,
  Circle,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useState, useEffect } from "react"

const menuItems = [
  {
    title: "Dashboard",
    url: "/dashboard",
    icon: Home,
  },
  {
    title: "Printers",
    url: "/printers",
    icon: Printer,
  },
  {
    title: "Queue Management",
    url: "/queue",
    icon: List,
  },
  {
    title: "Performance",
    url: "/performance",
    icon: BarChart,
  },
]

const settingsItems = [
  {
    title: "System Settings",
    url: "/settings",
    icon: Settings,
  },
  {
    title: "API Keys",
    url: "/settings/api-keys",
    icon: Key,
  },
]

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [mqttStatus, setMqttStatus] = useState<'connected' | 'disconnected' | 'error' | 'checking'>('checking')

  useEffect(() => {
    // Check MQTT status on mount
    checkMqttStatus()
    
    // Set up polling to check status every 10 seconds
    const interval = setInterval(() => {
      checkMqttStatus()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const checkMqttStatus = async () => {
    try {
      const response = await fetch('/api/mqtt-status')
      if (response.ok) {
        const result = await response.json()
        // The API returns { success, message, data: { connected, broker } }
        const isConnected = result.data?.connected || false
        setMqttStatus(isConnected ? 'connected' : 'disconnected')
      } else {
        setMqttStatus('error')
      }
    } catch {
      setMqttStatus('error')
    }
  }

  const getStatusColor = () => {
    switch (mqttStatus) {
      case 'connected':
        return 'text-green-500'
      case 'disconnected':
        return 'text-red-500'
      case 'error':
        return 'text-yellow-500'
      case 'checking':
        return 'text-gray-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusTooltip = () => {
    switch (mqttStatus) {
      case 'connected':
        return 'MQTT Broker Connected'
      case 'disconnected':
        return 'MQTT Broker Disconnected'
      case 'error':
        return 'MQTT Connection Error'
      case 'checking':
        return 'Checking MQTT Status...'
      default:
        return 'Unknown Status'
    }
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-2">
            <Printer className="h-6 w-6" />
            <span className="font-bold text-xl">LabelBerry</span>
          </div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button 
                  onClick={() => router.push('/settings')}
                  className="relative p-1 -m-1 rounded hover:bg-accent/50 transition-colors"
                >
                  <Circle 
                    className={`h-3 w-3 ${getStatusColor()} fill-current transition-colors duration-300`}
                  />
                  {(mqttStatus === 'checking' || mqttStatus === 'error') && (
                    <Circle 
                      className={`absolute top-0 left-0 h-3 w-3 ${getStatusColor()} animate-ping`}
                    />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-sm font-medium">{getStatusTooltip()}</p>
                <p className="text-xs text-muted-foreground">Click to configure MQTT settings</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Main</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={pathname === item.url}>
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Settings</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {settingsItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={pathname === item.url}>
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <button className="w-full">
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}