"use client";

import { useState } from "react";
import Link from "next/link";
import { useTemplates, useDeleteTemplate, useDuplicateTemplate } from "@/hooks/use-message-templates";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Search,
  Plus,
  Mail,
  MessageCircle,
  Smartphone,
  Edit,
  Copy,
  Trash2,
  Loader2,
  FileText,
} from "lucide-react";
import type { MessageTemplate, MessageChannel } from "@/types/message-templates";

const channelIcons: Record<MessageChannel, typeof Mail> = {
  email: Mail,
  whatsapp: MessageCircle,
  sms: Smartphone,
};

const channelColors: Record<MessageChannel, string> = {
  email: "bg-blue-100 text-blue-800 border-blue-200",
  whatsapp: "bg-green-100 text-green-800 border-green-200",
  sms: "bg-purple-100 text-purple-800 border-purple-200",
};

const channelLabels: Record<MessageChannel, string> = {
  email: "Email",
  whatsapp: "WhatsApp",
  sms: "SMS",
};

interface TemplateCardProps {
  template: MessageTemplate;
  onDelete: (template: MessageTemplate) => void;
  onDuplicate: (id: string) => void;
}

function TemplateCard({ template, onDelete, onDuplicate }: TemplateCardProps) {
  const Icon = channelIcons[template.channel];

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-lg truncate">{template.name}</h3>
              {template.is_default && (
                <Badge variant="outline" className="text-xs shrink-0">
                  Sistema
                </Badge>
              )}
            </div>
            
            {template.description && (
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                {template.description}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <Badge className={channelColors[template.channel]} variant="outline">
                <Icon className="w-3 h-3 mr-1" />
                {channelLabels[template.channel]}
              </Badge>
              
              {template.subject && (
                <span className="text-xs text-gray-500 truncate max-w-[200px]">
                  Asunto: {template.subject}
                </span>
              )}

              {!template.is_active && (
                <Badge variant="secondary" className="text-xs">
                  Inactiva
                </Badge>
              )}
            </div>

            {template.variables.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                <span className="text-xs text-gray-400 mr-1">Variables:</span>
                {template.variables.slice(0, 5).map((variable) => (
                  <code
                    key={variable}
                    className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600"
                  >
                    {"{"}{variable}{"}"}
                  </code>
                ))}
                {template.variables.length > 5 && (
                  <span className="text-xs text-gray-400">
                    +{template.variables.length - 5}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 shrink-0">
            <Link href={`/message-templates/${template.template_id}/edit`}>
              <Button variant="outline" size="sm" className="w-full">
                <Edit className="w-4 h-4 mr-1" />
                Editar
              </Button>
            </Link>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDuplicate(template.template_id)}
              className="w-full"
            >
              <Copy className="w-4 h-4 mr-1" />
              Duplicar
            </Button>
            
            {!template.is_default && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(template)}
                className="w-full text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Eliminar
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function MessageTemplatesPage() {
  const [search, setSearch] = useState("");
  const [channel, setChannel] = useState<MessageChannel | "all">("all");
  const [deleteTemplate, setDeleteTemplate] = useState<MessageTemplate | null>(null);

  const { data: templatesData, isLoading } = useTemplates({
    search: search || undefined,
    channel: channel === "all" ? undefined : channel,
    page: 1,
    page_size: 50,
  });

  const deleteMutation = useDeleteTemplate();
  const duplicateMutation = useDuplicateTemplate();

  const handleDelete = async () => {
    if (!deleteTemplate) return;
    await deleteMutation.mutateAsync(deleteTemplate.template_id);
    setDeleteTemplate(null);
  };

  const handleDuplicate = async (id: string) => {
    await duplicateMutation.mutateAsync(id);
  };

  const templates = templatesData?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Plantillas de Mensajes</h1>
          <p className="text-gray-600 mt-1">
            Gestiona las plantillas para comunicaciones con candidatos
          </p>
        </div>
        <Link href="/message-templates/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Nueva Plantilla
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Total Plantillas</p>
            <p className="text-2xl font-bold">{templatesData?.total || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Email</p>
            <p className="text-2xl font-bold">
              {templates.filter((t) => t.channel === "email").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">WhatsApp</p>
            <p className="text-2xl font-bold">
              {templates.filter((t) => t.channel === "whatsapp").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Activas</p>
            <p className="text-2xl font-bold">
              {templates.filter((t) => t.is_active).length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar por nombre o descripción..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={channel}
              onValueChange={(v) => setChannel(v as MessageChannel | "all")}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Canal" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los canales</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="whatsapp">WhatsApp</SelectItem>
                <SelectItem value="sms">SMS</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Templates List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : templates.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {templates.map((template) => (
            <TemplateCard
              key={template.template_id}
              template={template}
              onDelete={setDeleteTemplate}
              onDuplicate={handleDuplicate}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <FileText className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900">
            No se encontraron plantillas
          </h3>
          <p className="text-gray-500 mt-2">
            {search || channel !== "all"
              ? "Intenta ajustar los filtros de búsqueda"
              : "Crea tu primera plantilla para comenzar"}
          </p>
          {!search && channel === "all" && (
            <Link href="/message-templates/new">
              <Button className="mt-4">
                <Plus className="w-4 h-4 mr-2" />
                Crear Plantilla
              </Button>
            </Link>
          )}
        </div>
      )}

      {/* Delete Dialog */}
      <Dialog open={!!deleteTemplate} onOpenChange={() => setDeleteTemplate(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Eliminar plantilla?</DialogTitle>
            <DialogDescription>
              Esta acción no se puede deshacer. La plantilla{" "}
              <strong>{deleteTemplate?.name}</strong> se eliminará permanentemente.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTemplate(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
