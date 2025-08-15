"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { 
  Rocket, 
  Search, 
  Printer, 
  ListOrdered, 
  Clock, 
  AlertCircle,
  Copy,
  Play
} from "lucide-react"
import { toast } from "sonner"

interface ApiKey {
  id: string
  name: string
  key?: string
  created_at: string
}

interface PrinterDevice {
  id: string
  friendly_name: string
  status: string
  ip_address?: string
  device_id: string
}

interface TestResult {
  success?: boolean
  data?: Record<string, unknown>
  error?: string
  message?: string
}

export default function ApiDocsPage() {
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [printers, setPrinters] = useState<PrinterDevice[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState('')
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  useEffect(() => {
    // Set base URL
    setBaseUrl(window.location.origin)
    
    // Fetch API keys
    fetchApiKeys()
    
    // Fetch printers
    fetchPrinters()
  }, [])

  const fetchApiKeys = async () => {
    try {
      const response = await fetch('/api/api-keys')
      if (response.ok) {
        const result = await response.json()
        setApiKeys(result.data?.keys || [])
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error)
    }
  }

  const fetchPrinters = async () => {
    try {
      const response = await fetch('/api/pis')
      if (response.ok) {
        const result = await response.json()
        setPrinters(result.data?.pis || [])
        if (result.data?.pis?.length > 0) {
          setSelectedPrinter(result.data.pis[0].id)
        }
      }
    } catch (error) {
      console.error('Failed to fetch printers:', error)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const tryEndpoint = async (endpoint: string) => {
    setLoading({ ...loading, [endpoint]: true })
    try {
      let url = ''
      const options: RequestInit = {}
      
      switch(endpoint) {
        case 'list-printers':
          url = '/api/pis'
          break
        case 'printer-details':
          url = `/api/pis/${selectedPrinter}`
          break
        case 'print-history':
          url = '/api/recent-jobs?limit=10'
          break
        case 'label-sizes':
          url = '/api/label-sizes'
          break
        default:
          throw new Error('Unknown endpoint')
      }
      
      const response = await fetch(url, options)
      const result = await response.json()
      setTestResults({ ...testResults, [endpoint]: result })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setTestResults({ ...testResults, [endpoint]: { error: errorMessage } })
    } finally {
      setLoading({ ...loading, [endpoint]: false })
    }
  }

  const sendTestPrint = async () => {
    if (!selectedPrinter) {
      toast.error('Please select a printer')
      return
    }
    
    setLoading({ ...loading, 'test-print': true })
    try {
      const response = await fetch(`/api/pis/${selectedPrinter}/test-print`, {
        method: 'POST'
      })
      const result = await response.json()
      
      if (result.success) {
        toast.success('Test print sent successfully!')
        setTestResults({ ...testResults, 'test-print': result })
      } else {
        toast.error(result.message || 'Failed to send test print')
      }
    } catch (error) {
      toast.error('Failed to send test print')
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setTestResults({ ...testResults, 'test-print': { error: errorMessage } })
    } finally {
      setLoading({ ...loading, 'test-print': false })
    }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">API Documentation</h2>
      </div>

      {/* Getting Started */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Rocket className="h-5 w-5" />
            Getting Started
          </CardTitle>
          <CardDescription>
            Welcome to the LabelBerry API! This guide will help you integrate label printing into your applications.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-muted p-4 space-y-2">
            <div className="flex items-center gap-2">
              <strong>Base URL:</strong>
              <code className="text-sm bg-background px-2 py-1 rounded">{baseUrl}</code>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => copyToClipboard(baseUrl)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <strong>Content-Type:</strong>
              <code className="text-sm bg-background px-2 py-1 rounded">application/json</code>
            </div>
            <div className="flex items-center gap-2">
              <strong>Authentication:</strong>
              <code className="text-sm bg-background px-2 py-1 rounded">Bearer token in Authorization header</code>
            </div>
          </div>

          {/* Authentication Example */}
          <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-4 space-y-2">
            <p className="text-sm font-medium">Authentication Example:</p>
            <code className="text-xs bg-background px-2 py-1 rounded block">
              Authorization: Bearer labk_your_api_key_here
            </code>
            <p className="text-xs text-muted-foreground mt-2">
              Include this header in all authenticated requests. API keys start with &quot;ak_&quot; prefix.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    1
                  </div>
                  <CardTitle className="text-sm">Get Your API Key</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {apiKeys.length > 0 ? (
                  <div className="space-y-1">
                    <p>Available API Keys:</p>
                    <div className="space-y-1">
                      {apiKeys.slice(0, 2).map((key, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {key.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p>Create an API key in the API Keys section</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    2
                  </div>
                  <CardTitle className="text-sm">Find Your Printer</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">List available printers</p>
                <Button 
                  size="sm" 
                  onClick={() => tryEndpoint('list-printers')}
                  disabled={loading['list-printers']}
                >
                  <Play className="mr-2 h-3 w-3" />
                  Try It
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    3
                  </div>
                  <CardTitle className="text-sm">Send Print Job</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">Send ZPL to your printer</p>
                <Button 
                  size="sm"
                  onClick={sendTestPrint}
                  disabled={loading['test-print'] || !selectedPrinter}
                >
                  <Printer className="mr-2 h-3 w-3" />
                  Test Print
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Show test results */}
          {testResults['list-printers'] && (
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm font-medium mb-2">List Printers Response:</p>
              <pre className="text-xs overflow-auto">
                {JSON.stringify(testResults['list-printers'], null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Endpoints */}
      <Tabs defaultValue="discovery" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="discovery">Discovery</TabsTrigger>
          <TabsTrigger value="printing">Printing</TabsTrigger>
          <TabsTrigger value="queue">Queue</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="discovery" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Printer Discovery & Status
              </CardTitle>
              <CardDescription>
                Find and monitor your connected label printers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* List All Printers */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500">GET</Badge>
                    <code className="text-sm">/api/pis</code>
                  </div>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => tryEndpoint('list-printers')}
                    disabled={loading['list-printers']}
                  >
                    <Play className="mr-2 h-3 w-3" />
                    Try It
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Returns a list of all registered printers with their current status
                </p>
              </div>

              {/* Get Printer Details */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-500">GET</Badge>
                  <code className="text-sm">/api/pis/{'{pi_id}'}</code>
                </div>
                <p className="text-sm text-muted-foreground">
                  Get detailed information about a specific printer
                </p>
                {printers.length > 0 && (
                  <div className="flex gap-2 items-end">
                    <div className="flex-1">
                      <Label htmlFor="printer-select">Select Printer</Label>
                      <select
                        id="printer-select"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={selectedPrinter}
                        onChange={(e) => setSelectedPrinter(e.target.value)}
                      >
                        {printers.map((printer) => (
                          <option key={printer.id} value={printer.id}>
                            {printer.friendly_name} ({printer.status})
                          </option>
                        ))}
                      </select>
                    </div>
                    <Button 
                      onClick={() => tryEndpoint('printer-details')}
                      disabled={loading['printer-details']}
                    >
                      Get Details
                    </Button>
                  </div>
                )}
              </div>

              {testResults['printer-details'] && (
                <div className="rounded-lg bg-muted p-4">
                  <p className="text-sm font-medium mb-2">Printer Details Response:</p>
                  <pre className="text-xs overflow-auto">
                    {JSON.stringify(testResults['printer-details'], null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="printing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Printer className="h-5 w-5" />
                Sending Print Jobs
              </CardTitle>
              <CardDescription>
                Send ZPL data to your printers with automatic queuing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-4">
                <p className="text-sm">
                  <strong>Smart Routing:</strong> Jobs are automatically queued when printers are offline and sent when they reconnect.
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge className="bg-blue-500">POST</Badge>
                  <code className="text-sm">/api/pis/{'{pi_id}'}/print</code>
                  <Badge variant="outline">Requires Auth</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Send a print job to a printer. Jobs are queued if the printer is offline.
                </p>
              </div>

              <div className="space-y-2">
                <Label>Request Body Example</Label>
                <div className="rounded-lg bg-muted p-4">
                  <pre className="text-xs">
{`{
  "zpl_raw": "^XA^FO50,50^ADN,36,20^FDHello World^FS^XZ"
  // OR
  "zpl_url": "https://example.com/label.zpl"
}`}
                  </pre>
                </div>
              </div>

              <div className="space-y-2">
                <Label>cURL Example</Label>
                <div className="rounded-lg bg-muted p-4">
                  <pre className="text-xs overflow-x-auto">
{`# Send a print job with raw ZPL
curl -X POST http://your-server:8080/api/pis/YOUR_PI_ID/print \\
  -H "Authorization: Bearer labk_your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_raw": "^XA^FO50,50^ADN,36,20^FDHello World^FS^XZ"
  }'

# Send a print job from URL
curl -X POST http://your-server:8080/api/pis/YOUR_PI_ID/print \\
  -H "Authorization: Bearer labk_your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_url": "https://example.com/label.zpl"
  }'`}
                  </pre>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Response</Label>
                <div className="rounded-lg bg-muted p-4">
                  <pre className="text-xs">
{`{
  "success": true,
  "message": "Print job sent successfully",
  "data": {
    "job_id": "uuid-here",
    "status": "completed",
    "queue_position": null
  }
}`}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Direct Pi Printing */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Printer className="h-5 w-5" />
                Direct Pi Printing (Local Network)
              </CardTitle>
              <CardDescription>
                If you have direct network access to the Pi, you can send print jobs directly without authentication
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-4">
                <p className="text-sm">
                  <strong>Direct Access:</strong> Print directly to Pi at <code>http://pi-ip:5000/print</code> without authentication (local network only)
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge className="bg-blue-500">POST</Badge>
                  <code className="text-sm">http://pi-ip:5000/print</code>
                </div>
                <p className="text-sm text-muted-foreground">
                  Send print jobs directly to a Pi on your local network
                </p>
              </div>

              <div className="space-y-2">
                <Label>cURL Example (Direct to Pi)</Label>
                <div className="rounded-lg bg-muted p-4">
                  <pre className="text-xs overflow-x-auto">
{`# Direct print to Pi (no authentication required)
curl -X POST http://192.168.1.100:5000/print \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_raw": "^XA^FO50,50^FDDirect Print^FS^XZ"
  }'`}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="queue" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ListOrdered className="h-5 w-5" />
                Queue Management
              </CardTitle>
              <CardDescription>
                Monitor and manage print jobs in the queue
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500">GET</Badge>
                    <code className="text-sm">/api/queue</code>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    View all queued jobs across all printers
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-red-500">DELETE</Badge>
                    <code className="text-sm">/api/jobs/{'{job_id}'}/cancel</code>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Cancel a queued or pending job
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-blue-500">POST</Badge>
                    <code className="text-sm">/api/jobs/{'{job_id}'}/retry</code>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Retry a failed job
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Job History & Tracking
              </CardTitle>
              <CardDescription>
                Track the status and history of print jobs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500">GET</Badge>
                    <code className="text-sm">/api/recent-jobs</code>
                  </div>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => tryEndpoint('print-history')}
                    disabled={loading['print-history']}
                  >
                    <Play className="mr-2 h-3 w-3" />
                    Try It
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Get print history with complete job details
                </p>
              </div>

              {testResults['print-history'] && (
                <div className="rounded-lg bg-muted p-4">
                  <p className="text-sm font-medium mb-2">Print History Response:</p>
                  <pre className="text-xs overflow-auto max-h-64">
                    {JSON.stringify(testResults['print-history'], null, 2)}
                  </pre>
                </div>
              )}

              <div className="space-y-2">
                <Label>Job Status Reference</Label>
                <div className="grid gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">QUEUED</Badge>
                    <span className="text-sm">Waiting to be sent</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">PENDING</Badge>
                    <span className="text-sm">In printer&apos;s local queue</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-blue-500">PROCESSING</Badge>
                    <span className="text-sm">Currently printing</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500">COMPLETED</Badge>
                    <span className="text-sm">Successfully printed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive">FAILED</Badge>
                    <span className="text-sm">Print failed</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Error Responses */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            Error Responses
          </CardTitle>
          <CardDescription>
            Common error responses and how to handle them
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="destructive">401</Badge>
                <span className="font-medium">Unauthorized</span>
              </div>
              <p className="text-sm text-muted-foreground">Invalid or missing API key</p>
              <div className="rounded-lg bg-muted p-2">
                <code className="text-xs">{"{ \"detail\": \"Invalid API key\" }"}</code>
              </div>
            </div>

            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="destructive">404</Badge>
                <span className="font-medium">Not Found</span>
              </div>
              <p className="text-sm text-muted-foreground">The requested resource doesn&apos;t exist</p>
              <div className="rounded-lg bg-muted p-2">
                <code className="text-xs">{"{ \"detail\": \"Pi not found\" }"}</code>
              </div>
            </div>

            <div className="rounded-lg border p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="destructive">400</Badge>
                <span className="font-medium">Bad Request</span>
              </div>
              <p className="text-sm text-muted-foreground">Invalid request format or parameters</p>
              <div className="rounded-lg bg-muted p-2">
                <code className="text-xs">{"{ \"detail\": \"Either zpl_url or zpl_raw must be provided\" }"}</code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}