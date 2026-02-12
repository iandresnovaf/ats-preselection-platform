"use client";

import { useState, useCallback } from "react";
import { Submission, PipelineStage, SubmissionStatus } from "@/types/rhtools";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { 
  Clock, 
  AlertCircle, 
  User, 
  Briefcase, 
  Building2, 
  DollarSign, 
  MoreHorizontal,
  Eye,
  History,
  FileText,
  AlertTriangle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import { submissionsService } from "@/services/rhtools/submissions";
import Link from "next/link";

interface PipelineKanbanProps {
  stages: PipelineStage[];
  submissions: Submission[];
  onSubmissionMove?: (submissionId: string, toStageId: string) => void;
  onRefresh?: () => void;
  readOnly?: boolean;
}

interface DragState {
  submissionId: string | null;
  fromStageId: string | null;
}

const priorityConfig: Record<string, { label: string; color: string }> = {
  low: { label: "Baja", color: "bg-slate-100 text-slate-700" },
  medium: { label: "Media", color: "bg-blue-100 text-blue-700" },
  high: { label: "Alta", color: "bg-orange-100 text-orange-700" },
  urgent: { label: "Urgente", color: "bg-red-100 text-red-700" },
};

export function PipelineKanban({ 
  stages, 
  submissions, 
  onSubmissionMove, 
  onRefresh,
  readOnly = false 
}: PipelineKanbanProps) {
  const { toast } = useToast();
  const [dragState, setDragState] = useState<DragState>({ submissionId: null, fromStageId: null });
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [isChangeStageOpen, setIsChangeStageOpen] = useState(false);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [targetStageId, setTargetStageId] = useState<string>("");
  const [changeNotes, setChangeNotes] = useState("");
  const [changeReason, setChangeReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDragStart = useCallback((e: React.DragEvent, submissionId: string, stageId: string) => {
    if (readOnly) return;
    setDragState({ submissionId, fromStageId: stageId });
    e.dataTransfer.effectAllowed = "move";
  }, [readOnly]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, toStageId: string) => {
    e.preventDefault();
    if (readOnly || !dragState.submissionId || dragState.fromStageId === toStageId) {
      setDragState({ submissionId: null, fromStageId: null });
      return;
    }

    const submission = submissions.find(s => s.id === dragState.submissionId);
    if (submission) {
      setSelectedSubmission(submission);
      setTargetStageId(toStageId);
      setIsChangeStageOpen(true);
    }
    setDragState({ submissionId: null, fromStageId: null });
  }, [dragState, submissions, readOnly]);

  const handleChangeStage = async () => {
    if (!selectedSubmission || !targetStageId) return;

    setIsSubmitting(true);
    try {
      await submissionsService.changeStage(selectedSubmission.id, {
        to_stage_id: targetStageId,
        notes: changeNotes,
        reason: changeReason,
      });

      toast({
        title: "Éxito",
        description: "Etapa actualizada correctamente",
      });

      onSubmissionMove?.(selectedSubmission.id, targetStageId);
      onRefresh?.();
      setIsChangeStageOpen(false);
      setChangeNotes("");
      setChangeReason("");
    } catch (error) {
      toast({
        title: "Error",
        description: "No se pudo cambiar la etapa",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSubmissionsByStage = (stageId: string) => {
    return submissions.filter(s => s.current_stage_id === stageId);
  };

  const formatCurrency = (amount?: number, currency?: string) => {
    if (!amount) return "N/A";
    return new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: currency || "EUR",
    }).format(amount);
  };

  const isSLABreached = (submission: Submission) => {
    if (!submission.sla_deadline) return false;
    return new Date(submission.sla_deadline) < new Date();
  };

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {stages.map((stage) => {
        const stageSubmissions = getSubmissionsByStage(stage.id);
        const isDragOver = dragState.submissionId && dragState.fromStageId !== stage.id;

        return (
          <div
            key={stage.id}
            className={cn(
              "flex-shrink-0 w-80 flex flex-col max-h-[calc(100vh-250px)]",
              !readOnly && "cursor-pointer"
            )}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, stage.id)}
          >
            {/* Column Header */}
            <div 
              className="p-3 rounded-t-lg border"
              style={{ 
                backgroundColor: `${stage.color}20`,
                borderColor: stage.color,
                borderBottom: "none"
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: stage.color }}
                  />
                  <h3 className="font-semibold text-sm">{stage.name}</h3>
                </div>
                <Badge variant="secondary" className="text-xs">
                  {stageSubmissions.length}
                </Badge>
              </div>
              {stage.sla_hours && (
                <p className="text-xs text-muted-foreground mt-1">
                  SLA: {stage.sla_hours}h
                </p>
              )}
            </div>

            {/* Column Content */}
            <div 
              className={cn(
                "flex-1 overflow-y-auto p-2 space-y-2 border border-t-0 rounded-b-lg bg-muted/30",
                isDragOver && "bg-primary/5 border-primary/30"
              )}
            >
              {stageSubmissions.map((submission) => {
                const priority = priorityConfig[submission.priority];
                const slaBreached = isSLABreached(submission);

                return (
                  <Card
                    key={submission.id}
                    draggable={!readOnly}
                    onDragStart={(e) => handleDragStart(e, submission.id, stage.id)}
                    className={cn(
                      "cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow",
                      slaBreached && "border-red-300 bg-red-50/50"
                    )}
                  >
                    <CardContent className="p-3 space-y-2">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">
                            {submission.candidate?.first_name} {submission.candidate?.last_name}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            {submission.candidate?.email}
                          </p>
                        </div>
                        <Badge className={cn("text-xs", priority.color)}>
                          {priority.label}
                        </Badge>
                      </div>

                      {/* Client & Job */}
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Building2 className="h-3 w-3" />
                          <span className="truncate">{submission.client?.name}</span>
                        </div>
                        {submission.job && (
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Briefcase className="h-3 w-3" />
                            <span className="truncate">{submission.job.title}</span>
                          </div>
                        )}
                      </div>

                      {/* Consultant & Salary */}
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <User className="h-3 w-3" />
                          <span>{submission.consultant?.full_name?.split(" ")[0]}</span>
                        </div>
                        {submission.proposed_salary && (
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <DollarSign className="h-3 w-3" />
                            <span>{formatCurrency(submission.proposed_salary, submission.currency)}</span>
                          </div>
                        )}
                      </div>

                      {/* Footer */}
                      <div className="flex items-center justify-between pt-2 border-t">
                        <div className="flex items-center gap-1.5">
                          {slaBreached && (
                            <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                          )}
                          <span className={cn(
                            "text-xs",
                            slaBreached ? "text-red-600 font-medium" : "text-muted-foreground"
                          )}>
                            {submission.documents_count || 0} docs
                          </span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => {
                            setSelectedSubmission(submission);
                            setIsChangeStageOpen(true);
                          }}
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          Ver
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}

              {stageSubmissions.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <p className="text-sm">No hay submissions</p>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Change Stage Dialog */}
      <Dialog open={isChangeStageOpen} onOpenChange={setIsChangeStageOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Cambiar Etapa</DialogTitle>
            <DialogDescription>
              {selectedSubmission && (
                <>
                  Mover a <strong>{selectedSubmission.candidate?.first_name} {selectedSubmission.candidate?.last_name}</strong> de 
                  {" "}<strong>{selectedSubmission.current_stage?.name}</strong> a otra etapa.
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Nueva etapa *</Label>
              <Select value={targetStageId} onValueChange={setTargetStageId}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar etapa" />
                </SelectTrigger>
                <SelectContent>
                  {stages.map((stage) => (
                    <SelectItem 
                      key={stage.id} 
                      value={stage.id}
                      disabled={stage.id === selectedSubmission?.current_stage_id}
                    >
                      {stage.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Motivo del cambio</Label>
              <Select value={changeReason} onValueChange={setChangeReason}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar motivo (opcional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="candidate_progress">Candidato avanza</SelectItem>
                  <SelectItem value="client_request">Solicitud del cliente</SelectItem>
                  <SelectItem value="evaluation_complete">Evaluación completada</SelectItem>
                  <SelectItem value="interview_done">Entrevista realizada</SelectItem>
                  <SelectItem value="offer_made">Oferta realizada</SelectItem>
                  <SelectItem value="rejected">Rechazado</SelectItem>
                  <SelectItem value="other">Otro</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea
                placeholder="Añade notas sobre el cambio de etapa..."
                value={changeNotes}
                onChange={(e) => setChangeNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsChangeStageOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleChangeStage} 
              disabled={!targetStageId || isSubmitting}
            >
              {isSubmitting ? "Cambiando..." : "Cambiar Etapa"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
