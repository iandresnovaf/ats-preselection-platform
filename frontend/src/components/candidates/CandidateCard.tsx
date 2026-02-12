import { memo } from "react";
import { Candidate, CandidateStatus } from "@/types/candidates";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Mail, Phone, MapPin, Briefcase, Star, Calendar, MoreHorizontal, Eye, Edit, Trash2, Sparkles } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";

interface CandidateCardProps {
  candidate: Candidate;
  onEdit?: (candidate: Candidate) => void;
  onDelete?: (candidate: Candidate) => void;
  onEvaluate?: (candidate: Candidate) => void;
  onChangeStatus?: (candidate: Candidate) => void;
}

const statusConfig: Record<CandidateStatus, { label: string; color: string }> = {
  new: { label: "Nuevo", color: "bg-blue-100 text-blue-800" },
  screening: { label: "En revisión", color: "bg-yellow-100 text-yellow-800" },
  interview: { label: "Entrevista", color: "bg-purple-100 text-purple-800" },
  evaluation: { label: "Evaluación", color: "bg-orange-100 text-orange-800" },
  offer: { label: "Oferta", color: "bg-green-100 text-green-800" },
  hired: { label: "Contratado", color: "bg-emerald-100 text-emerald-800" },
  rejected: { label: "Rechazado", color: "bg-red-100 text-red-800" },
};

const sourceLabels: Record<string, string> = {
  email: "Email",
  manual: "Manual",
  zoho: "Zoho",
  linkedin: "LinkedIn",
  referral: "Referido",
  other: "Otro",
};

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-600";
  return "text-red-600";
}

function CandidateCardComponent({ candidate, onEdit, onDelete, onEvaluate, onChangeStatus }: CandidateCardProps) {
  const status = statusConfig[candidate.status];
  const fullName = `${candidate.first_name} ${candidate.last_name}`;
  const hasEvaluation = !!candidate.last_evaluation;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-lg truncate">{fullName}</h3>
              <span className={`text-xs px-2 py-1 rounded-full ${status.color}`}>
                {status.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{candidate.current_position || "Sin posición registrada"}</p>
            {candidate.job_opening && (
              <p className="text-xs text-muted-foreground mt-1">
                Para: <span className="font-medium">{candidate.job_opening.title}</span>
              </p>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/dashboard/candidates/${candidate.id}`} className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  Ver detalles
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onEdit?.(candidate)}>
                <Edit className="h-4 w-4 mr-2" />
                Editar
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onChangeStatus?.(candidate)}>
                <Briefcase className="h-4 w-4 mr-2" />
                Cambiar estado
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onDelete?.(candidate)} className="text-red-600">
                <Trash2 className="h-4 w-4 mr-2" />
                Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Mail className="h-4 w-4" />
            <span className="truncate">{candidate.email}</span>
          </div>
          {candidate.phone && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Phone className="h-4 w-4" />
              <span>{candidate.phone}</span>
            </div>
          )}
          {candidate.current_company && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Briefcase className="h-4 w-4" />
              <span>{candidate.current_company}</span>
              {candidate.years_experience !== undefined && (
                <span className="text-xs">({candidate.years_experience} años exp.)</span>
              )}
            </div>
          )}
          <div className="flex items-center gap-2 text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>{new Date(candidate.created_at).toLocaleDateString('es-ES')}</span>
            <span className="text-xs">({sourceLabels[candidate.source] || candidate.source})</span>
          </div>
        </div>

        {hasEvaluation && (
          <div className="mt-4 pt-3 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Última evaluación:</span>
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4" />
                <span className={`font-semibold ${getScoreColor(candidate.last_evaluation!.score)}`}>
                  {candidate.last_evaluation!.score}/100
                </span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {new Date(candidate.last_evaluation!.created_at).toLocaleDateString('es-ES')}
            </p>
          </div>
        )}
      </CardContent>
      <CardFooter className="flex gap-2 pt-0">
        <Link href={`/dashboard/candidates/${candidate.id}`} className="flex-1">
          <Button variant="outline" className="w-full" size="sm">
            <Eye className="h-4 w-4 mr-2" />
            Ver
          </Button>
        </Link>
        <Button 
          variant="secondary" 
          className="flex-1" 
          size="sm"
          onClick={() => onEvaluate?.(candidate)}
        >
          <Sparkles className="h-4 w-4 mr-2" />
          Evaluar
        </Button>
      </CardFooter>
    </Card>
  );
}

// Memoize para evitar re-renders innecesarios
export const CandidateCard = memo(CandidateCardComponent);
