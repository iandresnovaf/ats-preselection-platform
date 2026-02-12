'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState, ReactNode } from 'react';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        staleTime: 60 * 1000, // 1 minuto por defecto
        gcTime: 5 * 60 * 1000, // 5 minutos (antes cacheTime)
        retry: 2,
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}

// Helper function para obtener staleTime por tipo de query
export function getStaleTimeByQueryType(queryKey: string[]): number {
  const key = queryKey[0];
  
  switch (key) {
    case 'configurations':
      return 5 * 60 * 1000; // 5 minutos
    case 'jobs':
      return 60 * 1000; // 1 minuto
    case 'candidates':
      return 30 * 1000; // 30 segundos
    case 'user':
      return 5 * 60 * 1000; // 5 minutos
    default:
      return 60 * 1000; // 1 minuto por defecto
  }
}
