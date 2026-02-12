'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { Candidate, CandidateStatus, CandidateSource, CandidateFilters } from '@/types/candidates';
import { CandidateCard } from '@/components/candidates/CandidateCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Plus, Search, Loader2, Users, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/store/auth';
import { candidateService } from '@/services/candidates';
import { CandidateForm } from '@/components/candidates/CandidateForm';
import { jobService } from '@/services/jobs';
import { JobOpening } from '@/types/jobs';

// Dynamic imports para mejor performance
const EvaluationModal = dynamic(
  () => import('@/components/evaluations/EvaluationModal'),
  { 
    ssr: false,
    loading: () => (
      <Dialog open={true}>
        <DialogContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        </DialogContent>
      </Dialog>
    )
  }
);

const statusOptions: { value: CandidateStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Todos los estados' },
  { value: 'new', label: 'Nuevo' },
  { value: 'screening', label: 'En revisión' },
  { value: 'interview', label: 'Entrevista' },
  { value: 'evaluation', label: 'Evaluación' },
  { value: 'offer', label: 'Oferta' },
  { value: 'hired', label: 'Contratado' },
  { value: 'rejected', label: 'Rechazado' },
];

const sourceOptions: { value: CandidateSource | 'all'; label: string }[] = [
  { value: 'all', label: 'Todas las fuentes' },
  { value: 'email', label: 'Email' },
  { value: 'manual', label: 'Manual' },
  { value: 'zoho', label: 'Zoho' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'referral', label: 'Referido' },
  { value: 'other', label: 'Otro' },
];

const statusFlow: CandidateStatus[] = ['new', 'screening', 'interview', 'evaluation', 'offer', 'hired'];

