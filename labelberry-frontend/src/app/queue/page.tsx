"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { RefreshCw, Trash2, RotateCcw } from "lucide-react"
import { useState, useEffect } from "react"

interface QueueItem {
  id: string
  printerId: string
  printerName: string
  status: "pending" | "processing" | "completed" | "failed"
  zplSource: string
  createdAt: string
  startedAt?: string
  completedAt?: string
  retryCount: number
  errorMessage?: string
}

export default function QueuePage() {
  const [queueItems, setQueueItems] = useState<QueueItem[]>([])

  const [selectedPrinter, setSelectedPrinter] = useState<string>("all")
  const [selectedStatus, setSelectedStatus] = useState<string>("all")

  const fetchQueueItems = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedPrinter !== "all") params.append("printerId", selectedPrinter)
      if (selectedStatus !== "all") params.append("status", selectedStatus)
      
      const response = await fetch(`/api/queue?${params}`)
      const result = await response.json()
      // Handle wrapped API response or direct array
      const data = result.data?.items || result.data || result || []
      setQueueItems(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Failed to fetch queue items:', error)
      setQueueItems([])
    }
  }

  useEffect(() => {
    fetchQueueItems()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPrinter, selectedStatus])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="outline">Pending</Badge>
      case "processing":
        return <Badge className="bg-blue-500">Processing</Badge>
      case "completed":
        return <Badge className="bg-green-500">Completed</Badge>
      case "failed":
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  const handleRetry = (itemId: string) => {
    console.log(`Retrying job ${itemId}`)
    // Add retry logic here
  }

  const handleDelete = async (itemId: string) => {
    // TODO: Implement delete endpoint
    setQueueItems(queueItems.filter(item => item.id !== itemId))
  }

  const handleClearCompleted = () => {
    setQueueItems(queueItems.filter(item => item.status !== "completed"))
  }

  const filteredItems = queueItems.filter(item => {
    if (selectedPrinter !== "all" && item.printerId !== selectedPrinter) return false
    if (selectedStatus !== "all" && item.status !== selectedStatus) return false
    return true
  })

  const stats = {
    total: queueItems.length,
    pending: queueItems.filter(i => i.status === "pending").length,
    processing: queueItems.filter(i => i.status === "processing").length,
    completed: queueItems.filter(i => i.status === "completed").length,
    failed: queueItems.filter(i => i.status === "failed").length
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Queue Management</h2>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={handleClearCompleted}>
            Clear Completed
          </Button>
          <Button variant="outline" size="sm" onClick={() => fetchQueueItems()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Processing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats.processing}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Print Queue</CardTitle>
          <CardDescription>
            Manage and monitor all print jobs across printers
          </CardDescription>
          <div className="flex space-x-2 pt-4">
            <Select value={selectedPrinter} onValueChange={setSelectedPrinter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Filter by printer" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Printers</SelectItem>
                <SelectItem value="1">Warehouse A - Station 1</SelectItem>
                <SelectItem value="2">Warehouse A - Station 2</SelectItem>
                <SelectItem value="3">Warehouse B - Main</SelectItem>
                <SelectItem value="4">Office - Shipping</SelectItem>
              </SelectContent>
            </Select>
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Printer</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Retries</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredItems.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-sm">{item.id}</TableCell>
                  <TableCell>{item.printerName}</TableCell>
                  <TableCell>{getStatusBadge(item.status)}</TableCell>
                  <TableCell className="max-w-[200px] truncate">
                    {item.zplSource.startsWith("http") ? (
                      <span className="text-sm text-muted-foreground">URL: {item.zplSource}</span>
                    ) : (
                      <span className="text-sm text-muted-foreground">Raw ZPL</span>
                    )}
                  </TableCell>
                  <TableCell>{item.createdAt}</TableCell>
                  <TableCell>{item.retryCount}</TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      {item.status === "failed" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRetry(item.id)}
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>
                      )}
                      {(item.status === "pending" || item.status === "failed") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}