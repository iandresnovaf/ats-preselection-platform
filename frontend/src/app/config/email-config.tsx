"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export function EmailConfigForm() {
  const [config, setConfig] = useState({
    smtpHost: "",
    smtpPort: "587",
    username: "",
    password: "",
    useTls: true,
    fromEmail: "",
    fromName: "Top Management",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Save to backend
    console.log("Saving Email config:", config);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="smtpHost">SMTP Host</Label>
          <Input
            id="smtpHost"
            value={config.smtpHost}
            onChange={(e) => setConfig({ ...config, smtpHost: e.target.value })}
            placeholder="smtp.gmail.com"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="smtpPort">Puerto</Label>
          <Input
            id="smtpPort"
            value={config.smtpPort}
            onChange={(e) => setConfig({ ...config, smtpPort: e.target.value })}
            placeholder="587"
          />
        </div>
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="username">Usuario / Email</Label>
        <Input
          id="username"
          value={config.username}
          onChange={(e) => setConfig({ ...config, username: e.target.value })}
          placeholder="noreply@tuempresa.com"
        />
      </div>
      
      <div className="space-y-2">
        <Label htmlFor="password">Contraseña / App Password</Label>
        <Input
          id="password"
          type="password"
          value={config.password}
          onChange={(e) => setConfig({ ...config, password: e.target.value })}
          placeholder="••••••••"
        />
      </div>
      
      <div className="flex items-center space-x-2">
        <Switch
          id="useTls"
          checked={config.useTls}
          onCheckedChange={(checked) => setConfig({ ...config, useTls: checked })}
        />
        <Label htmlFor="useTls">Usar TLS/SSL</Label>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="fromEmail">Email Remitente</Label>
          <Input
            id="fromEmail"
            value={config.fromEmail}
            onChange={(e) => setConfig({ ...config, fromEmail: e.target.value })}
            placeholder="noreply@tuempresa.com"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="fromName">Nombre Remitente</Label>
          <Input
            id="fromName"
            value={config.fromName}
            onChange={(e) => setConfig({ ...config, fromName: e.target.value })}
            placeholder="Top Management"
          />
        </div>
      </div>
      
      <Button type="submit">Guardar Configuración</Button>
    </form>
  );
}
