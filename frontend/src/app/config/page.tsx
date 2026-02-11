"use client";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SystemStatus } from "./system-status";
import { WhatsAppConfigForm } from "./whatsapp-config";
import { ATSConfigForm } from "./ats-config";
import { LLMConfigForm } from "./llm-config";
import { EmailConfigForm } from "./email-config";
import { BrandingConfigForm } from "./branding-config";
import { AccountConfigForm } from "./account-config";

export default function ConfigurationPage() {
  return (
    <ProtectedRoute allowedRoles={["super_admin"]}>
      <ConfigurationDashboard />
    </ProtectedRoute>
  );
}

function ConfigurationDashboard() {
  const [activeTab, setActiveTab] = useState("status");

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Configuración del Sistema</h1>
        <p className="text-muted-foreground mt-2">
          Gestiona las integraciones con WhatsApp, ATS (Zoho/Odoo), LLM y Email. Solo disponible para Super Administradores.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-7 lg:w-auto">
          <TabsTrigger value="status">Estado</TabsTrigger>
          <TabsTrigger value="account">Mi Cuenta</TabsTrigger>
          <TabsTrigger value="branding">Marca/Logo</TabsTrigger>
          <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger>
          <TabsTrigger value="ats">ATS</TabsTrigger>
          <TabsTrigger value="llm">LLM</TabsTrigger>
          <TabsTrigger value="email">Email</TabsTrigger>
        </TabsList>

        <TabsContent value="status" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Estado del Sistema</CardTitle>
              <CardDescription>
                Verifica el estado de todas las integraciones y servicios.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SystemStatus />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="account" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mi Cuenta</CardTitle>
              <CardDescription>
                Gestiona tu contraseña y email de acceso.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AccountConfigForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="branding" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Personalización de Marca</CardTitle>
              <CardDescription>
                Configura el logo y nombre de tu empresa para personalizar la experiencia de los candidatos.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <BrandingConfigForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="whatsapp" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>WhatsApp Business API</CardTitle>
              <CardDescription>
                Configura la integración con WhatsApp Business API de Meta.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <WhatsAppConfigForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ats" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Integración con ATS</CardTitle>
              <CardDescription>
                Selecciona y configura tu sistema de seguimiento de candidatos (ATS).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ATSConfigForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="llm" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Proveedor LLM</CardTitle>
              <CardDescription>
                Configura OpenAI, Anthropic u otro proveedor de LLM.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LLMConfigForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="email" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Servidor de Email</CardTitle>
              <CardDescription>
                Configura SMTP o servicios como SendGrid/Mailgun.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmailConfigForm />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
