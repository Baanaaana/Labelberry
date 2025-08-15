"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Activity, Printer, AlertCircle, CheckCircle, Clock, RefreshCw, X, RotateCcw, Trash2 } from "lucide-react"
import { useState, useEffect } from "react"
import { toast } from "sonner"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

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
  const [showClearHistoryDialog, setShowClearHistoryDialog] = useState(false)

  const handleCancelJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/cancel`, {
        method: 'POST'
      })
      
      if (response.ok) {
        toast.success('Job cancelled successfully')
        fetchData() // Refresh the data
      } else {
        const error = await response.json().catch(() => null)
        toast.error(`Failed to cancel job: ${error?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to cancel job:', error)
      toast.error('Failed to cancel job')
    }
  }

  const handleRetryJob = async (jobId: string) => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/retry`, {
        method: 'POST'
      })
      
      if (response.ok) {
        toast.success('Job restarted successfully')
        fetchData() // Refresh the data
      } else {
        const error = await response.json().catch(() => null)
        toast.error(`Failed to retry job: ${error?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to retry job:', error)
      toast.error('Failed to retry job')
    }
  }

  const handleClearStuckJobs = async () => {
    try {
      // Find all stuck pending jobs (older than 5 minutes)
      const stuckJobs = recentJobs.filter(job => {
        if (job.status !== 'pending') return false
        const jobAge = Date.now() - new Date(job.createdAt).getTime()
        return jobAge > 5 * 60 * 1000 // 5 minutes
      })
      
      if (stuckJobs.length === 0) {
        toast.info('No stuck jobs found')
        return
      }
      
      // Cancel all stuck jobs
      const promises = stuckJobs.map(job => 
        fetch(`/api/jobs/${job.id}/cancel`, { method: 'POST' })
      )
      
      await Promise.all(promises)
      toast.success(`Cleared ${stuckJobs.length} stuck job(s)`)
      fetchData() // Refresh the data
    } catch (error) {
      console.error('Failed to clear stuck jobs:', error)
      toast.error('Failed to clear stuck jobs')
    }
  }

  const handleClearHistory = async () => {
    try {
      const response = await fetch('/api/jobs/clear-history', {
        method: 'DELETE'
      })
      
      if (response.ok) {
        const result = await response.json()
        toast.success(result.message || 'Print history cleared successfully')
        setRecentJobs([]) // Clear the local state immediately
        fetchData() // Refresh all data
      } else {
        const error = await response.json().catch(() => null)
        toast.error(`Failed to clear history: ${error?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to clear history:', error)
      toast.error('Failed to clear print history')
    } finally {
      setShowClearHistoryDialog(false)
    }
  }

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
      
      {/* Overview Section */}
      <div className="space-y-4">
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
      </div>
      
      {/* Recent Activity Section */}
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Print Jobs</CardTitle>
                <CardDescription>
                  Last 50 print jobs across all printers
                </CardDescription>
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearStuckJobs}
                  title="Clear all pending jobs older than 5 minutes"
                >
                  Clear Stuck Jobs
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowClearHistoryDialog(true)}
                  title="Clear all print history"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear History
                </Button>
              </div>
            </div>
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
                        {/* Retry button for failed or cancelled jobs */}
                        {(job.status === 'failed' || job.status === 'cancelled') && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRetryJob(job.id)}
                            title="Retry job"
                          >
                            <RotateCcw className="h-4 w-4" />
                          </Button>
                        )}
                        {/* Cancel button only for pending or processing jobs */}
                        {(job.status === 'pending' || job.status === 'processing') && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCancelJob(job.id)}
                            title="Cancel job"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
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
      </div>

      <AlertDialog open={showClearHistoryDialog} onOpenChange={setShowClearHistoryDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear Print History</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to clear all print job history? This action cannot be undone and will permanently delete all print job records from the database.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleClearHistory} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Clear All History
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}