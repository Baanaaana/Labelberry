"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Plus, Trash2, Copy, Eye, EyeOff } from "lucide-react"
import { useState, useEffect } from "react"

interface ApiKey {
  id: string
  name: string
  key: string
  description: string
  lastUsed: string | null
  createdAt: string
}

interface ApiKeyData {
  id: string
  name: string
  key: string
  description?: string
  lastUsed?: string | null
  createdAt: string
}

export default function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])

  const [showKeys, setShowKeys] = useState<{ [key: string]: boolean }>({})
  const [newKeyDialog, setNewKeyDialog] = useState(false)
  const [newKeyData, setNewKeyData] = useState({
    name: "",
    description: ""
  })
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [keyToDelete, setKeyToDelete] = useState<{ id: string; name: string } | null>(null)

  const fetchApiKeys = async () => {
    try {
      const response = await fetch('/fastapi/api-keys')
      const result = await response.json()
      
      // Handle wrapped API response
      const data = result.data?.keys || result.data || result || []
      const keysArray = Array.isArray(data) ? data : []
      
      const formattedKeys = keysArray.map((key: ApiKeyData) => ({
        id: key.id,
        name: key.name,
        key: key.key,
        description: key.description || '',
        lastUsed: key.lastUsed || null,
        createdAt: key.createdAt
      }))
      
      setApiKeys(formattedKeys)
    } catch (error) {
      console.error('Failed to fetch API keys:', error)
      setApiKeys([])
    }
  }

  useEffect(() => {
    fetchApiKeys()
  }, [])

  const toggleKeyVisibility = (keyId: string) => {
    setShowKeys(prev => ({ ...prev, [keyId]: !prev[keyId] }))
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // Could add a toast notification here
  }

  const handleDeleteClick = (keyId: string, keyName: string) => {
    setKeyToDelete({ id: keyId, name: keyName })
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!keyToDelete) return
    
    try {
      const response = await fetch(`/fastapi/api-keys/${keyToDelete.id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // Successfully deleted, update the UI
        setApiKeys(prev => prev.filter(k => k.id !== keyToDelete.id))
        setDeleteDialogOpen(false)
        setKeyToDelete(null)
      } else {
        // Handle error - you might want to add toast notification here
        console.error('Failed to delete API key')
      }
    } catch (error) {
      console.error('Failed to delete API key:', error)
    }
  }

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setKeyToDelete(null)
  }

  const createApiKey = async () => {
    try {
      const response = await fetch('/fastapi/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newKeyData.name,
          description: newKeyData.description
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        
        // Create the new key object from the response
        const newKey: ApiKey = {
          id: result.data?.id || Date.now().toString(),
          name: newKeyData.name,
          key: result.data?.key || `ak_${Math.random().toString(36).substring(2, 15)}`,
          description: newKeyData.description,
          lastUsed: null,
          createdAt: new Date().toISOString()
        }
        
        // Add to local state
        setApiKeys(prev => [...prev, newKey])
        
        // Close dialog and reset form
        setNewKeyDialog(false)
        setNewKeyData({
          name: "",
          description: ""
        })
        
        // Refresh the list to ensure consistency
        fetchApiKeys()
      } else {
        console.error('Failed to create API key')
      }
    } catch (error) {
      console.error('Failed to create API key:', error)
    }
  }


  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">API Keys</h2>
          <p className="text-muted-foreground">
            Manage API keys for accessing the LabelBerry system
          </p>
        </div>
        <Dialog open={newKeyDialog} onOpenChange={setNewKeyDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create API Key
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[525px]">
            <DialogHeader>
              <DialogTitle>Create New API Key</DialogTitle>
              <DialogDescription>
                Generate a new API key for accessing the LabelBerry system
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">
                  Name
                </Label>
                <Input
                  id="name"
                  value={newKeyData.name}
                  onChange={(e) => setNewKeyData({...newKeyData, name: e.target.value})}
                  className="col-span-3"
                  placeholder="e.g., Production API"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="description" className="text-right">
                  Description
                </Label>
                <Input
                  id="description"
                  value={newKeyData.description}
                  onChange={(e) => setNewKeyData({...newKeyData, description: e.target.value})}
                  className="col-span-3"
                  placeholder="What is this key for?"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setNewKeyDialog(false)}>
                Cancel
              </Button>
              <Button onClick={createApiKey}>
                Create Key
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active API Keys</CardTitle>
          <CardDescription>
            Manage and monitor API key usage
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{apiKey.name}</p>
                      <p className="text-sm text-muted-foreground">{apiKey.description}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <code className="text-sm">
                        {showKeys[apiKey.id] ? apiKey.key : "ak_••••••••••••••••"}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleKeyVisibility(apiKey.id)}
                      >
                        {showKeys[apiKey.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(apiKey.key)}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    {apiKey.lastUsed ? (
                      <span className="text-sm">{new Date(apiKey.lastUsed).toLocaleString()}</span>
                    ) : (
                      <span className="text-muted-foreground">Never</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">{new Date(apiKey.createdAt).toLocaleDateString()}</span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteClick(apiKey.id, apiKey.name)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the API key &quot;{keyToDelete?.name}&quot;? This action cannot be undone and any applications using this key will stop working.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleCancelDelete}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              Delete API Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  )
}