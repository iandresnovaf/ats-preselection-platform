import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ATSProvider } from '@/types/rhtools';

interface ConfigState {
  // ATS Configuration
  atsProvider: ATSProvider;
  isRHToolsEnabled: boolean;
  
  // Actions
  setATSProvider: (provider: ATSProvider) => void;
  toggleRHTools: () => void;
}

export const useConfigStore = create<ConfigState>()(
  persist(
    (set, get) => ({
      atsProvider: 'rhtools', // Default para desarrollo
      isRHToolsEnabled: true,

      setATSProvider: (provider: ATSProvider) => {
        set({ 
          atsProvider: provider,
          isRHToolsEnabled: provider === 'rhtools'
        });
      },

      toggleRHTools: () => {
        const current = get().isRHToolsEnabled;
        set({ 
          isRHToolsEnabled: !current,
          atsProvider: !current ? 'rhtools' : 'zoho'
        });
      },
    }),
    {
      name: 'ats-config-storage',
      partialize: (state) => ({ 
        atsProvider: state.atsProvider,
        isRHToolsEnabled: state.isRHToolsEnabled 
      }),
    }
  )
);

// Hook helper para verificar si RHTools está habilitado
export function useIsRHToolsEnabled(): boolean {
  return useConfigStore((state) => state.isRHToolsEnabled);
}

// Hook para obtener el provider actual
export function useATSProvider(): ATSProvider {
  return useConfigStore((state) => state.atsProvider);
}
