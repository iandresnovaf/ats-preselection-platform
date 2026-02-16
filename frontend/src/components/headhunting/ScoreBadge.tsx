"use client";

import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg" | "xl";
  showLabel?: boolean;
  className?: string;
}

/**
 * Componente ScoreBadge
 * Muestra un score 0-100 con colores semánticos:
 * - 80-100: Verde (Excelente)
 * - 60-79: Amarillo (Aceptable)
 * - 0-59: Rojo (Necesita mejora)
 */
export function ScoreBadge({
  score,
  size = "md",
  showLabel = false,
  className,
}: ScoreBadgeProps) {
  // Determinar color basado en score
  const getColorClass = (s: number): string => {
    if (s >= 80) return "bg-green-100 text-green-800 border-green-200";
    if (s >= 60) return "bg-yellow-100 text-yellow-800 border-yellow-200";
    return "bg-red-100 text-red-800 border-red-200";
  };

  const getLabel = (s: number): string => {
    if (s >= 80) return "Excelente";
    if (s >= 60) return "Aceptable";
    return "Necesita mejora";
  };

  // Tamaños
  const sizeClasses = {
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-2.5 py-1",
    lg: "text-base px-3 py-1.5",
    xl: "text-2xl px-4 py-2 font-bold",
  };

  // Círculo de progreso para tamaño xl
  const renderCircle = () => {
    if (size !== "xl") return null;
    
    const radius = 36;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (score / 100) * circumference;
    
    const strokeColor = score >= 80 ? "#22c55e" : score >= 60 ? "#eab308" : "#ef4444";
    
    return (
      <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 80 80">
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="6"
        />
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500"
        />
      </svg>
    );
  };

  if (size === "xl") {
    return (
      <div className={cn("flex flex-col items-center gap-2", className)}>
        <div className="relative">
          {renderCircle()}
          <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold">
            {score}
          </span>
        </div>
        {showLabel && (
          <span className={cn("text-sm font-medium", 
            score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-600" : "text-red-600"
          )}>
            {getLabel(score)}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-full border font-medium",
          sizeClasses[size],
          getColorClass(score)
        )}
        title={`Score: ${score}/100`}
      >
        {score}
      </span>
      {showLabel && (
        <span className="text-sm text-gray-600">{getLabel(score)}</span>
      )}
    </div>
  );
}

/**
 * Versión simplificada - solo el número con color
 */
export function ScoreValue({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const colorClass = score >= 80 
    ? "text-green-600" 
    : score >= 60 
    ? "text-yellow-600" 
    : "text-red-600";

  return (
    <span className={cn("font-semibold", colorClass, className)}>
      {score}
    </span>
  );
}

/**
 * Barra de progreso horizontal para scores
 */
export function ScoreBar({
  score,
  height = "h-2",
  showValue = true,
  className,
}: {
  score: number;
  height?: string;
  showValue?: boolean;
  className?: string;
}) {
  const colorClass = score >= 80 
    ? "bg-green-500" 
    : score >= 60 
    ? "bg-yellow-500" 
    : "bg-red-500";

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className={cn("flex-1 bg-gray-200 rounded-full overflow-hidden", height)}>
        <div
          className={cn("transition-all duration-500 rounded-full", colorClass)}
          style={{ width: `${score}%` }}
        />
      </div>
      {showValue && (
        <ScoreValue score={score} className="text-sm w-8 text-right" />
      )}
    </div>
  );
}
