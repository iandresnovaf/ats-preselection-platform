"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Edit2, Check, X, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExtractedRoleData } from "./RoleDocumentUploader";

interface RoleDataPreviewProps {
  data: ExtractedRoleData;
  onConfirm: (data: Partial<ExtractedRoleData>) => void;
  onCancel: () => void;
}

type EditMode = {
  [key: string]: boolean;
};

export function RoleDataPreview({ data, onConfirm, onCancel }: RoleDataPreviewProps) {
  const [editedData, setEditedData] = useState<ExtractedRoleData>(data);
  const [editMode, setEditMode] = useState<EditMode>({});
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["basic", "hierarchy", "requirements"])
  );

  // Reset edited data when new data comes in
  useEffect(() => {
    setEditedData(data);
  }, [data]);

  const toggleEdit = (field: string) => {
    setEditMode((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const handleSave = () => {
    onConfirm(editedData);
  };

  const updateField = (path: string, value: any) => {
    setEditedData((prev) => {
      const newData = { ...prev };
      const keys = path.split(".");
      let current: any = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = value;
      return newData;
    });
  };

  const SectionHeader = ({
    title,
    section,
    icon: Icon,
  }: {
    title: string;
    section: string;
    icon?: React.ElementType;
  }) => (
    <button
      onClick={() => toggleSection(section)}
      className="flex items-center justify-between w-full py-2 text-left hover:bg-gray-50 rounded-lg px-2 -mx-2 transition-colors"
    >
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-gray-500" />}
        <h3 className="font-semibold text-gray-900">{title}</h3>
      </div>
      {expandedSections.has(section) ? (
        <ChevronUp className="w-4 h-4 text-gray-400" />
      ) : (
        <ChevronDown className="w-4 h-4 text-gray-400" />
      )}
    </button>
  );

  const EditableField = ({
    label,
    value,
    path,
    multiline = false,
  }: {
    label: string;
    value: string;
    path: string;
    multiline?: boolean;
  }) => {
    const isEditing = editMode[path];

    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-medium text-gray-500 uppercase">
            {label}
          </Label>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => toggleEdit(path)}
          >
            {isEditing ? (
              <X className="w-3 h-3" />
            ) : (
              <Edit2 className="w-3 h-3" />
            )}
          </Button>
        </div>
        {isEditing ? (
          multiline ? (
            <Textarea
              value={value}
              onChange={(e) => updateField(path, e.target.value)}
              className="min-h-[100px]"
              autoFocus
              onBlur={() => toggleEdit(path)}
            />
          ) : (
            <Input
              value={value}
              onChange={(e) => updateField(path, e.target.value)}
              autoFocus
              onBlur={() => toggleEdit(path)}
              onKeyDown={(e) => {
                if (e.key === "Enter") toggleEdit(path);
              }}
            />
          )
        ) : (
          <div
            className={cn(
              "text-sm text-gray-900",
              multiline && "whitespace-pre-wrap",
              !value && "text-gray-400 italic"
            )}
            onClick={() => toggleEdit(path)}
          >
            {value || "No especificado"}
          </div>
        )}
      </div>
    );
  };

  const ListField = ({
    label,
    items,
    path,
  }: {
    label: string;
    items: string[];
    path: string;
  }) => {
    const [newItem, setNewItem] = useState("");

    const addItem = () => {
      if (newItem.trim()) {
        updateField(path, [...items, newItem.trim()]);
        setNewItem("");
      }
    };

    const removeItem = (index: number) => {
      updateField(
        path,
        items.filter((_, i) => i !== index)
      );
    };

    return (
      <div className="space-y-2">
        <Label className="text-xs font-medium text-gray-500 uppercase">
          {label}
        </Label>
        <div className="flex flex-wrap gap-2">
          {items.map((item, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1 px-2 py-1"
            >
              {item}
              <button
                onClick={() => removeItem(index)}
                className="ml-1 text-gray-400 hover:text-red-500"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2 mt-2">
          <Input
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            placeholder="Agregar nuevo..."
            className="flex-1"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addItem();
              }
            }}
          />
          <Button type="button" size="sm" onClick={addItem}>
            Agregar
          </Button>
        </div>
      </div>
    );
  };

  return (
    <Card className="border-green-200">
      <CardHeader className="bg-green-50 border-b border-green-100">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg text-green-900">
              Datos Extraídos del Documento
            </CardTitle>
            <p className="text-sm text-green-700 mt-1">
              Revise y edite la información antes de crear la vacante
            </p>
          </div>
          {data.metadata?.extraction_warnings?.length > 0 && (
            <div className="flex items-center gap-2 text-amber-600 bg-amber-50 px-3 py-1 rounded-full text-sm">
              <AlertCircle className="w-4 h-4" />
              {data.metadata.extraction_warnings.length} advertencias
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6 pt-6">
        {/* Información Básica */}
        <div className="border rounded-lg p-4">
          <SectionHeader title="Información Básica" section="basic" />
          {expandedSections.has("basic") && (
            <div className="mt-4 space-y-4">
              <EditableField
                label="Título del Cargo"
                value={editedData.role_title}
                path="role_title"
              />
              <EditableField
                label="Objetivo del Rol"
                value={editedData.objective}
                path="objective"
                multiline
              />
              <EditableField
                label="Descripción Completa"
                value={editedData.description}
                path="description"
                multiline
              />
            </div>
          )}
        </div>

        {/* Jerarquía */}
        <div className="border rounded-lg p-4">
          <SectionHeader title="Estructura del Cargo" section="hierarchy" />
          {expandedSections.has("hierarchy") && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <EditableField
                label="Reporta a"
                value={editedData.hierarchy.reports_to}
                path="hierarchy.reports_to"
              />
              <EditableField
                label="Nivel"
                value={editedData.hierarchy.level}
                path="hierarchy.level"
              />
              <EditableField
                label="Personas a Cargo"
                value={editedData.hierarchy.direct_reports}
                path="hierarchy.direct_reports"
              />
              <EditableField
                label="Modalidad"
                value={editedData.hierarchy.work_mode}
                path="hierarchy.work_mode"
              />
              <EditableField
                label="Ubicación"
                value={editedData.hierarchy.location}
                path="hierarchy.location"
              />
            </div>
          )}
        </div>

        {/* Requisitos */}
        <div className="border rounded-lg p-4">
          <SectionHeader title="Perfil Requerido" section="requirements" />
          {expandedSections.has("requirements") && (
            <div className="mt-4 space-y-4">
              <EditableField
                label="Formación"
                value={editedData.requirements.education}
                path="requirements.education"
                multiline
              />
              <EditableField
                label="Años de Experiencia"
                value={editedData.requirements.experience_years}
                path="requirements.experience_years"
              />
              <EditableField
                label="Detalles de Experiencia"
                value={editedData.requirements.experience_details}
                path="requirements.experience_details"
                multiline
              />
            </div>
          )}
        </div>

        {/* Responsabilidades */}
        <div className="border rounded-lg p-4">
          <SectionHeader title="Responsabilidades" section="responsibilities" />
          {expandedSections.has("responsibilities") && (
            <div className="mt-4 space-y-4">
              {Object.entries(editedData.responsibilities).map(
                ([category, items]) => (
                  <div key={category} className="border-l-2 border-gray-200 pl-4">
                    <h4 className="font-medium text-gray-700 mb-2">{category}</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {items.map((item, index) => (
                        <li key={index} className="text-sm text-gray-600">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              )}
              {Object.keys(editedData.responsibilities).length === 0 && (
                <p className="text-sm text-gray-400 italic">
                  No se encontraron responsabilidades
                </p>
              )}
            </div>
          )}
        </div>

        {/* Skills */}
        <div className="border rounded-lg p-4">
          <SectionHeader title="Habilidades y Competencias" section="skills" />
          {expandedSections.has("skills") && (
            <div className="mt-4 space-y-4">
              <ListField
                label="Conocimientos Técnicos"
                items={editedData.skills.technical}
                path="skills.technical"
              />
              <ListField
                label="Competencias Blandas"
                items={editedData.skills.soft}
                path="skills.soft"
              />
            </div>
          )}
        </div>

        {/* Herramientas y DISC */}
        <div className="border rounded-lg p-4">
          <SectionHeader title="Herramientas y Perfil DISC" section="tools" />
          {expandedSections.has("tools") && (
            <div className="mt-4 space-y-4">
              <ListField
                label="Herramientas y Software"
                items={editedData.tools}
                path="tools"
              />
              {editedData.disc_profile && (
                <EditableField
                  label="Perfil DISC Esperado"
                  value={editedData.disc_profile}
                  path="disc_profile"
                />
              )}
            </div>
          )}
        </div>

        {/* Secciones encontradas */}
        {data.metadata?.sections_found && (
          <div className="text-xs text-gray-500">
            <p className="font-medium mb-1">Secciones detectadas:</p>
            <div className="flex flex-wrap gap-1">
              {data.metadata.sections_found.map((section) => (
                <Badge key={section} variant="outline" className="text-xs">
                  {section}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end gap-4 pt-4 border-t">
          <Button variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
          <Button onClick={handleSave} className="gap-2">
            <Check className="w-4 h-4" />
            Confirmar y Crear Vacante
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}