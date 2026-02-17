"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  useCreateTemplate,
  useUpdateTemplate,
  useTemplateVariables,
  usePreviewTemplate,
} from "@/hooks/use-message-templates";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Loader2,
  Eye,
  Save,
  ArrowLeft,
  Mail,
  MessageCircle,
  Smartphone,
  Plus,
  X,
  Info,
} from "lucide-react";
import type {
  MessageTemplate,
  MessageChannel,
  CreateTemplateData,
} from "@/types/message-templates";

const channelOptions: { value: MessageChannel; label: string; icon: typeof Mail }[] = [
  { value: "email", label: "Email", icon: Mail },
  { value: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { value: "sms", label: "SMS", icon: Smartphone },
];

interface TemplateFormProps {
  template?: MessageTemplate;
  mode: "create" | "edit";
}

export default function TemplateForm({ template, mode }: TemplateFormProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("edit");
  
  // Form state
  const [name, setName] = useState(template?.name || "");
  const [description, setDescription] = useState(template?.description || "");
  const [channel, setChannel] = useState<MessageChannel>(template?.channel || "whatsapp");
  const [subject, setSubject] = useState(template?.subject || "");
  const [body, setBody] = useState(template?.body || "");
  const [isActive, setIsActive] = useState(template?.is_active ?? true);
  const [detectedVars, setDetectedVars] = useState<string[]>(template?.variables || []);
  
  // Preview state
  const [previewVars, setPreviewVars] = useState<Record<string, string>>({});
  
  const createMutation = useCreateTemplate();
  const updateMutation = useUpdateTemplate();
  const { data: availableVars } = useTemplateVariables();
  const previewMutation = usePreviewTemplate(
    mode === "edit" && template ? template.template_id : null
  );

  // Detectar variables del body y subject
  const detectVariables = useCallback((text: string) => {
    const regex = /\{([a-z_][a-z0-9_]*)\}/g;
    const matches = text.match(regex);
    if (matches) {
      const vars = matches.map((m) => m.slice(1, -1)); // Remover { y }
      return [...new Set(vars)]; // Eliminar duplicados
    }
    return [];
  }, []);

  // Actualizar variables detectadas cuando cambia el contenido
  useEffect(() => {
    const bodyVars = detectVariables(body);
    const subjectVars = detectVariables(subject);
    const allVars = [...new Set([...bodyVars, ...subjectVars])];
    setDetectedVars(allVars);
  }, [body, subject, detectVariables]);

  // Generar preview
  const handlePreview = async () => {
    if (mode === "create") {
      // En modo create, simulamos el preview localmente
      const previewBody = detectedVars.reduce((acc, varName) => {
        const value = previewVars[varName] || `[${varName}]`;
        return acc.replace(new RegExp(`\\{${varName}\\}`, "g"), value);
      }, body);
      
      const previewSubject = channel === "email" && subject
        ? detectedVars.reduce((acc, varName) => {
            const value = previewVars[varName] || `[${varName}]`;
            return acc.replace(new RegExp(`\\{${varName}\\}`, "g"), value);
          }, subject)
        : undefined;
      
      return {
        body: previewBody,
        subject: previewSubject,
        rendered_variables: previewVars,
        missing_variables: detectedVars.filter((v) => !previewVars[v]),
        extra_variables: [],
      };
    }
    
    return await previewMutation.mutateAsync(previewVars);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const data: CreateTemplateData = {
      name,
      description: description || undefined,
      channel,
      subject: channel === "email" ? subject : undefined,
      body,
      variables: detectedVars,
      is_active: isActive,
    };

    if (mode === "create") {
      await createMutation.mutateAsync(data);
    } else if (template) {
      await updateMutation.mutateAsync({
        id: template.template_id,
        payload: data,
      });
    }
    
    router.push("/message-templates");
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  // Insertar variable en el cursor
  const insertVariable = (variableName: string) => {
    const textarea = document.getElementById("body") as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newBody = body.substring(0, start) + `{${variableName}}` + body.substring(end);
      setBody(newBody);
      
      // Restaurar foco
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + variableName.length + 2, start + variableName.length + 2);
      }, 0);
    } else {
      setBody((prev) => prev + `{${variableName}}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">
            {mode === "create" ? "Nueva Plantilla" : "Editar Plantilla"}
          </h1>
          <p className="text-gray-600 mt-1">
            {mode === "create"
              ? "Crea una nueva plantilla para comunicaciones"
              : `Editando: ${template?.name}`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push("/message-templates")}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            <Save className="w-4 h-4 mr-2" />
            {mode === "create" ? "Crear Plantilla" : "Guardar Cambios"}
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="edit">Editar</TabsTrigger>
          <TabsTrigger value="preview">Vista Previa</TabsTrigger>
        </TabsList>

        <TabsContent value="edit" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Form */}
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Información General</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="name">
                      Nombre <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ej: Contacto Inicial WhatsApp"
                      required
                      minLength={3}
                      maxLength={100}
                    />
                  </div>

                  <div>
                    <Label htmlFor="description">Descripción</Label>
                    <Input
                      id="description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Breve descripción de cuándo usar esta plantilla"
                      maxLength={255}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="channel">
                        Canal <span className="text-red-500">*</span>
                      </Label>
                      <Select
                        value={channel}
                        onValueChange={(v) => setChannel(v as MessageChannel)}
                        disabled={mode === "edit" && template?.is_default}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {channelOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              <div className="flex items-center gap-2">
                                <opt.icon className="w-4 h-4" />
                                {opt.label}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="flex items-center justify-end pt-6">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="is_active"
                          checked={isActive}
                          onCheckedChange={setIsActive}
                        />
                        <Label htmlFor="is_active">Plantilla activa</Label>
                      </div>
                    </div>
                  </div>

                  {channel === "email" && (
                    <div>
                      <Label htmlFor="subject">
                        Asunto <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="subject"
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        placeholder="Ej: Oportunidad laboral: {role_title}"
                        required={channel === "email"}
                        maxLength={255}
                      />
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Contenido del Mensaje</CardTitle>
                </CardHeader>
                <CardContent>
                  <div>
                    <Label htmlFor="body">
                      Cuerpo del mensaje <span className="text-red-500">*</span>
                    </Label>
                    <Textarea
                      id="body"
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      placeholder={`Escribe el contenido de tu mensaje...

Usa las variables disponibles con el formato {nombre_variable}

Ejemplo:
¡Hola {candidate_name}! 👋

Soy {consultant_name} de Top Management. Te contacto sobre la posición de {role_title}...`}
                      required
                      minLength={10}
                      maxLength={10000}
                      className="min-h-[300px] font-mono text-sm"
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      {body.length} / 10000 caracteres
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Variables Disponibles</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-gray-500 mb-4">
                    Haz clic en una variable para insertarla
                  </p>
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {availableVars?.map((variable) => (
                      <TooltipProvider key={variable.name}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              onClick={() => insertVariable(variable.name)}
                              className="w-full text-left px-2 py-1.5 rounded hover:bg-gray-100 transition-colors text-sm"
                            >
                              <code className="text-blue-600 font-medium">
                                {"{"}{variable.name}{"}"}
                              </code>
                              <span className="text-gray-500 text-xs ml-2">
                                {variable.category}
                              </span>
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">{variable.description}</p>
                            {variable.example_value && (
                              <p className="text-xs text-gray-400 mt-1">
                                Ej: {variable.example_value}
                              </p>
                            )}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Variables Detectadas</CardTitle>
                </CardHeader>
                <CardContent>
                  {detectedVars.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {detectedVars.map((variable) => (
                        <Badge key={variable} variant="secondary" className="text-xs">
                          {"{"}{variable}{"}"}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">
                      No se han detectado variables. Usa el formato{" "}
                      <code>{"{variable_name}"}</code>
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="preview" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Configurar Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500 mb-4">
                Ingresa valores de ejemplo para las variables:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {detectedVars.map((varName) => (
                  <div key={varName}>
                    <Label htmlFor={`var-${varName}`} className="text-sm">
                      <code>{"{"}{varName}{"}"}</code>
                    </Label>
                    <Input
                      id={`var-${varName}`}
                      value={previewVars[varName] || ""}
                      onChange={(e) =>
                        setPreviewVars((prev) => ({
                          ...prev,
                          [varName]: e.target.value,
                        }))
                      }
                      placeholder={`Valor para ${varName}`}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resultado</CardTitle>
            </CardHeader>
            <CardContent>
              {previewMutation.isPending ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                </div>
              ) : (
                <div className="space-y-4">
                  {channel === "email" && (
                    <div className="border-b pb-4">
                      <Label className="text-xs text-gray-500">Asunto</Label>
                      <p className="font-medium">
                        {mode === "edit" && template
                          ? previewMutation.data?.subject || subject
                          : detectedVars.reduce((acc, varName) => {
                              const value = previewVars[varName] || `[${varName}]`;
                              return acc.replace(new RegExp(`\\{${varName}\\}`, "g"), value);
                            }, subject)}
                      </p>
                    </div>
                  )}
                  <div>
                    <Label className="text-xs text-gray-500">Cuerpo</Label>
                    <div className="mt-2 p-4 bg-gray-50 rounded-lg whitespace-pre-wrap font-mono text-sm">
                      {mode === "edit" && template
                        ? previewMutation.data?.body
                        : detectedVars.reduce((acc, varName) => {
                            const value = previewVars[varName] || `[${varName}]`;
                            return acc.replace(new RegExp(`\\{${varName}\\}`, "g"), value);
                          }, body)}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </form>
  );
}
