"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Switch } from "@/components/ui/switch"
import { Save } from "lucide-react"
import { useState } from "react"

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    serverUrl: "https://labelberry.example.com",
    wsPort: "8080",
    defaultLabelWidth: "4",
    defaultLabelHeight: "6",
    maxQueueSize: "100",
    retryAttempts: "3",
    retryDelay: "5",
    enableNotifications: true,
    enableAutoReconnect: true,
    enableDebugMode: false,
    dataRetention: "30",
    logLevel: "info"
  })

  const [credentials, setCredentials] = useState({
    currentPassword: "",
    newUsername: "",
    newPassword: "",
    confirmPassword: ""
  })

  const handleSaveSettings = () => {
    console.log("Saving settings:", settings)
    // Add save logic here
  }

  const handleUpdateCredentials = () => {
    console.log("Updating credentials")
    // Add credential update logic here
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">System Settings</h2>
      </div>

      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="printer">Printer Defaults</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>
                Configure basic system settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="server-url">Server URL</Label>
                  <Input
                    id="server-url"
                    value={settings.serverUrl}
                    onChange={(e) => setSettings({...settings, serverUrl: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ws-port">WebSocket Port</Label>
                  <Input
                    id="ws-port"
                    value={settings.wsPort}
                    onChange={(e) => setSettings({...settings, wsPort: e.target.value})}
                  />
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="notifications"
                    checked={settings.enableNotifications}
                    onCheckedChange={(checked) => setSettings({...settings, enableNotifications: checked})}
                  />
                  <Label htmlFor="notifications">Enable notifications</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="auto-reconnect"
                    checked={settings.enableAutoReconnect}
                    onCheckedChange={(checked) => setSettings({...settings, enableAutoReconnect: checked})}
                  />
                  <Label htmlFor="auto-reconnect">Enable auto-reconnect for printers</Label>
                </div>
              </div>
              
              <Button onClick={handleSaveSettings}>
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="printer" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Printer Defaults</CardTitle>
              <CardDescription>
                Set default values for new printer configurations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="label-width">Default Label Width (inches)</Label>
                  <Input
                    id="label-width"
                    type="number"
                    value={settings.defaultLabelWidth}
                    onChange={(e) => setSettings({...settings, defaultLabelWidth: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="label-height">Default Label Height (inches)</Label>
                  <Input
                    id="label-height"
                    type="number"
                    value={settings.defaultLabelHeight}
                    onChange={(e) => setSettings({...settings, defaultLabelHeight: e.target.value})}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="max-queue">Max Queue Size</Label>
                  <Input
                    id="max-queue"
                    type="number"
                    value={settings.maxQueueSize}
                    onChange={(e) => setSettings({...settings, maxQueueSize: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="retry-attempts">Retry Attempts</Label>
                  <Input
                    id="retry-attempts"
                    type="number"
                    value={settings.retryAttempts}
                    onChange={(e) => setSettings({...settings, retryAttempts: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="retry-delay">Retry Delay (seconds)</Label>
                  <Input
                    id="retry-delay"
                    type="number"
                    value={settings.retryDelay}
                    onChange={(e) => setSettings({...settings, retryDelay: e.target.value})}
                  />
                </div>
              </div>
              
              <Button onClick={handleSaveSettings}>
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Manage authentication and security settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="current-password">Current Password</Label>
                  <Input
                    id="current-password"
                    type="password"
                    value={credentials.currentPassword}
                    onChange={(e) => setCredentials({...credentials, currentPassword: e.target.value})}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="new-username">New Username (optional)</Label>
                    <Input
                      id="new-username"
                      value={credentials.newUsername}
                      onChange={(e) => setCredentials({...credentials, newUsername: e.target.value})}
                      placeholder="Leave blank to keep current"
                    />
                  </div>
                  <div></div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="new-password">New Password</Label>
                    <Input
                      id="new-password"
                      type="password"
                      value={credentials.newPassword}
                      onChange={(e) => setCredentials({...credentials, newPassword: e.target.value})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm Password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      value={credentials.confirmPassword}
                      onChange={(e) => setCredentials({...credentials, confirmPassword: e.target.value})}
                    />
                  </div>
                </div>
              </div>
              
              <Button onClick={handleUpdateCredentials}>
                <Save className="mr-2 h-4 w-4" />
                Update Credentials
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
              <CardDescription>
                Configure advanced system options
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="data-retention">Data Retention (days)</Label>
                  <Input
                    id="data-retention"
                    type="number"
                    value={settings.dataRetention}
                    onChange={(e) => setSettings({...settings, dataRetention: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="log-level">Log Level</Label>
                  <select
                    id="log-level"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={settings.logLevel}
                    onChange={(e) => setSettings({...settings, logLevel: e.target.value})}
                  >
                    <option value="debug">Debug</option>
                    <option value="info">Info</option>
                    <option value="warn">Warning</option>
                    <option value="error">Error</option>
                  </select>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Switch
                  id="debug-mode"
                  checked={settings.enableDebugMode}
                  onCheckedChange={(checked) => setSettings({...settings, enableDebugMode: checked})}
                />
                <Label htmlFor="debug-mode">Enable debug mode</Label>
              </div>
              
              <Button onClick={handleSaveSettings}>
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}