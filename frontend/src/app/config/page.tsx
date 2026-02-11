"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SystemStatus } from "./system-status";
import { WhatsAppConfigForm } from "./whatsapp-config";
import { ZohoConfigForm } from "./zoho-config";
import { LLMConfigForm } from "./llm-config";
import { EmailConfigForm } from "./email-config";

export function ConfigurationDashboard() {
  const [activeTab, setActiveTab] = useState("status");

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Configuración del Sistema</h1>
        <p className="text-muted-foreground mt-2">
          Gestiona las integraciones con WhatsApp, Zoho, LLM y Email.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5 lg:w-auto">
          <TabsTrigger value="status">Estado</TabsTrigger>
          <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger>
          <TabsTrigger value="zoho">Zoho</TabsTrigger>
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

        <TabsContent value="zoho" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Zoho Recruit API</CardTitle>
              <CardDescription>
                Configura la integración con Zoho Recruit.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ZohoConfigForm />
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
