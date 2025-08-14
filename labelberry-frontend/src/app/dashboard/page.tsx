"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Activity, Printer, AlertCircle, CheckCircle, Clock, RefreshCw } from "lucide-react"
import { useState, useEffect } from "react"

interface DashboardStats {
  totalPrinters: number
  onlinePrinters: number
  totalJobsToday: number
  failedJobsToday: number
  avgPrintTime: number
  queueLength: number
}

interface PrinterStatus {
  id: string
  name: string
  status: "online" | "offline" | "error"
  ipAddress: string
  lastSeen: string
  jobsProcessed: number
  queueLength: number
}

interface PrinterData {
  id: string
  name?: string
  friendly_name?: string
  status: string
  ipAddress?: string
  ip_address?: string
  lastSeen?: string
  last_seen?: string
  metrics?: {
    jobsToday: number
  }
}

interface RecentJob {
  id: string
  printerName: string
  status: string
  createdAt: string
  completedAt?: string
  errorMessage?: string
  source: string
}

interface RecentAlert {
  type: 'error' | 'warning' | 'success'
  severity: 'high' | 'medium' | 'low'
  message: string
  printerName: string
  timestamp?: string
  icon: string
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalPrinters: 0,
    onlinePrinters: 0,
    totalJobsToday: 0,
    failedJobsToday: 0,
    avgPrintTime: 0,
    queueLength: 0
  })
  
  const [printers, setPrinters] = useState<PrinterStatus[]>([])
  const [recentJobs, setRecentJobs] = useState<RecentJob[]>([])
  const [recentAlerts, setRecentAlerts] = useState<RecentAlert[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      // Fetch stats
      const statsResponse = await fetch('/api/dashboard/stats')
      if (statsResponse.ok) {
        const statsResult = await statsResponse.json()
        if (statsResult.success && statsResult.data) {
          setStats(statsResult.data)
        }
      }

      // Fetch printers
      const printersResponse = await fetch('/api/pis')
      const printersResult = await printersResponse.json()
      const printersData = printersResult.data?.pis || []
      
      const formattedPrinters = printersData.map((printer: PrinterData) => ({
        id: printer.id,
        name: printer.friendly_name || printer.name,
        status: printer.status,
        ipAddress: printer.ip_address || printer.ipAddress || 'N/A',
        lastSeen: printer.last_seen ? new Date(printer.last_seen).toLocaleString() : 'Never',
        jobsProcessed: printer.metrics?.jobsToday || 0,
        queueLength: 0 // TODO: Calculate from queue
      }))
      
      setPrinters(formattedPrinters)
      
      // Fetch recent jobs
      const jobsResponse = await fetch('/api/recent-jobs?limit=50')
      if (jobsResponse.ok) {
        const jobsResult = await jobsResponse.json()
        if (jobsResult.success && jobsResult.data?.jobs) {
          setRecentJobs(jobsResult.data.jobs)
        }
      }
      
      // Fetch recent alerts
      const alertsResponse = await fetch('/api/recent-alerts?limit=10')
      if (alertsResponse.ok) {
        const alertsResult = await alertsResponse.json()
        if (alertsResult.success && alertsResult.data?.alerts) {
          setRecentAlerts(alertsResult.data.alerts)
        }
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "online":
        return <Badge className="bg-green-500">Online</Badge>
      case "offline":
        return <Badge variant="secondary">Offline</Badge>
      case "error":
        return <Badge variant="destructive">Error</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>
      
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="printers">Printers</TabsTrigger>
          <TabsTrigger value="recent">Recent Activity</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Printers</CardTitle>
                <Printer className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.totalPrinters}</div>
                <p className="text-xs text-muted-foreground">
                  {stats.onlinePrinters} online
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Jobs Today</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.totalJobsToday}</div>
                <p className="text-xs text-muted-foreground">
                  {stats.failedJobsToday} failed
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Print Time</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.avgPrintTime}ms</div>
                <p className="text-xs text-muted-foreground">
                  Per label
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Queue Length</CardTitle>
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.queueLength}</div>
                <p className="text-xs text-muted-foreground">
                  Pending jobs
                </p>
              </CardContent>
            </Card>
          </div>
          
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <Card className="col-span-4">
              <CardHeader>
                <CardTitle>Printer Status</CardTitle>
                <CardDescription>
                  Real-time status of all connected printers
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {printers.map((printer) => (
                    <div key={printer.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div>
                          <p className="text-sm font-medium">{printer.name}</p>
                          <p className="text-xs text-muted-foreground">{printer.ipAddress}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {printer.queueLength > 0 && (
                          <Badge variant="outline">{printer.queueLength} in queue</Badge>
                        )}
                        {getStatusBadge(printer.status)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            
            <Card className="col-span-3">
              <CardHeader>
                <CardTitle>Recent Alerts</CardTitle>
                <CardDescription>
                  System alerts and notifications
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recentAlerts.length > 0 ? (
                    recentAlerts.slice(0, 5).map((alert, index) => (
                      <div key={index} className="flex items-start space-x-2">
                        {alert.type === 'error' && <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />}
                        {alert.type === 'warning' && <AlertCircle className="h-4 w-4 text-yellow-500 mt-0.5" />}
                        {alert.type === 'success' && <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />}
                        <div>
                          <p className="text-sm font-medium">{alert.message}</p>
                          <p className="text-xs text-muted-foreground">
                            {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'Just now'}
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No recent alerts</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="printers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Printers</CardTitle>
              <CardDescription>
                Detailed view of all registered printers
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {printers.map((printer) => (
                  <Card key={printer.id}>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{printer.name}</h3>
                          <p className="text-sm text-muted-foreground">IP: {printer.ipAddress}</p>
                          <p className="text-sm text-muted-foreground">Last seen: {printer.lastSeen}</p>
                        </div>
                        <div className="text-right">
                          {getStatusBadge(printer.status)}
                          <p className="text-sm mt-2">Jobs today: {printer.jobsProcessed}</p>
                          <p className="text-sm">Queue: {printer.queueLength}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="recent" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Print Jobs</CardTitle>
              <CardDescription>
                Last 50 print jobs across all printers
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recentJobs.length > 0 ? (
                <div className="space-y-2">
                  {recentJobs.map((job) => (
                    <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <p className="text-sm font-medium">{job.printerName}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(job.createdAt).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge 
                          variant={
                            job.status === 'completed' ? 'default' :
                            job.status === 'failed' ? 'destructive' :
                            job.status === 'processing' ? 'secondary' :
                            'outline'
                          }
                        >
                          {job.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  No recent print jobs to display
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}