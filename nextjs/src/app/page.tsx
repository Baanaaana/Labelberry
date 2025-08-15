"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Plus, Settings, Trash2, TestTube, RefreshCw, Copy, CheckCircle, Printer, Activity, Clock, AlertCircle } from "lucide-react"
import { useState, useEffect } from "react"

interface DashboardStats {
  totalPrinters: number
  onlinePrinters: number
  totalJobsToday: number
  failedJobsToday: number
  avgPrintTime: number
  queueLength: number
}

interface PrinterDetails {
  id: string
  name: string
  deviceId: string
  apiKey: string
  status: "online" | "offline" | "error"
  ipAddress: string
  lastSeen: string
  deviceName?: string
  location?: string
  labelSize?: string
  configuration: {
    printerDevice: string
    labelSize: string
    autoReconnect: boolean
    maxQueueSize: number
  }
  metrics: {
    jobsToday: number
    failedJobs: number
    avgPrintTime: number
    uptime: string
  }
}

export default function PrintersPage() {
  const [printers, setPrinters] = useState<PrinterDetails[]>([])
  const [stats, setStats] = useState<DashboardStats>({
    totalPrinters: 0,
    onlinePrinters: 0,
    totalJobsToday: 0,
    failedJobsToday: 0,
    avgPrintTime: 0,
    queueLength: 0
  })
  const [serverIp, setServerIp] = useState<string>('')
  const [copied, setCopied] = useState(false)

  const [selectedPrinter, setSelectedPrinter] = useState<PrinterDetails | null>(null)
  const [configDialogOpen, setConfigDialogOpen] = useState(false)
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [printerToDelete, setPrinterToDelete] = useState<{ id: string; name: string } | null>(null)
  const [newPrinter, setNewPrinter] = useState({
    name: '',
    deviceId: '',
    apiKey: ''
  })
  const [editPrinterData, setEditPrinterData] = useState({
    friendlyName: '',
    deviceName: '',
    location: '',
    labelSize: 'standard'
  })

  const fetchPrinters = async () => {
    try {
      // Fetch printers
      const response = await fetch('/api/pis')
      const result = await response.json()
      const data = result.data?.pis || []
      
      // Fetch dashboard stats separately
      const statsResponse = await fetch('/api/dashboard-stats')
      let dashboardStats = null
      if (statsResponse.ok) {
        const statsResult = await statsResponse.json()
        dashboardStats = statsResult.data
      }
      
      const formattedPrinters = data.map((printer: {
        id: string
        friendly_name: string
        device_id: string
        api_key: string
        status: string
        ip_address?: string
        last_seen?: string
        printer_device?: string
        device_name?: string
        location?: string
        label_size?: string
        auto_reconnect?: boolean
        max_queue_size?: number
        metrics?: {
          jobsToday: number
          failedJobs: number
          avgPrintTime: number
          uptime: string
        }
      }) => ({
        id: printer.id,
        name: printer.friendly_name,
        deviceId: printer.device_id,
        apiKey: printer.api_key,
        status: printer.status,
        ipAddress: printer.ip_address || 'N/A',
        lastSeen: printer.last_seen ? new Date(printer.last_seen).toLocaleString() : 'Never',
        deviceName: printer.device_name,
        location: printer.location,
        labelSize: printer.label_size,
        configuration: {
          printerDevice: printer.printer_device || "/dev/usb/lp0",
          labelSize: printer.label_size || "4x6",
          autoReconnect: printer.auto_reconnect !== undefined ? printer.auto_reconnect : true,
          maxQueueSize: printer.max_queue_size || 100,
        },
        metrics: printer.metrics || {
          jobsToday: 0,
          failedJobs: 0,
          avgPrintTime: 0,
          uptime: "0 days"
        }
      }))
      
      setPrinters(formattedPrinters)
      
      // Use dashboard stats if available, otherwise calculate from printer data
      if (dashboardStats) {
        setStats({
          totalPrinters: dashboardStats.totalPrinters || formattedPrinters.length,
          onlinePrinters: dashboardStats.onlinePrinters || formattedPrinters.filter((p: PrinterDetails) => p.status === "online").length,
          totalJobsToday: dashboardStats.totalJobsToday || 0,
          failedJobsToday: dashboardStats.failedJobsToday || 0,
          avgPrintTime: dashboardStats.avgPrintTime || 0,
          queueLength: dashboardStats.queueLength || 0
        })
      } else {
        // Fallback to calculating from printer data
        const onlinePrinters = formattedPrinters.filter((p: PrinterDetails) => p.status === "online").length
        const totalJobsToday = formattedPrinters.reduce((acc: number, p: PrinterDetails) => acc + (p.metrics?.jobsToday || 0), 0)
        const failedJobsToday = formattedPrinters.reduce((acc: number, p: PrinterDetails) => acc + (p.metrics?.failedJobs || 0), 0)
        
        setStats({
          totalPrinters: formattedPrinters.length,
          onlinePrinters,
          totalJobsToday,
          failedJobsToday,
          avgPrintTime: 0,
          queueLength: 0
        })
      }
    } catch (error) {
      console.error('Failed to fetch printers:', error)
    }
  }

  useEffect(() => {
    fetchPrinters()
    fetchServerIp()
  }, [])

  const fetchServerIp = async () => {
    try {
      // Get the current hostname/IP from the browser
      const hostname = window.location.hostname
      
      // If it's localhost, try to get the actual network IP
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        // Fetch the actual server IP from our API
        const response = await fetch('/api/server-info')
        if (response.ok) {
          const data = await response.json()
          setServerIp(data.ip || 'YOUR_SERVER_IP')
        } else {
          setServerIp('YOUR_SERVER_IP')
        }
      } else {
        // If accessed via network IP or domain, use that
        setServerIp(hostname)
      }
    } catch (error) {
      console.error('Failed to determine server IP:', error)
      setServerIp('YOUR_SERVER_IP')
    }
  }

  const copyServerUrl = () => {
    const url = serverIp === 'YOUR_SERVER_IP' 
      ? 'http://YOUR_SERVER_IP:8080' 
      : `http://${serverIp}:8080`
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
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

  const pollJobStatus = async (jobId: string, printerName: string) => {
    let attempts = 0
    const maxAttempts = 15 // Poll for up to 15 seconds
    
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}/status`)
        if (response.ok) {
          const result = await response.json()
          if (result.data?.status === 'completed') {
            toast.success(`Print job completed successfully on ${printerName}!`, {
              duration: 5000,
              icon: '🎉'
            })
            return true
          } else if (result.data?.status === 'failed') {
            toast.error(`Print job failed on ${printerName}`)
            return true
          }
        }
      } catch (error) {
        console.error('Error polling job status:', error)
      }
      
      attempts++
      if (attempts < maxAttempts) {
        setTimeout(checkStatus, 1000) // Check every second
      }
      return false
    }
    
    setTimeout(checkStatus, 2000) // Start checking after 2 seconds
  }

  const handleTestPrint = async (printerId: string) => {
    try {
      const response = await fetch(`/api/pis/${printerId}/test-print`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}) // Empty body will use default test label
      })
      
      if (response.ok) {
        const result = await response.json()
        const printer = printers.find(p => p.id === printerId)
        const printerName = printer?.name || 'Printer'
        
        toast.success(result.message || 'Test print sent successfully!')
        
        // Start polling for job completion if we have a job ID
        if (result.data?.job_id) {
          pollJobStatus(result.data.job_id, printerName)
        }
      } else {
        const error = await response.json().catch(() => null)
        toast.error(`Failed to send test print: ${error?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to send test print:', error)
      toast.error('Failed to send test print. Please check the console for details.')
    }
  }

  const handleDeleteClick = (printerId: string, printerName: string) => {
    setPrinterToDelete({ id: printerId, name: printerName })
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!printerToDelete) return
    
    try {
      const response = await fetch(`/api/pis/${printerToDelete.id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // Successfully deleted, update the UI
        setPrinters(printers.filter(p => p.id !== printerToDelete.id))
        setDeleteDialogOpen(false)
        setPrinterToDelete(null)
        toast.success(`Printer "${printerToDelete.name}" deleted successfully`)
      } else {
        // Handle error response
        const errorData = await response.json().catch(() => null)
        console.error('Failed to delete printer:', response.status, errorData)
        toast.error(`Failed to delete printer: ${errorData?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to delete printer:', error)
      toast.error('Failed to delete printer. Please check the console for details.')
    }
  }

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setPrinterToDelete(null)
  }

  const handleRefresh = () => {
    fetchPrinters()
  }

  const handleEditPrinter = (printer: PrinterDetails) => {
    // Always get the latest printer data from the list
    const currentPrinter = printers.find(p => p.id === printer.id) || printer
    setSelectedPrinter(currentPrinter)
    setEditPrinterData({
      friendlyName: currentPrinter.name,
      deviceName: currentPrinter.deviceName || currentPrinter.deviceId.split('-')[0].toUpperCase() || 'PI-2025',
      location: currentPrinter.location || '',
      labelSize: currentPrinter.labelSize || 'standard'
    })
    setConfigDialogOpen(true)
  }


  const handleSaveEditPrinter = async () => {
    if (!selectedPrinter) return
    
    try {
      const updateData = {
        friendly_name: editPrinterData.friendlyName,
        device_name: editPrinterData.deviceName,
        location: editPrinterData.location,
        label_size: editPrinterData.labelSize
      }
      console.log('Sending update:', updateData, 'to printer ID:', selectedPrinter.id)
      
      const response = await fetch(`/api/pis/${selectedPrinter.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData)
      })
      
      if (response.ok) {
        // Close dialog first
        setConfigDialogOpen(false)
        setSelectedPrinter(null)
        
        // Show success message
        toast.success(`Printer "${editPrinterData.friendlyName}" updated successfully`)
        
        // Refresh the printers list from server to get the updated data
        await fetchPrinters()
      } else {
        const error = await response.json().catch(() => null)
        toast.error(`Failed to update printer: ${error?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to update printer:', error)
      toast.error('Failed to update printer. Please check the console for details.')
    }
  }

  const handleAddPrinter = async () => {
    try {
      const response = await fetch('/api/pis/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: newPrinter.deviceId,  // Changed from device_id to id
          friendly_name: newPrinter.name,
          api_key: newPrinter.apiKey,
          printer_model: 'Zebra'  // Optional, but good to have
        })
      })
      
      if (response.ok) {
        // Close dialog and refresh list
        setAddDialogOpen(false)
        setNewPrinter({ name: '', deviceId: '', apiKey: '' })
        fetchPrinters()
        toast.success(`Printer "${newPrinter.name}" added successfully`)
      } else {
        const error = await response.json()
        toast.error(`Failed to add printer: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to add printer:', error)
      toast.error('Failed to add printer. Please check the console for details.')
    }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Printers</h2>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Printer
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Printer</DialogTitle>
                <DialogDescription>
                  Register a new Raspberry Pi printer to the system. You can enter the Device ID and API Key from your Pi installation.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="name" className="text-right">
                    Name
                  </Label>
                  <Input 
                    id="name" 
                    className="col-span-3" 
                    placeholder="e.g., Pi Rene" 
                    value={newPrinter.name}
                    onChange={(e) => setNewPrinter({...newPrinter, name: e.target.value})}
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="device-id" className="text-right">
                    Device ID
                  </Label>
                  <Input 
                    id="device-id" 
                    className="col-span-3" 
                    placeholder="e.g., feb9fba3-bcdd-4990-8d89-62ecd33c7efd" 
                    value={newPrinter.deviceId}
                    onChange={(e) => setNewPrinter({...newPrinter, deviceId: e.target.value})}
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="api-key" className="text-right">
                    API Key
                  </Label>
                  <Input 
                    id="api-key" 
                    className="col-span-3" 
                    placeholder="e.g., 0ce5717b-c7ee-4274-8e38-a1525968b036" 
                    value={newPrinter.apiKey}
                    onChange={(e) => setNewPrinter({...newPrinter, apiKey: e.target.value})}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddPrinter}>Add Printer</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Metrics Section */}
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
            <div className="text-2xl font-bold">
              {stats.avgPrintTime > 0 ? `${(stats.avgPrintTime / 1000).toFixed(1)}s` : '-'}
            </div>
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

      <Card>
        <CardHeader>
          <CardTitle>Server Configuration</CardTitle>
          <CardDescription>
            Use this server address when installing LabelBerry on a Raspberry Pi
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <code className="flex-1 px-3 py-2 bg-muted rounded-md font-mono text-sm">
              {serverIp === 'YOUR_SERVER_IP' 
                ? 'http://YOUR_SERVER_IP:8080' 
                : `http://${serverIp}:8080`}
            </code>
            <Button
              variant="outline"
              size="sm"
              onClick={copyServerUrl}
              className="shrink-0"
            >
              {copied ? (
                <>
                  <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy
                </>
              )}
            </Button>
          </div>
          {serverIp === 'YOUR_SERVER_IP' && (
            <p className="text-sm text-muted-foreground mt-2">
              To find your server&apos;s IP address, run: <code className="text-xs bg-muted px-1 py-0.5 rounded">hostname -I</code> on the server
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>All Printers</CardTitle>
            <CardDescription>
              Manage and configure all registered printers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Device ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead>Jobs Today</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {printers.map((printer) => (
                  <TableRow key={printer.id}>
                    <TableCell className="font-medium">{printer.name}</TableCell>
                    <TableCell>{printer.deviceId}</TableCell>
                    <TableCell>{getStatusBadge(printer.status)}</TableCell>
                    <TableCell>{printer.ipAddress}</TableCell>
                    <TableCell>{printer.lastSeen}</TableCell>
                    <TableCell>{printer.metrics.jobsToday}</TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditPrinter(printer)}
                          title="Edit Printer"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTestPrint(printer.id)}
                          title="Test Print"
                        >
                          <TestTube className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteClick(printer.id, printer.name)}
                          title="Delete Printer"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {selectedPrinter && (
          <Dialog open={configDialogOpen} onOpenChange={(open) => {
            setConfigDialogOpen(open)
            // Reset edit data when dialog is closed
            if (!open) {
              setSelectedPrinter(null)
            }
          }}>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Edit Printer</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="friendly-name">Friendly Name</Label>
                  <Input
                    id="friendly-name"
                    value={editPrinterData.friendlyName}
                    onChange={(e) => setEditPrinterData({...editPrinterData, friendlyName: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="device-name">Device Name</Label>
                  <Input
                    id="device-name"
                    value={editPrinterData.deviceName}
                    onChange={(e) => setEditPrinterData({...editPrinterData, deviceName: e.target.value})}
                    placeholder="e.g., PI-2025"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="location">Location</Label>
                  <Input
                    id="location"
                    value={editPrinterData.location}
                    onChange={(e) => setEditPrinterData({...editPrinterData, location: e.target.value})}
                    placeholder="e.g., Kantoor"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="label-size">Label Size</Label>
                  <Select 
                    value={editPrinterData.labelSize}
                    onValueChange={(value) => setEditPrinterData({...editPrinterData, labelSize: value})}
                  >
                    <SelectTrigger id="label-size">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="standard">Standard (57mm x 32mm)</SelectItem>
                      <SelectItem value="large">Large (102mm x 152mm)</SelectItem>
                      <SelectItem value="small">Small (25mm x 25mm)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setConfigDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSaveEditPrinter}>Save Changes</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirm Deletion</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete printer &quot;{printerToDelete?.name}&quot;? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={handleCancelDelete}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleConfirmDelete}>
                Delete Printer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </div>
  )
}