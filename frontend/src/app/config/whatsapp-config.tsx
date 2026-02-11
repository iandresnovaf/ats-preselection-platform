"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function WhatsAppConfigForm() {
  const [config, setConfig] = useState({
    accessToken: "",
    phoneNumberId: "",
    verifyToken: "",
    webhookUrl: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Save to backend
    console.log("Saving WhatsApp config:", config);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="accessToken">Access Token de Meta</Label>
        <Input
          id="accessToken"
          type="password"
          value={config.accessToken}
          onChange={(e) => setConfig({ ...config, accessToken: e.target.value })}
          placeholder="EAA..."
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="phoneNumberId">Phone Number ID</Label>
        <Input
          id="phoneNumberId"
          value={config.phoneNumberId}
          onChange={(e) => setConfig({ ...config, phoneNumberId: e.target.value })}
          placeholder="123456789"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="verifyToken">Verify Token (para webhooks)</Label>
        <Input
          id="verifyToken"
          value={config.verifyToken}
          onChange={(e) => setConfig({ ...config, verifyToken: e.target.value })}
          placeholder="my_verify_token"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="webhookUrl">Webhook URL</Label>
        <Input
          id="webhookUrl"
          value={config.webhookUrl}
          onChange={(e) => setConfig({ ...config, webhookUrl: e.target.value })}
          placeholder="https://tudominio.com/api/webhooks/whatsapp"
        />
        <p className="text-sm text-muted-foreground">
          Configura esta URL en el dashboard de Meta para recibir mensajes.
        </p>
      </div>
      
      <Button type="submit">Guardar Configuración</Button>
    </form>
  );
}
