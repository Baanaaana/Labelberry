"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { RefreshCw, Activity, Cpu, HardDrive, CheckCircle } from "lucide-react"
import { useState, useEffect } from "react"

interface PiMetrics {
  id: string
  deviceId: string
  name: string
  status: string
  cpuUsage: number
  memoryUsage: number
  queueSize: number
  jobsCompleted: number
  jobsFailed: number
  uptime: number
  lastUpdate: string
  ipAddress?: string
  printerModel?: string
}

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<PiMetrics[]>([])
  const [selectedPi, setSelectedPi] = useState<string>("all")
  const [timeRange, setTimeRange] = useState<string>("24h")
  const [loading, setLoading] = useState(true)
  const [selectedMetrics, setSelectedMetrics] = useState<PiMetrics | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const fetchMetrics = async () => {
    try {
      // Fetch all Pi devices with their latest metrics
      const response = await fetch('/api/pis')
      const result = await response.json()
      const pis = result.data?.pis || []
      
      // Fetch metrics for each Pi
      const metricsPromises = pis.map(async (pi: {
        id: string
        device_id: string
        friendly_name?: string
        status?: string
        last_seen?: string
        ip_address?: string
        printer_model?: string
      }) => {
        const metricsResponse = await fetch(`/api/metrics/${pi.id}?timeRange=${timeRange}`)
        let latestMetrics = null
        
        if (metricsResponse.ok) {
          const metricsResult = await metricsResponse.json()
          const metricsData = metricsResult.data?.metrics || []
          if (metricsData.length > 0) {
            latestMetrics = metricsData[0] // Get the most recent metrics
          }
        }
        
        return {
          id: pi.id,
          deviceId: pi.device_id,
          name: pi.friendly_name || 'Unknown',
          status: pi.status || 'offline',
          cpuUsage: latestMetrics?.cpu_usage || 0,
          memoryUsage: latestMetrics?.memory_usage || 0,
          queueSize: latestMetrics?.queue_size || 0,
          jobsCompleted: latestMetrics?.jobs_processed || 0,
          jobsFailed: latestMetrics?.jobs_failed || 0,
          uptime: latestMetrics?.uptime || 0,
          lastUpdate: latestMetrics?.created_at || pi.last_seen || new Date().toISOString(),
          ipAddress: pi.ip_address,
          printerModel: pi.printer_model
        }
      })
      
      const allMetrics = await Promise.all(metricsPromises)
      setMetrics(allMetrics)
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange])

  const handleRefresh = () => {
    setLoading(true)
    fetchMetrics()
  }

  const handleShowDetails = (pi: PiMetrics) => {
    setSelectedMetrics(pi)
    setDialogOpen(true)
  }

  // Calculate aggregated metrics
  const filteredMetrics = selectedPi === "all" 
    ? metrics 
    : metrics.filter(m => m.id === selectedPi)

  const aggregatedMetrics = {
    avgCpu: filteredMetrics.reduce((acc, m) => acc + m.cpuUsage, 0) / (filteredMetrics.length || 1),
    avgMemory: filteredMetrics.reduce((acc, m) => acc + m.memoryUsage, 0) / (filteredMetrics.length || 1),
    totalJobs: filteredMetrics.reduce((acc, m) => acc + m.jobsCompleted + m.jobsFailed, 0),
    successRate: filteredMetrics.reduce((acc, m) => {
      const total = m.jobsCompleted + m.jobsFailed
      return total > 0 ? acc + (m.jobsCompleted / total * 100) : acc
    }, 0) / (filteredMetrics.length || 1)
  }

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

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else {
      return `${minutes}m`
    }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Performance Metrics</h2>
        <div className="flex items-center space-x-2">
          <Select value={selectedPi} onValueChange={setSelectedPi}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Printers</SelectItem>
              {metrics.map((pi) => (
                <SelectItem key={pi.id} value={pi.id}>
                  {pi.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg CPU Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{aggregatedMetrics.avgCpu.toFixed(1)}%</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Memory</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{aggregatedMetrics.avgMemory.toFixed(1)}%</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{aggregatedMetrics.totalJobs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{aggregatedMetrics.successRate.toFixed(1)}%</div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Metrics Table */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Metrics</CardTitle>
          <CardDescription>
            Real-time performance metrics for all Raspberry Pi devices
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Printer</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>CPU %</TableHead>
                <TableHead>Memory %</TableHead>
                <TableHead>Queue</TableHead>
                <TableHead>Jobs</TableHead>
                <TableHead>Failed</TableHead>
                <TableHead>Uptime</TableHead>
                <TableHead>Last Update</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMetrics.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground">
                    No metrics data available
                  </TableCell>
                </TableRow>
              ) : (
                filteredMetrics.map((pi) => (
                  <TableRow key={pi.id}>
                    <TableCell className="font-medium">{pi.name}</TableCell>
                    <TableCell>{getStatusBadge(pi.status)}</TableCell>
                    <TableCell>
                      <span className={pi.cpuUsage > 80 ? "text-red-600 font-semibold" : ""}>
                        {pi.cpuUsage.toFixed(1)}%
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className={pi.memoryUsage > 80 ? "text-red-600 font-semibold" : ""}>
                        {pi.memoryUsage.toFixed(1)}%
                      </span>
                    </TableCell>
                    <TableCell>{pi.queueSize}</TableCell>
                    <TableCell>{pi.jobsCompleted}</TableCell>
                    <TableCell>
                      {pi.jobsFailed > 0 && (
                        <span className="text-red-600">{pi.jobsFailed}</span>
                      )}
                      {pi.jobsFailed === 0 && <span className="text-green-600">0</span>}
                    </TableCell>
                    <TableCell>{formatUptime(pi.uptime)}</TableCell>
                    <TableCell>{new Date(pi.lastUpdate).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleShowDetails(pi)}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Details Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Performance Details - {selectedMetrics?.name}</DialogTitle>
            <DialogDescription>
              Detailed performance metrics and system information
            </DialogDescription>
          </DialogHeader>
          {selectedMetrics && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Device ID</p>
                  <p className="text-sm">{selectedMetrics.deviceId}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">IP Address</p>
                  <p className="text-sm">{selectedMetrics.ipAddress || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Printer Model</p>
                  <p className="text-sm">{selectedMetrics.printerModel || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Status</p>
                  <div className="text-sm">{getStatusBadge(selectedMetrics.status)}</div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold">System Resources</h4>
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">CPU Usage</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{selectedMetrics.cpuUsage.toFixed(1)}%</div>
                      <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${selectedMetrics.cpuUsage > 80 ? 'bg-red-500' : 'bg-blue-500'}`}
                          style={{ width: `${selectedMetrics.cpuUsage}%` }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Memory Usage</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{selectedMetrics.memoryUsage.toFixed(1)}%</div>
                      <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${selectedMetrics.memoryUsage > 80 ? 'bg-red-500' : 'bg-purple-500'}`}
                          style={{ width: `${selectedMetrics.memoryUsage}%` }}
                        />
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold">Print Statistics</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Jobs Completed</p>
                    <p className="text-xl font-bold text-green-600">{selectedMetrics.jobsCompleted}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Jobs Failed</p>
                    <p className="text-xl font-bold text-red-600">{selectedMetrics.jobsFailed}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Queue Size</p>
                    <p className="text-xl font-bold">{selectedMetrics.queueSize}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold">System Uptime</h4>
                <p className="text-sm">{formatUptime(selectedMetrics.uptime)}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}