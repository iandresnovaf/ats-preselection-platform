"use client";

import { cn } from "@/lib/utils";
import { CheckCircle, Circle, Clock, AlertCircle, User } from "lucide-react";
import type { PipelineStage, StageTransition } from "@/types/headhunting";
import { getStageLabel, PIPELINE_STAGES } from "@/types/headhunting";

interface TimelineStageProps {
  stage: PipelineStage;
  isActive?: boolean;
  isCompleted?: boolean;
  isLast?: boolean;
  date?: string;
  responsible?: string;
  notes?: string;
  onClick?: () => void;
  className?: string;
}

/**
 * Componente TimelineStage
 * Visualiza una etapa del pipeline con su estado
 */
export function TimelineStageItem({
  stage,
  isActive = false,
  isCompleted = false,
  isLast = false,
  date,
  responsible,
  notes,
  onClick,
  className,
}: TimelineStageProps) {
  const label = getStageLabel(stage);

  // Icono según estado
  const getIcon = () => {
    if (isCompleted) {
      return (
        <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
          <CheckCircle className="w-5 h-5 text-white" />
        </div>
      );
    }
    if (isActive) {
      return (
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center ring-4 ring-blue-100">
          <Clock className="w-5 h-5 text-white" />
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
        <Circle className="w-5 h-5 text-gray-400" />
      </div>
    );
  };

  return (
    <div
      className={cn(
        "flex gap-4",
        onClick && "cursor-pointer",
        className
      )}
      onClick={onClick}
    >
      {/* Icono y línea */}
      <div className="flex flex-col items-center">
        {getIcon()}
        {!isLast && (
          <div
            className={cn(
              "w-0.5 flex-1 min-h-[40px]",
              isCompleted ? "bg-green-500" : "bg-gray-200"
            )}
          />
        )}
      </div>

      {/* Contenido */}
      <div
        className={cn(
          "flex-1 pb-6",
          isActive && "bg-blue-50/50 -mx-2 px-2 py-2 rounded-lg -mt-2"
        )}
      >
        <h4
          className={cn(
            "font-medium",
            isActive ? "text-blue-700" : isCompleted ? "text-green-700" : "text-gray-500"
          )}
        >
          {label}
        </h4>

        {date && (
          <p className="text-xs text-gray-500 mt-0.5">
            {new Date(date).toLocaleDateString("es-ES", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </p>
        )}

        {responsible && (
          <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
            <User className="w-3 h-3" />
            <span>{responsible}</span>
          </div>
        )}

        {notes && (
          <p className="text-sm text-gray-600 mt-2 bg-white p-2 rounded border border-gray-100">
            {notes}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Timeline completo del pipeline
 */
interface PipelineTimelineProps {
  currentStage: PipelineStage;
  transitions?: StageTransition[];
  onStageClick?: (stage: PipelineStage) => void;
  className?: string;
}

export function PipelineTimeline({
  currentStage,
  transitions = [],
  onStageClick,
  className,
}: PipelineTimelineProps) {
  const currentOrder = PIPELINE_STAGES.find(s => s.value === currentStage)?.order || 0;
  
  // Crear mapa de transiciones
  const transitionMap = new Map<string, StageTransition>();
  transitions.forEach(t => {
    transitionMap.set(t.to_stage, t);
  });

  // Filtrar etapas relevantes (no mostrar rejected en el flujo normal)
  const stages = PIPELINE_STAGES.filter(s => s.value !== "rejected");

  return (
    <div className={cn("space-y-0", className)}>
      {stages.map((stage, index) => {
        const stageOrder = stage.order;
        const isCompleted = stageOrder < currentOrder;
        const isActive = stage.value === currentStage;
        const isLast = index === stages.length - 1;
        
        const transition = transitionMap.get(stage.value);

        return (
          <TimelineStageItem
            key={stage.value}
            stage={stage.value}
            isActive={isActive}
            isCompleted={isCompleted}
            isLast={isLast}
            date={transition?.created_at}
            responsible={transition?.changed_by_user?.full_name}
            notes={transition?.notes}
            onClick={onStageClick ? () => onStageClick(stage.value) : undefined}
          />
        );
      })}

      {/* Si está rechazado, mostrarlo al final */}
      {currentStage === "rejected" && (
        <TimelineStageItem
          stage="rejected"
          isActive={true}
          isLast={true}
          date={transitionMap.get("rejected")?.created_at}
          responsible={transitionMap.get("rejected")?.changed_by_user?.full_name}
          notes={transitionMap.get("rejected")?.notes}
        />
      )}
    </div>
  );
}

/**
 * Mini timeline horizontal (para cards)
 */
interface MiniPipelineProps {
  currentStage: PipelineStage;
  className?: string;
}

export function MiniPipeline({ currentStage, className }: MiniPipelineProps) {
  const currentOrder = PIPELINE_STAGES.find(s => s.value === currentStage)?.order || 0;
  const stages = PIPELINE_STAGES.filter(s => s.value !== "rejected");

  return (
    <div className={cn("flex items-center gap-1", className)}>
      {stages.map((stage, index) => {
        const isCompleted = stage.order < currentOrder;
        const isActive = stage.value === currentStage;

        return (
          <div key={stage.value} className="flex items-center">
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                isActive && "w-3 h-3 ring-2 ring-blue-200",
                isCompleted ? "bg-green-500" : isActive ? "bg-blue-500" : "bg-gray-200"
              )}
              title={stage.label}
            />
            {index < stages.length - 1 && (
              <div
                className={cn(
                  "w-4 h-0.5",
                  isCompleted ? "bg-green-500" : "bg-gray-200"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Badge de etapa actual
 */
interface StageBadgeProps {
  stage: PipelineStage;
  className?: string;
}

export function StageBadge({ stage, className }: StageBadgeProps) {
  const config: Record<PipelineStage, { bg: string; text: string; label: string }> = {
    sourcing: { bg: "bg-gray-100", text: "text-gray-700", label: "Sourcing" },
    shortlist: { bg: "bg-blue-100", text: "text-blue-700", label: "Pre-selección" },
    terna: { bg: "bg-purple-100", text: "text-purple-700", label: "Terna" },
    interview: { bg: "bg-orange-100", text: "text-orange-700", label: "Entrevista" },
    offer: { bg: "bg-yellow-100", text: "text-yellow-700", label: "Oferta" },
    hired: { bg: "bg-green-100", text: "text-green-700", label: "Contratado" },
    rejected: { bg: "bg-red-100", text: "text-red-700", label: "Rechazado" },
  };

  const { bg, text, label } = config[stage];

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        bg,
        text,
        className
      )}
    >
      {label}
    </span>
  );
}
