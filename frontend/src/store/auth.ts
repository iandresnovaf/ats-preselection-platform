import { create } from 'zustand';
import { User } from '@/types/auth';
import { authService } from '@/services/auth';

// Transforma el usuario del backend (snake_case) al formato del frontend (camelCase)
function transformUser(user: any): User {
  if (!user) return null as any;

  // Separar full_name en firstName y lastName
  const nameParts = user.full_name?.split(' ') || ['', ''];
  const firstName = nameParts[0] || '';
  const lastName = nameParts.slice(1).join(' ') || '';

  return {
    id: user.id,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    status: user.status,
    created_at: user.created_at,
    last_login: user.last_login,
    // Campos computados (camelCase)
    firstName,
    lastName,
    fullName: user.full_name,
    isActive: user.status === 'active',
  };
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  setUser: (user: User | null) => void;
  clearError: () => void;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      // El backend envía tokens en cookies httpOnly automáticamente
      const response = await authService.login({ email, password });
      
      // Transformar usuario
      const transformedUser = transformUser(response.user);
      
      set({
        user: transformedUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      // No exponer detalles internos del error
      let errorMessage = 'Error de autenticación. Por favor, verifica tus credenciales.';
      
      // Solo mostrar mensajes genéricos al usuario
      if (error.response?.status === 401) {
        errorMessage = 'Credenciales inválidas. Por favor, verifica tu email y contraseña.';
      } else if (error.response?.status === 429) {
        errorMessage = 'Demasiados intentos. Por favor, intenta más tarde.';
      } else if (error.response?.status >= 500) {
        errorMessage = 'Error del servidor. Por favor, intenta más tarde.';
      }
      
      set({
        isLoading: false,
        error: errorMessage,
        isAuthenticated: false,
        user: null,
      });
      throw error;
    }
  },

  logout: async () => {
    try {
      await authService.logout();
    } catch (error) {
      // Ignorar errores de logout - las cookies httpOnly se eliminarán del lado del servidor
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const user = await authService.getMe();
      const transformedUser = transformUser(user);
      set({
        user: transformedUser,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      if (error.response?.status === 401) {
        // No autenticado - redirigir a login
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      } else if (error.response?.status === 403) {
        // Forbidden - user doesn't have permission
        set({
          isLoading: false,
          error: 'No tienes permisos para acceder a este recurso',
        });
      } else {
        // Error genérico sin exponer detalles internos
        set({
          isLoading: false,
          error: 'Error al cargar la información del usuario',
        });
      }
    }
  },

  setUser: (user: User | null) => {
    set({ user, isAuthenticated: !!user });
  },

  clearError: () => {
    set({ error: null });
  },

  checkAuth: async () => {
    try {
      const user = await authService.getMe();
      const transformedUser = transformUser(user);
      set({
        user: transformedUser,
        isAuthenticated: true,
      });
      return true;
    } catch (error: any) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        set({
          user: null,
          isAuthenticated: false,
        });
      }
      return false;
    }
  },
}));

// Selectores optimizados para evitar re-renders
// Uso: const user = useUser() en lugar de const user = useAuthStore(state => state.user)
export const useUser = () => useAuthStore(state => state.user);
export const useIsAuthenticated = () => useAuthStore(state => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore(state => state.isLoading);
export const useAuthError = () => useAuthStore(state => state.error);