export default function CandidatesPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  
  const [filters, setFilters] = useState<CandidateFilters>({});
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [evaluationCandidate, setEvaluationCandidate] = useState<Candidate | null>(null);
  const [candidateToDelete, setCandidateToDelete] = useState<Candidate | null>(null);
  const [newStatus, setNewStatus] = useState<CandidateStatus>('new');

  const isConsultant = user?.role === 'consultant' || user?.role === 'super_admin';

  // Fetch jobs for filter
  const { data: jobs = [] } = useQuery({
    queryKey: ['jobs', 'active'],
    queryFn: () => jobService.getJobs({ status: 'active' }),
  });

  // Fetch candidates
  const { data: candidates = [], isLoading, error } = useQuery({
    queryKey: ['candidates', filters],
    queryFn: () => candidateService.getCandidates(filters),
  });

  // Create candidate mutation
  const createCandidateMutation = useMutation({
    mutationFn: candidateService.createCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setIsCreateModalOpen(false);
      toast({
        title: 'Candidato creado',
        description: 'El candidato ha sido creado exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al crear el candidato',
        variant: 'destructive',
      });
    },
  });

  // Update candidate mutation
  const updateCandidateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      candidateService.updateCandidate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setIsEditModalOpen(false);
      setSelectedCandidate(null);
      toast({
        title: 'Candidato actualizado',
        description: 'El candidato ha sido actualizado exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al actualizar el candidato',
        variant: 'destructive',
      });
    },
  });

  // Delete candidate mutation
  const deleteCandidateMutation = useMutation({
    mutationFn: candidateService.deleteCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setCandidateToDelete(null);
      toast({
        title: 'Candidato eliminado',
        description: 'El candidato ha sido eliminado exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al eliminar el candidato',
        variant: 'destructive',
      });
    },
  });

  // Change status mutation
  const changeStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: CandidateStatus }) => 
      candidateService.changeStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates'] });
      setIsStatusModalOpen(false);
      setSelectedCandidate(null);
      toast({
        title: 'Estado actualizado',
        description: 'El estado del candidato ha sido actualizado exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al cambiar el estado',
        variant: 'destructive',
      });
    },
  });

  const handleCreateCandidate = async (data: any) => {
    await createCandidateMutation.mutateAsync(data);
  };

  const handleUpdateCandidate = async (data: any) => {
    if (selectedCandidate) {
      await updateCandidateMutation.mutateAsync({ id: selectedCandidate.id, data });
    }
  };

  const handleEdit = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    setIsEditModalOpen(true);
  };

  const handleDelete = (candidate: Candidate) => {
    setCandidateToDelete(candidate);
  };

  const confirmDelete = async () => {
    if (candidateToDelete) {
      await deleteCandidateMutation.mutateAsync(candidateToDelete.id);
    }
  };

  const handleChangeStatus = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    setNewStatus(candidate.status);
    setIsStatusModalOpen(true);
  };

  const confirmChangeStatus = async () => {
    if (selectedCandidate) {
      await changeStatusMutation.mutateAsync({ 
        id: selectedCandidate.id, 
        status: newStatus 
      });
    }
  };

  const handleEvaluate = (candidate: Candidate) => {
    setEvaluationCandidate(candidate);
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold">Error al cargar candidatos</h2>
        <p className="text-muted-foreground mt-2">
          Hubo un problema al cargar los candidatos. Por favor, intenta de nuevo.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Candidatos</h1>
          <p className="text-muted-foreground mt-1">
            Gestiona los candidatos y sus evaluaciones.
          </p>
        </div>
        {isConsultant && (
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo Candidato
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre, email, empresa..."
            className="pl-10"
            value={filters.search || ''}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <Select
            value={filters.job_opening_id || 'all'}
            onValueChange={(value) =>
              setFilters({ ...filters, job_opening_id: value === 'all' ? undefined : value })
            }
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Todas las ofertas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las ofertas</SelectItem>
              {jobs.map((job) => (
                <SelectItem key={job.id} value={job.id}>
                  {job.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.status || 'all'}
            onValueChange={(value) =>
              setFilters({ ...filters, status: value === 'all' ? undefined : value as CandidateStatus })
            }
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filtrar por estado" />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.source || 'all'}
            onValueChange={(value) =>
              setFilters({ ...filters, source: value === 'all' ? undefined : value as CandidateSource })
            }
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filtrar por fuente" />
            </SelectTrigger>
            <SelectContent>
              {sourceOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Candidates Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : candidates.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center border rounded-lg bg-muted/50">
          <Users className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold">No hay candidatos</h3>
          <p className="text-muted-foreground mt-1 max-w-md">
            {filters.search || filters.status || filters.job_opening_id
              ? "No se encontraron candidatos con los filtros aplicados."
              : "Aún no hay candidatos registrados."}
          </p>
          {isConsultant && !filters.search && !filters.status && !filters.job_opening_id && (
            <Button onClick={() => setIsCreateModalOpen(true)} className="mt-4">
              <Plus className="mr-2 h-4 w-4" />
              Crear primer candidato
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onEvaluate={handleEvaluate}
              onChangeStatus={handleChangeStatus}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nuevo Candidato</DialogTitle>
          </DialogHeader>
          <CandidateForm
            onSubmit={handleCreateCandidate}
            onCancel={() => setIsCreateModalOpen(false)}
            isLoading={createCandidateMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Candidato</DialogTitle>
          </DialogHeader>
          {selectedCandidate && (
            <CandidateForm
              candidate={selectedCandidate}
              onSubmit={handleUpdateCandidate}
              onCancel={() => {
                setIsEditModalOpen(false);
                setSelectedCandidate(null);
              }}
              isLoading={updateCandidateMutation.isPending}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Change Status Modal */}
      <Dialog open={isStatusModalOpen} onOpenChange={setIsStatusModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambiar Estado</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-muted-foreground">
              Cambiar estado de <strong>{selectedCandidate?.first_name} {selectedCandidate?.last_name}</strong>
            </p>
            <Select
              value={newStatus}
              onValueChange={(value) => setNewStatus(value as CandidateStatus)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona un estado" />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.filter(o => o.value !== 'all').map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsStatusModalOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={confirmChangeStatus}
              disabled={changeStatusMutation.isPending}
            >
              {changeStatusMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Guardar'
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!candidateToDelete} onOpenChange={() => setCandidateToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar candidato?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. El candidato <strong>{candidateToDelete?.first_name} {candidateToDelete?.last_name}</strong> será eliminado permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-red-600 hover:bg-red-700"
              disabled={deleteCandidateMutation.isPending}
            >
              {deleteCandidateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Eliminando...
                </>
              ) : (
                'Eliminar'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Evaluation Modal */}
      {evaluationCandidate && (
        <EvaluationModal
          candidate={evaluationCandidate}
          isOpen={!!evaluationCandidate}
          onClose={() => setEvaluationCandidate(null)}
          onEvaluationComplete={() => {
            queryClient.invalidateQueries({ queryKey: ['candidates'] });
          }}
        />
      )}
    </div>
  );
}
