'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { JobOpening, JobStatus, JobFilters } from '@/types/jobs';
import { JobCard } from '@/components/jobs/JobCard';
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
import { Plus, Search, Loader2, Briefcase, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/store/auth';
import { jobService } from '@/services/jobs';

// Dynamic import para JobForm (modal pesado)
const JobForm = dynamic(
  () => import('@/components/jobs/JobForm'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }
);

const statusOptions: { value: JobStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Todos los estados' },
  { value: 'draft', label: 'Borrador' },
  { value: 'active', label: 'Activa' },
  { value: 'paused', label: 'Pausada' },
  { value: 'closed', label: 'Cerrada' },
];

export default function JobsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  
  const [filters, setFilters] = useState<JobFilters>({});
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<JobOpening | null>(null);
  const [jobToDelete, setJobToDelete] = useState<JobOpening | null>(null);
  const [jobToClose, setJobToClose] = useState<JobOpening | null>(null);

  const isConsultant = user?.role === 'consultant' || user?.role === 'super_admin';

  // Fetch jobs
  const { data: jobs = [], isLoading, error } = useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => jobService.getJobs(filters),
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: jobService.createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setIsCreateModalOpen(false);
      toast({
        title: 'Oferta creada',
        description: 'La oferta ha sido creada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al crear la oferta',
        variant: 'destructive',
      });
    },
  });

  // Update job mutation
  const updateJobMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => jobService.updateJob(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setIsEditModalOpen(false);
      setSelectedJob(null);
      toast({
        title: 'Oferta actualizada',
        description: 'La oferta ha sido actualizada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al actualizar la oferta',
        variant: 'destructive',
      });
    },
  });

  // Delete job mutation
  const deleteJobMutation = useMutation({
    mutationFn: jobService.deleteJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setJobToDelete(null);
      toast({
        title: 'Oferta eliminada',
        description: 'La oferta ha sido eliminada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al eliminar la oferta',
        variant: 'destructive',
      });
    },
  });

  // Close job mutation
  const closeJobMutation = useMutation({
    mutationFn: jobService.closeJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setJobToClose(null);
      toast({
        title: 'Oferta cerrada',
        description: 'La oferta ha sido cerrada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al cerrar la oferta',
        variant: 'destructive',
      });
    },
  });

  // Pause job mutation
  const pauseJobMutation = useMutation({
    mutationFn: jobService.pauseJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast({
        title: 'Oferta pausada',
        description: 'La oferta ha sido pausada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al pausar la oferta',
        variant: 'destructive',
      });
    },
  });

  // Activate job mutation
  const activateJobMutation = useMutation({
    mutationFn: jobService.activateJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast({
        title: 'Oferta activada',
        description: 'La oferta ha sido activada exitosamente.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al activar la oferta',
        variant: 'destructive',
      });
    },
  });

  const handleCreateJob = async (data: any) => {
    await createJobMutation.mutateAsync(data);
  };

  const handleUpdateJob = async (data: any) => {
    if (selectedJob) {
      await updateJobMutation.mutateAsync({ id: selectedJob.id, data });
    }
  };

  const handleEdit = (job: JobOpening) => {
    setSelectedJob(job);
    setIsEditModalOpen(true);
  };

  const handleDelete = (job: JobOpening) => {
    setJobToDelete(job);
  };

  const confirmDelete = async () => {
    if (jobToDelete) {
      await deleteJobMutation.mutateAsync(jobToDelete.id);
    }
  };

  const handleClose = (job: JobOpening) => {
    setJobToClose(job);
  };

  const confirmClose = async () => {
    if (jobToClose) {
      await closeJobMutation.mutateAsync(jobToClose.id);
    }
  };

  const handlePause = async (job: JobOpening) => {
    await pauseJobMutation.mutateAsync(job.id);
  };

  const handleActivate = async (job: JobOpening) => {
    await activateJobMutation.mutateAsync(job.id);
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold">Error al cargar ofertas</h2>
        <p className="text-muted-foreground mt-2">
          Hubo un problema al cargar las ofertas. Por favor, intenta de nuevo.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ofertas de Trabajo</h1>
          <p className="text-muted-foreground mt-1">
            Gestiona las ofertas de empleo y sus candidatos.
          </p>
        </div>
        {isConsultant && (
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nueva Oferta
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por título, departamento..."
            className="pl-10"
            value={filters.search || ''}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
        </div>
        <Select
          value={filters.status || 'all'}
          onValueChange={(value) =>
            setFilters({ ...filters, status: value === 'all' ? undefined : value as JobStatus })
          }
        >
          <SelectTrigger className="w-[200px]">
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
      </div>

      {/* Jobs Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center border rounded-lg bg-muted/50">
          <Briefcase className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold">No hay ofertas</h3>
          <p className="text-muted-foreground mt-1 max-w-md">
            {filters.search || filters.status 
              ? "No se encontraron ofertas con los filtros aplicados."
              : "Aún no has creado ninguna oferta de trabajo."}
          </p>
          {isConsultant && !filters.search && !filters.status && (
            <Button onClick={() => setIsCreateModalOpen(true)} className="mt-4">
              <Plus className="mr-2 h-4 w-4" />
              Crear primera oferta
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onClose={handleClose}
              onPause={handlePause}
              onActivate={handleActivate}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Crear Nueva Oferta</DialogTitle>
          </DialogHeader>
          <JobForm
            onSubmit={handleCreateJob}
            onCancel={() => setIsCreateModalOpen(false)}
            isLoading={createJobMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Oferta</DialogTitle>
          </DialogHeader>
          {selectedJob && (
            <JobForm
              job={selectedJob}
              onSubmit={handleUpdateJob}
              onCancel={() => {
                setIsEditModalOpen(false);
                setSelectedJob(null);
              }}
              isLoading={updateJobMutation.isPending}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!jobToDelete} onOpenChange={() => setJobToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar oferta?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. La oferta <strong>{jobToDelete?.title}</strong> será eliminada permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-red-600 hover:bg-red-700"
              disabled={deleteJobMutation.isPending}
            >
              {deleteJobMutation.isPending ? (
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

      {/* Close Confirmation */}
      <AlertDialog open={!!jobToClose} onOpenChange={() => setJobToClose(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Cerrar oferta?</AlertDialogTitle>
            <AlertDialogDescription>
              Al cerrar la oferta <strong>{jobToClose?.title}</strong>, ya no aceptará nuevos candidatos.
              Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmClose}
              className="bg-orange-600 hover:bg-orange-700"
              disabled={closeJobMutation.isPending}
            >
              {closeJobMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Cerrando...
                </>
              ) : (
                'Cerrar oferta'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
