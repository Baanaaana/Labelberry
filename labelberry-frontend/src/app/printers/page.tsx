"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
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
import { Plus, Settings, Trash2, TestTube, RefreshCw, Copy, CheckCircle } from "lucide-react"
import { useState, useEffect } from "react"

interface PrinterDetails {
  id: string
  name: string
  deviceId: string
  apiKey: string
  status: "online" | "offline" | "error"
  ipAddress: string
  lastSeen: string
  configuration: {
    printerDevice: string
    labelSize: string
    defaultDarkness: number
    defaultSpeed: number
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

interface PrinterApiData {
  id: string
  name: string
  deviceId: string
  apiKey: string
  status: string
  ipAddress?: string
  lastSeen?: string
  configuration?: PrinterDetails['configuration']
  metrics?: PrinterDetails['metrics']
}

export default function PrintersPage() {
  const [printers, setPrinters] = useState<PrinterDetails[]>([])
  const [serverIp, setServerIp] = useState<string>('')
  const [copied, setCopied] = useState(false)

  const [selectedPrinter, setSelectedPrinter] = useState<PrinterDetails | null>(null)
  const [configDialogOpen, setConfigDialogOpen] = useState(false)

  const fetchPrinters = async () => {
    try {
      const response = await fetch('/api/pis')
      const result = await response.json()
      const data = result.data?.pis || []
      
      const formattedPrinters = data.map((printer: PrinterApiData) => ({
        id: printer.id,
        name: printer.name,
        deviceId: printer.deviceId,
        apiKey: printer.apiKey,
        status: printer.status,
        ipAddress: printer.ipAddress || 'N/A',
        lastSeen: printer.lastSeen ? new Date(printer.lastSeen).toLocaleString() : 'Never',
        configuration: printer.configuration || {
          printerDevice: "/dev/usb/lp0",
          labelSize: "4x6",
          defaultDarkness: 15,
          defaultSpeed: 4,
          autoReconnect: true,
          maxQueueSize: 100
        },
        metrics: printer.metrics || {
          jobsToday: 0,
          failedJobs: 0,
          avgPrintTime: 0,
          uptime: "0 days"
        }
      }))
      
      setPrinters(formattedPrinters)
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

  const handleTestPrint = (printerId: string) => {
    console.log(`Testing printer ${printerId}`)
    // Add test print logic here
  }

  const handleDeletePrinter = async (printerId: string) => {
    try {
      const response = await fetch(`/api/pis/${printerId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // Successfully deleted, update the UI
        setPrinters(printers.filter(p => p.id !== printerId))
      } else {
        // Handle error response
        const errorData = await response.json().catch(() => null)
        console.error('Failed to delete printer:', response.status, errorData)
        alert(`Failed to delete printer: ${errorData?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to delete printer:', error)
      alert('Failed to delete printer. Please check the console for details.')
    }
  }

  const handleRefresh = () => {
    fetchPrinters()
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
          <Dialog>
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
                  Register a new Raspberry Pi printer to the system
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="name" className="text-right">
                    Name
                  </Label>
                  <Input id="name" className="col-span-3" placeholder="e.g., Warehouse A - Station 1" />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="device-id" className="text-right">
                    Device ID
                  </Label>
                  <Input id="device-id" className="col-span-3" placeholder="Will be auto-generated" disabled />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="api-key" className="text-right">
                    API Key
                  </Label>
                  <Input id="api-key" className="col-span-3" placeholder="Will be auto-generated" disabled />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit">Add Printer</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
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
                          onClick={() => {
                            setSelectedPrinter(printer)
                            setConfigDialogOpen(true)
                          }}
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTestPrint(printer.id)}
                        >
                          <TestTube className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeletePrinter(printer.id)}
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
          <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Configure {selectedPrinter.name}</DialogTitle>
                <DialogDescription>
                  Update printer configuration and settings
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="printer-name" className="text-right">
                    Name
                  </Label>
                  <Input
                    id="printer-name"
                    className="col-span-3"
                    defaultValue={selectedPrinter.name}
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="printer-device" className="text-right">
                    Device
                  </Label>
                  <Input
                    id="printer-device"
                    className="col-span-3"
                    defaultValue={selectedPrinter.configuration.printerDevice}
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="label-size" className="text-right">
                    Label Size
                  </Label>
                  <Select defaultValue={selectedPrinter.configuration.labelSize}>
                    <SelectTrigger className="col-span-3">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="4x6">4x6 inches</SelectItem>
                      <SelectItem value="4x4">4x4 inches</SelectItem>
                      <SelectItem value="2x1">2x1 inches</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="darkness" className="text-right">
                    Darkness
                  </Label>
                  <Input
                    id="darkness"
                    type="number"
                    className="col-span-3"
                    defaultValue={selectedPrinter.configuration.defaultDarkness}
                    min="0"
                    max="30"
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="speed" className="text-right">
                    Speed
                  </Label>
                  <Input
                    id="speed"
                    type="number"
                    className="col-span-3"
                    defaultValue={selectedPrinter.configuration.defaultSpeed}
                    min="1"
                    max="14"
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="queue-size" className="text-right">
                    Max Queue Size
                  </Label>
                  <Input
                    id="queue-size"
                    type="number"
                    className="col-span-3"
                    defaultValue={selectedPrinter.configuration.maxQueueSize}
                    min="1"
                    max="1000"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setConfigDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit">Save Changes</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  )
}