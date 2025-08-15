"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Save } from "lucide-react"
import { useState, useEffect } from "react"
import { toast } from "sonner"

export default function SettingsPage() {
  const [mqttSettings, setMqttSettings] = useState({
    mqtt_broker: "localhost",
    mqtt_port: "1883",
    mqtt_username: "",
    mqtt_password: ""
  })

  // Fetch MQTT settings on component mount
  useEffect(() => {
    fetchMqttSettings()
  }, [])

  const fetchMqttSettings = async () => {
    try {
      const response = await fetch('/api/mqtt-settings')
      if (response.ok) {
        const result = await response.json()
        if (result.success && result.data) {
          setMqttSettings({
            mqtt_broker: result.data.mqtt_broker || 'localhost',
            mqtt_port: result.data.mqtt_port?.toString() || '1883',
            mqtt_username: result.data.mqtt_username || '',
            mqtt_password: ''  // Don't populate password field
          })
        }
      }
    } catch (error) {
      console.error('Failed to fetch MQTT settings:', error)
    }
  }

  const handleSaveMqttSettings = async () => {
    try {
      // Only include password if it's not empty
      const settingsToSave = {
        mqtt_broker: mqttSettings.mqtt_broker,
        mqtt_port: mqttSettings.mqtt_port,
        mqtt_username: mqttSettings.mqtt_username,
      }
      
      // Only add password if user entered something
      if (mqttSettings.mqtt_password && mqttSettings.mqtt_password.trim() !== '') {
        (settingsToSave as Record<string, string | number>).mqtt_password = mqttSettings.mqtt_password
      }
      
      const response = await fetch('/api/mqtt-settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settingsToSave)
      })
      
      if (response.ok) {
        const result = await response.json()
        toast.success(result.message || 'MQTT settings saved successfully!')
        // Clear password field after save
        setMqttSettings(prev => ({ ...prev, mqtt_password: '' }))
      } else {
        const error = await response.json().catch(() => null)
        toast.error(`Failed to save MQTT settings: ${error?.detail || response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to save MQTT settings:', error)
      toast.error('Failed to save MQTT settings. Please check the console for details.')
    }
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">System Settings</h2>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>MQTT Broker Settings</CardTitle>
          <CardDescription>
            Configure the MQTT broker connection for printer communication
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="mqtt-broker">MQTT Broker Host</Label>
              <Input
                id="mqtt-broker"
                placeholder="e.g., localhost or 192.168.1.100"
                value={mqttSettings.mqtt_broker}
                onChange={(e) => setMqttSettings({...mqttSettings, mqtt_broker: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mqtt-port">MQTT Port</Label>
              <Input
                id="mqtt-port"
                type="number"
                placeholder="1883"
                value={mqttSettings.mqtt_port}
                onChange={(e) => setMqttSettings({...mqttSettings, mqtt_port: e.target.value})}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="mqtt-username">Username (Optional)</Label>
              <Input
                id="mqtt-username"
                placeholder="Leave blank for no authentication"
                value={mqttSettings.mqtt_username}
                onChange={(e) => setMqttSettings({...mqttSettings, mqtt_username: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mqtt-password">Password (Optional)</Label>
              <Input
                id="mqtt-password"
                type="password"
                placeholder="Leave blank to keep current password"
                value={mqttSettings.mqtt_password}
                onChange={(e) => setMqttSettings({...mqttSettings, mqtt_password: e.target.value})}
              />
            </div>
          </div>

          <div className="rounded-lg bg-muted p-4">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> The MQTT broker is used for real-time communication with Raspberry Pi printers. 
              Make sure the broker is accessible from both this server and all Raspberry Pi devices.
            </p>
          </div>
          
          <Button onClick={handleSaveMqttSettings}>
            <Save className="mr-2 h-4 w-4" />
            Save MQTT Settings
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}