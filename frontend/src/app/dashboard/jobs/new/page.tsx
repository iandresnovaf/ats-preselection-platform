'use client';

import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { JobForm } from '@/components/jobs/JobForm';
import { jobService } from '@/services/jobs';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/store/auth';
import { AlertCircle } from 'lucide-react';

export default function NewJobPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { user } = useAuthStore();

  const isConsultant = user?.role === 'consultant' || user?.role === 'super_admin';

  const createJobMutation = useMutation({
    mutationFn: jobService.createJob,
    onSuccess: (data) => {
      toast({
        title: 'Oferta creada',
        description: 'La oferta ha sido creada exitosamente.',
      });
      router.push(`/dashboard/jobs/${data.id}`);
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al crear la oferta',
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = async (data: any) => {
    await createJobMutation.mutateAsync(data);
  };

  const handleCancel = () => {
    router.push('/dashboard/jobs');
  };

  if (!isConsultant) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold">Acceso Denegado</h2>
        <p className="text-muted-foreground mt-2">
          No tienes permisos para crear ofertas de trabajo.
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

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <Link href="/dashboard/jobs">
          <Button variant="outline" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a ofertas
          </Button>
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Nueva Oferta de Trabajo</h1>
        <p className="text-muted-foreground mt-1">
          Crea una nueva oferta de empleo para comenzar a recibir candidatos.
        </p>
      </div>

      <JobForm
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isLoading={createJobMutation.isPending}
      />
    </div>
  );
}
