'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { JobOpening, JobStatus } from '@/types/jobs';
import { Candidate } from '@/types/candidates';
import { jobService } from '@/services/jobs';
import { candidateService } from '@/services/candidates';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  ArrowLeft,
  Briefcase,
  MapPin,
  Users,
  Calendar,
  Edit,
  Plus,
  Loader2,
  User,
  Star,
  TrendingUp,
  Mail,
  Phone,
  FileText,
  Sparkles,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import JobForm from '@/components/jobs/JobForm';
import { CandidateForm } from '@/components/candidates/CandidateForm';
import { EvaluationModal } from '@/components/evaluations/EvaluationModal';
import { useAuthStore } from '@/store/auth';

const statusConfig: Record<JobStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  draft: { label: "Borrador", variant: "secondary" },
  active: { label: "Activa", variant: "default" },
  paused: { label: "Pausada", variant: "outline" },
  closed: { label: "Cerrada", variant: "destructive" },
};

const candidateStatusConfig: Record<string, { label: string; color: string }> = {
  new: { label: "Nuevo", color: "bg-blue-100 text-blue-800" },
  screening: { label: "En revisión", color: "bg-yellow-100 text-yellow-800" },
  interview: { label: "Entrevista", color: "bg-purple-100 text-purple-800" },
  evaluation: { label: "Evaluación", color: "bg-orange-100 text-orange-800" },
  offer: { label: "Oferta", color: "bg-green-100 text-green-800" },
  hired: { label: "Contratado", color: "bg-emerald-100 text-emerald-800" },
  rejected: { label: "Rechazado", color: "bg-red-100 text-red-800" },
};

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-600";
  return "text-red-600";
}

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddCandidateModalOpen, setIsAddCandidateModalOpen] = useState(false);
  const [evaluationCandidate, setEvaluationCandidate] = useState<Candidate | null>(null);

  const isConsultant = user?.role === 'consultant' || user?.role === 'super_admin';

  // Fetch job details
  const { data: job, isLoading: isLoadingJob } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobService.getJob(jobId),
    enabled: !!jobId,
  });

  // Fetch candidates for this job
  const { data: candidates = [], isLoading: isLoadingCandidates } = useQuery({
    queryKey: ['candidates', 'job', jobId],
    queryFn: () => candidateService.getCandidatesByJob(jobId),
    enabled: !!jobId,
  });

  // Fetch job statistics
  const { data: statistics } = useQuery({
    queryKey: ['job', jobId, 'statistics'],
    queryFn: () => jobService.getJobStatistics(jobId),
    enabled: !!jobId,
  });

  // Update job mutation
  const updateJobMutation = useMutation({
    mutationFn: (data: any) => jobService.updateJob(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      setIsEditModalOpen(false);
      toast({
        title: 'Oferta actualizada',
        description: 'La oferta ha sido actualizada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: (error.response?.data?.detail ? (typeof error.response.data.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response.data.detail)) : 'Error al actualizar la oferta'),
        variant: 'destructive',
      });
    },
  });

  // Create candidate mutation
  const createCandidateMutation = useMutation({
    mutationFn: candidateService.createCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates', 'job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['job', jobId, 'statistics'] });
      setIsAddCandidateModalOpen(false);
      toast({
        title: 'Candidato agregado',
        description: 'El candidato ha sido agregado exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: (error.response?.data?.detail ? (typeof error.response.data.detail === 'string' ? error.response.data.detail : JSON.stringify(error.response.data.detail)) : 'Error al agregar el candidato'),
        variant: 'destructive',
      });
    },
  });

  const handleUpdateJob = async (data: any) => {
    await updateJobMutation.mutateAsync(data);
  };

  const handleAddCandidate = async (data: any) => {
    await createCandidateMutation.mutateAsync({
      ...data,
      job_opening_id: jobId,
    });
  };

  if (isLoadingJob) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Briefcase className="h-12 w-12 text-muted-foreground mb-4" />
        <h2 className="text-xl font-semibold">Oferta no encontrada</h2>
        <p className="text-muted-foreground mt-2">
          La oferta que buscas no existe o ha sido eliminada.
        </p>
        <Link href="/dashboard/jobs">
          <Button variant="outline" className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a ofertas
          </Button>
        </Link>
      </div>
    );
  }

  const status = statusConfig[job.status];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/jobs">
            <Button variant="outline" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">{job.title}</h1>
              <Badge variant={status.variant}>{status.label}</Badge>
            </div>
            <p className="text-muted-foreground">{job.department} • {job.location}</p>
          </div>
        </div>
        {isConsultant && job.status !== 'closed' && (
          <Button onClick={() => setIsEditModalOpen(true)} variant="outline">
            <Edit className="mr-2 h-4 w-4" />
            Editar
          </Button>
        )}
      </div>

      <Tabs defaultValue="info" className="space-y-6">
        <TabsList>
          <TabsTrigger value="info">Información General</TabsTrigger>
          <TabsTrigger value="candidates">
            Candidatos ({candidates.length})
          </TabsTrigger>
          <TabsTrigger value="statistics">Estadísticas</TabsTrigger>
        </TabsList>

        {/* Info Tab */}
        <TabsContent value="info" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Descripción</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none">
                  <p className="text-muted-foreground whitespace-pre-wrap">{job.description}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Detalles</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Briefcase className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Seniority</p>
                    <p className="font-medium">{job.seniority}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <MapPin className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Ubicación</p>
                    <p className="font-medium">{job.location}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Sector</p>
                    <p className="font-medium">{job.sector}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Creada</p>
                    <p className="font-medium">
                      {new Date(job.created_at).toLocaleDateString('es-ES')}
                    </p>
                  </div>
                </div>
                {job.assigned_consultant && (
                  <div className="flex items-center gap-3">
                    <User className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Consultor</p>
                      <p className="font-medium">{job.assigned_consultant.full_name}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Candidates Tab */}
        <TabsContent value="candidates" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Candidatos</h2>
            {isConsultant && job.status !== 'closed' && (
              <Button onClick={() => setIsAddCandidateModalOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Agregar Candidato
              </Button>
            )}
          </div>

          {isLoadingCandidates ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : candidates.length === 0 ? (
            <div className="text-center py-12 border rounded-lg bg-muted/50">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold">No hay candidatos</h3>
              <p className="text-muted-foreground mt-1">
                Aún no hay candidatos para esta oferta.
              </p>
              {isConsultant && job.status !== 'closed' && (
                <Button onClick={() => setIsAddCandidateModalOpen(true)} className="mt-4">
                  <Plus className="mr-2 h-4 w-4" />
                  Agregar candidato
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {candidates.map((candidate) => {
                const status = candidateStatusConfig[candidate.status];
                const hasEvaluation = !!candidate.last_evaluation;
                
                return (
                  <Card key={candidate.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold">
                              {candidate.first_name} {candidate.last_name}
                            </h3>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}>
                              {status.label}
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground">{candidate.email}</p>
                          {candidate.current_position && (
                            <p className="text-sm text-muted-foreground">
                              {candidate.current_position}
                              {candidate.current_company && ` en ${candidate.current_company}`}
                            </p>
                          )}
                        </div>
                        {hasEvaluation && (
                          <div className="text-right">
                            <div className="flex items-center gap-1">
                              <Star className="h-4 w-4" />
                              <span className={`font-semibold ${getScoreColor(candidate.last_evaluation!.score)}`}>
                                {candidate.last_evaluation!.score}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2 mt-4">
                        <Link href={`/dashboard/candidates/${candidate.id}`} className="flex-1">
                          <Button variant="outline" size="sm" className="w-full">
                            Ver detalles
                          </Button>
                        </Link>
                        <Button 
                          size="sm" 
                          variant="secondary"
                          onClick={() => setEvaluationCandidate(candidate)}
                        >
                          <Sparkles className="h-4 w-4 mr-1" />
                          Evaluar
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* Statistics Tab */}
        <TabsContent value="statistics" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Candidatos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{statistics?.total_candidates || candidates.length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Puntuación Promedio
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {statistics?.average_evaluation_score?.toFixed(1) || '-'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Top Candidatos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{statistics?.top_candidates || '-'}</div>
              </CardContent>
            </Card>
          </div>

          {statistics?.by_status && Object.keys(statistics.by_status).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Candidatos por Estado</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(statistics.by_status).map(([status, count]) => {
                    const statusConfig = candidateStatusConfig[status];
                    const total = statistics.total_candidates;
                    const percentage = total > 0 ? (count / total) * 100 : 0;
                    
                    return (
                      <div key={status}>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">{statusConfig?.label || status}</span>
                          <span className="text-sm font-medium">{count}</span>
                        </div>
                        <Progress value={percentage} className="h-2" />
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Oferta</DialogTitle>
          </DialogHeader>
          <JobForm
            job={job}
            onSubmit={handleUpdateJob}
            onCancel={() => setIsEditModalOpen(false)}
            isLoading={updateJobMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Add Candidate Modal */}
      <Dialog open={isAddCandidateModalOpen} onOpenChange={setIsAddCandidateModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Agregar Candidato</DialogTitle>
          </DialogHeader>
          <CandidateForm
            jobId={jobId}
            onSubmit={handleAddCandidate}
            onCancel={() => setIsAddCandidateModalOpen(false)}
            isLoading={createCandidateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Evaluation Modal */}
      {evaluationCandidate && (
        <EvaluationModal
          candidate={evaluationCandidate}
          isOpen={!!evaluationCandidate}
          onClose={() => setEvaluationCandidate(null)}
          onEvaluationComplete={() => {
            queryClient.invalidateQueries({ queryKey: ['candidates', 'job', jobId] });
          }}
        />
      )}
    </div>
  );
}
