"use client";

import { useParams } from "next/navigation";
import { useTemplate } from "@/hooks/use-message-templates";
import TemplateForm from "@/components/message-templates/template-form";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export default function EditTemplatePage() {
  const params = useParams();
  const templateId = params.id as string;
  
  const { data: template, isLoading } = useTemplate(templateId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!template) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <h2 className="text-lg font-medium">Plantilla no encontrada</h2>
          <p className="text-gray-500 mt-2">
            La plantilla que buscas no existe o no tienes permisos para verla.
          </p>
        </CardContent>
      </Card>
    );
  }

  return <TemplateForm template={template} mode="edit" />;
}
