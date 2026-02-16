"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Bot,
  User,
  Settings,
  CheckCircle,
  XCircle,
} from "lucide-react";
import type { ApplicationFlag, FlagSeverity, FlagCategory } from "@/types/headhunting";

interface FlagCardProps {
  flag: ApplicationFlag;
  onResolve?: (id: string, notes?: string) => void;
  onDismiss?: (id: string) => void;
  compact?: boolean;
  className?: string;
}

/**
 * Componente FlagCard
 * Muestra una alerta/flag con severidad, categoría y evidencia
 */
export function FlagCard({
  flag,
  onResolve,
  onDismiss,
  compact = false,
  className,
}: FlagCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState("");

  // Configuración por severidad
  const severityConfig: Record<FlagSeverity, {
    icon: React.ReactNode;
    badge: string;
    border: string;
    bg: string;
    label: string;
  }> = {
    high: {
      icon: <AlertTriangle className="w-4 h-4" />,
      badge: "bg-red-100 text-red-800 border-red-200",
      border: "border-red-300",
      bg: "bg-red-50",
      label: "Alto",
    },
    medium: {
      icon: <AlertCircle className="w-4 h-4" />,
      badge: "bg-yellow-100 text-yellow-800 border-yellow-200",
      border: "border-yellow-300",
      bg: "bg-yellow-50",
      label: "Medio",
    },
    low: {
      icon: <Info className="w-4 h-4" />,
      badge: "bg-blue-100 text-blue-800 border-blue-200",
      border: "border-blue-300",
      bg: "bg-blue-50",
      label: "Bajo",
    },
  };

  // Labels de categorías
  const categoryLabels: Record<FlagCategory, string> = {
    skills_gap: "Brecha de habilidades",
    experience_mismatch: "Experiencia no coincide",
    salary_expectation: "Expectativa salarial",
    availability: "Disponibilidad",
    relocation: "Reubicación",
    culture_fit: "Cultura organizacional",
    reference_issue: "Problema con referencias",
    background_check: "Verificación de antecedentes",
    other: "Otro",
  };

  // Icono por fuente
  const getSourceIcon = (source: string) => {
    switch (source) {
      case "ai":
        return <Bot className="w-3 h-3" />;
      case "manual":
        return <User className="w-3 h-3" />;
      case "system":
        return <Settings className="w-3 h-3" />;
      default:
        return null;
    }
  };

  const config = severityConfig[flag.severity];

  // Versión compacta (para listas)
  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                "flex items-center gap-2 px-2 py-1 rounded-lg border",
                config.border,
                config.bg,
                className
              )}
            >
              {config.icon}
              <span className="text-xs font-medium truncate max-w-[150px]">
                {categoryLabels[flag.category]}
              </span>
            </div>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <p className="font-medium">{flag.description}</p>
            {flag.evidence && (
              <p className="text-xs text-gray-500 mt-1">{flag.evidence}</p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div
        className={cn(
          "rounded-lg border p-4",
          config.border,
          config.bg,
          flag.resolved && "opacity-60 bg-gray-50 border-gray-200",
          className
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            {config.icon}
            <Badge variant="outline" className={config.badge}>
              {config.label}
            </Badge>
            <span className="text-xs text-gray-500">
              {categoryLabels[flag.category]}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="flex items-center gap-1 text-xs text-gray-400"
              title={`Fuente: ${flag.source}`}
            >
              {getSourceIcon(flag.source)}
              {flag.source === "ai" ? "IA" : flag.source === "manual" ? "Manual" : "Sistema"}
            </span>
            {flag.evidence && (
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="mt-2 text-sm text-gray-800">{flag.description}</p>

        {/* Evidence (expandable) */}
        {flag.evidence && (
          <CollapsibleContent>
            <div className="mt-3 p-3 bg-white/60 rounded border border-gray-200">
              <p className="text-xs font-medium text-gray-500 mb-1">Evidencia:</p>
              <p className="text-sm text-gray-700">{flag.evidence}</p>
            </div>
          </CollapsibleContent>
        )}

        {/* Footer */}
        <div className="mt-3 flex items-center justify-between">
          <div className="text-xs text-gray-400">
            {flag.created_by_user ? (
              <span>Por: {flag.created_by_user.full_name}</span>
            ) : (
              <span>Automático</span>
            )}
            <span className="mx-1">•</span>
            <span>{new Date(flag.created_at).toLocaleDateString("es-ES")}</span>
          </div>

          {/* Actions */}
          {!flag.resolved ? (
            <div className="flex items-center gap-2">
              {onResolve && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => onResolve(flag.id, resolutionNotes)}
                >
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Resolver
                </Button>
              )}
              {onDismiss && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-gray-400 hover:text-red-500"
                  onClick={() => onDismiss(flag.id)}
                >
                  <XCircle className="w-3 h-3 mr-1" />
                  Descartar
                </Button>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-green-600">
              <CheckCircle className="w-3 h-3" />
              <span>Resuelto</span>
              {flag.resolved_at && (
                <span className="text-gray-400">
                  el {new Date(flag.resolved_at).toLocaleDateString("es-ES")}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </Collapsible>
  );
}

/**
 * Lista de flags agrupados por severidad
 */
interface FlagListProps {
  flags: ApplicationFlag[];
  onResolve?: (id: string, notes?: string) => void;
  onDismiss?: (id: string) => void;
  showResolved?: boolean;
  className?: string;
}

export function FlagList({
  flags,
  onResolve,
  onDismiss,
  showResolved = false,
  className,
}: FlagListProps) {
  const filteredFlags = showResolved 
    ? flags 
    : flags.filter(f => !f.resolved);

  const groupedFlags = {
    high: filteredFlags.filter(f => f.severity === "high" && !f.resolved),
    medium: filteredFlags.filter(f => f.severity === "medium" && !f.resolved),
    low: filteredFlags.filter(f => f.severity === "low" && !f.resolved),
    resolved: filteredFlags.filter(f => f.resolved),
  };

  if (filteredFlags.length === 0) {
    return (
      <div className={cn("text-center py-8 text-gray-400", className)}>
        <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No hay alertas pendientes</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {groupedFlags.high.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-red-600 uppercase tracking-wide">
            Alertas Críticas ({groupedFlags.high.length})
          </h4>
          {groupedFlags.high.map(flag => (
            <FlagCard
              key={flag.id}
              flag={flag}
              onResolve={onResolve}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}

      {groupedFlags.medium.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-yellow-600 uppercase tracking-wide">
            Advertencias ({groupedFlags.medium.length})
          </h4>
          {groupedFlags.medium.map(flag => (
            <FlagCard
              key={flag.id}
              flag={flag}
              onResolve={onResolve}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}

      {groupedFlags.low.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-blue-600 uppercase tracking-wide">
            Observaciones ({groupedFlags.low.length})
          </h4>
          {groupedFlags.low.map(flag => (
            <FlagCard
              key={flag.id}
              flag={flag}
              onResolve={onResolve}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}

      {showResolved && groupedFlags.resolved.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Resueltas ({groupedFlags.resolved.length})
          </h4>
          {groupedFlags.resolved.map(flag => (
            <FlagCard
              key={flag.id}
              flag={flag}
              onResolve={onResolve}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}
    </div>
  );
}
