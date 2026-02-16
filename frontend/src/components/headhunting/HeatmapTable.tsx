"use client";

import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScoreValue } from "./ScoreBadge";
import type { AssessmentScore } from "@/types/headhunting";

interface HeatmapTableProps {
  dimensions: string[];
  candidates: {
    id: string;
    name: string;
    photo_url?: string;
    scores: Record<string, number>; // dimension -> score
    overall_score: number;
  }[];
  className?: string;
}

/**
 * Componente HeatmapTable
 * Tabla comparativa con colores por score
 * Filas: dimensiones | Columnas: candidatos
 */
export function HeatmapTable({
  dimensions,
  candidates,
  className,
}: HeatmapTableProps) {
  // Función para determinar el color de fondo según el score
  const getHeatmapColor = (score: number): string => {
    if (score >= 90) return "bg-green-500 text-white";
    if (score >= 80) return "bg-green-400 text-white";
    if (score >= 70) return "bg-green-300 text-gray-900";
    if (score >= 60) return "bg-yellow-300 text-gray-900";
    if (score >= 50) return "bg-yellow-400 text-gray-900";
    if (score >= 40) return "bg-orange-300 text-gray-900";
    if (score >= 30) return "bg-orange-400 text-white";
    return "bg-red-500 text-white";
  };

  if (candidates.length === 0) {
    return (
      <div className={cn("text-center py-8 text-gray-400", className)}>
        <p>No hay candidatos para comparar</p>
      </div>
    );
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="sticky left-0 bg-white z-10 min-w-[150px]">
              Dimensión
            </TableHead>
            {candidates.map((candidate) => (
              <TableHead
                key={candidate.id}
                className="text-center min-w-[100px]"
              >
                <div className="flex flex-col items-center gap-1">
                  {candidate.photo_url ? (
                    <img
                      src={candidate.photo_url}
                      alt={candidate.name}
                      className="w-10 h-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-sm font-medium text-gray-600">
                      {candidate.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
                    </div>
                  )}
                  <span className="text-xs font-medium truncate max-w-[100px]">
                    {candidate.name}
                  </span>
                  <span className="text-xs font-bold text-blue-600">
                    {candidate.overall_score}
                  </span>
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {dimensions.map((dimension) => (
            <TableRow key={dimension}>
              <TableCell className="sticky left-0 bg-white z-10 font-medium">
                {dimension}
              </TableCell>
              {candidates.map((candidate) => {
                const score = candidate.scores[dimension] ?? 0;
                return (
                  <TableCell key={candidate.id} className="p-0">
                    <div
                      className={cn(
                        "flex items-center justify-center py-3 font-semibold text-sm transition-colors",
                        getHeatmapColor(score)
                      )}
                      title={`${dimension}: ${score}/100`}
                    >
                      {score}
                    </div>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
          
          {/* Fila de Overall Score */}
          <TableRow className="border-t-2 border-gray-300">
            <TableCell className="sticky left-0 bg-white z-10 font-bold">
              Score General
            </TableCell>
            {candidates.map((candidate) => (
              <TableCell key={candidate.id} className="p-0">
                <div
                  className={cn(
                    "flex items-center justify-center py-3 font-bold text-lg",
                    getHeatmapColor(candidate.overall_score)
                  )}
                >
                  {candidate.overall_score}
                </div>
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>

      {/* Leyenda */}
      <div className="flex items-center justify-center gap-4 mt-4 text-xs">
        <span className="text-gray-500">Score:</span>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-red-500 rounded" />
          <span>0-39</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-orange-400 rounded" />
          <span>40-59</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-yellow-300 rounded" />
          <span>60-79</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-400 rounded" />
          <span>80-89</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-500 rounded" />
          <span>90-100</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Versión simplificada - solo una fila por candidato
 */
interface CompactHeatmapProps {
  candidates: {
    id: string;
    name: string;
    scores: Record<string, number>;
    overall_score: number;
  }[];
  dimensions: string[];
  className?: string;
}

export function CompactHeatmap({
  candidates,
  dimensions,
  className,
}: CompactHeatmapProps) {
  const getHeatmapColor = (score: number): string => {
    if (score >= 90) return "bg-green-500";
    if (score >= 80) return "bg-green-400";
    if (score >= 70) return "bg-green-300";
    if (score >= 60) return "bg-yellow-300";
    if (score >= 50) return "bg-yellow-400";
    if (score >= 40) return "bg-orange-300";
    if (score >= 30) return "bg-orange-400";
    return "bg-red-500";
  };

  return (
    <div className={cn("space-y-3", className)}>
      {candidates.map((candidate) => (
        <div
          key={candidate.id}
          className="p-3 rounded-lg border hover:shadow-sm transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">{candidate.name}</span>
            <ScoreValue score={candidate.overall_score} className="text-lg" />
          </div>
          
          <div className="grid grid-cols-2 gap-2">
            {dimensions.slice(0, 4).map((dim) => {
              const score = candidate.scores[dim] ?? 0;
              return (
                <div key={dim} className="flex items-center gap-2">
                  <div
                    className={cn("w-3 h-3 rounded-full", getHeatmapColor(score))}
                    title={`${dim}: ${score}`}
                  />
                  <span className="text-xs text-gray-600 truncate flex-1">{dim}</span>
                  <span className="text-xs font-medium">{score}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Barra de comparación de scores
 */
interface ScoreComparisonBarProps {
  candidates: {
    id: string;
    name: string;
    score: number;
    color?: string;
  }[];
  maxScore?: number;
  className?: string;
}

export function ScoreComparisonBar({
  candidates,
  maxScore = 100,
  className,
}: ScoreComparisonBarProps) {
  const colors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-purple-500",
    "bg-orange-500",
    "bg-pink-500",
    "bg-cyan-500",
    "bg-indigo-500",
    "bg-red-500",
  ];

  return (
    <div className={cn("space-y-3", className)}>
      {candidates.map((candidate, index) => (
        <div key={candidate.id}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium">{candidate.name}</span>
            <span className="text-sm font-bold">{candidate.score}</span>
          </div>
          <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                candidate.color || colors[index % colors.length]
              )}
              style={{ width: `${(candidate.score / maxScore) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
