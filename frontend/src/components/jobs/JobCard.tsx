import { JobOpening, JobStatus } from "@/types/jobs";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Briefcase, MapPin, Users, Calendar, MoreHorizontal, Eye, Edit, Trash2, Pause, Play, XCircle } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";

interface JobCardProps {
  job: JobOpening;
  onEdit?: (job: JobOpening) => void;
  onDelete?: (job: JobOpening) => void;
  onClose?: (job: JobOpening) => void;
  onPause?: (job: JobOpening) => void;
  onActivate?: (job: JobOpening) => void;
}

const statusConfig: Record<JobStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  draft: { label: "Borrador", variant: "secondary" },
  active: { label: "Activa", variant: "default" },
  paused: { label: "Pausada", variant: "outline" },
  closed: { label: "Cerrada", variant: "destructive" },
};

export function JobCard({ job, onEdit, onDelete, onClose, onPause, onActivate }: JobCardProps) {
  const status = statusConfig[job.status];

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-lg truncate">{job.title}</h3>
              <Badge variant={status.variant}>{status.label}</Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{job.department}</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/dashboard/jobs/${job.id}`} className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  Ver detalles
                </Link>
              </DropdownMenuItem>
              {job.status !== 'closed' && (
                <DropdownMenuItem onClick={() => onEdit?.(job)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Editar
                </DropdownMenuItem>
              )}
              {job.status === 'active' && (
                <DropdownMenuItem onClick={() => onPause?.(job)}>
                  <Pause className="h-4 w-4 mr-2" />
                  Pausar
                </DropdownMenuItem>
              )}
              {job.status === 'paused' && (
                <DropdownMenuItem onClick={() => onActivate?.(job)}>
                  <Play className="h-4 w-4 mr-2" />
                  Activar
                </DropdownMenuItem>
              )}
              {(job.status === 'active' || job.status === 'paused') && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => onClose?.(job)} className="text-orange-600">
                    <XCircle className="h-4 w-4 mr-2" />
                    Cerrar oferta
                  </DropdownMenuItem>
                </>
              )}
              {job.status === 'draft' && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => onDelete?.(job)} className="text-red-600">
                    <Trash2 className="h-4 w-4 mr-2" />
                    Eliminar
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span className="truncate">{job.location}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Briefcase className="h-4 w-4" />
            <span className="truncate">{job.seniority}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="h-4 w-4" />
            <span>{job.candidate_count || 0} candidatos</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>{new Date(job.created_at).toLocaleDateString('es-ES')}</span>
          </div>
        </div>
        {job.assigned_consultant && (
          <div className="mt-3 pt-3 border-t">
            <p className="text-sm text-muted-foreground">
              Consultor: <span className="text-foreground font-medium">{job.assigned_consultant.full_name}</span>
            </p>
          </div>
        )}
      </CardContent>
      <CardFooter className="pt-0">
        <Link href={`/dashboard/jobs/${job.id}`} className="w-full">
          <Button variant="outline" className="w-full" size="sm">
            <Eye className="h-4 w-4 mr-2" />
            Ver detalles
          </Button>
        </Link>
      </CardFooter>
    </Card>
  );
}
