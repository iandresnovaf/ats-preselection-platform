import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
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

// Valida si un token JWT está expirado
function isTokenExpired(token: string | null): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= exp;
  } catch {
    return true;
  }
}

// Obtiene tiempo restante de expiración en ms
function getTokenTimeRemaining(token: string | null): number {
  if (!token) return 0;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000;
    return Math.max(0, exp - Date.now());
  } catch {
    return 0;
  }
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  clearError: () => void;
  refreshAccessToken: () => Promise<string | null>;
  isTokenValid: () => boolean;
  getTokenTimeRemaining: () => number;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authService.login({ email, password });
          
          // Store tokens
          localStorage.setItem('access_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);
          
          // Transformar usuario
          const transformedUser = transformUser(response.user);
          
          set({
            user: transformedUser,
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || 
                              error.response?.data?.message || 
                              'Error de autenticación. Por favor, verifica tus credenciales.';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
            token: null,
            refreshToken: null,
          });
          throw error;
        }
      },

      logout: async () => {
        try {
          await authService.logout();
        } catch (error) {
          // Ignore logout errors
        } finally {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          set({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      fetchUser: async () => {
        const token = get().token || localStorage.getItem('access_token');

        // Validar si el token existe y no está expirado
        if (!token || isTokenExpired(token)) {
          // Intentar refresh si hay refresh token
          const refreshToken = get().refreshToken || localStorage.getItem('refresh_token');
          if (refreshToken) {
            const newToken = await get().refreshAccessToken();
            if (!newToken) {
              set({ isAuthenticated: false, user: null, token: null, refreshToken: null });
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
              return;
            }
          } else {
            set({ isAuthenticated: false, user: null });
            return;
          }
        }

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
            // Try to refresh token
            const newToken = await get().refreshAccessToken();
            if (!newToken) {
              set({
                user: null,
                token: null,
                refreshToken: null,
                isAuthenticated: false,
                isLoading: false,
              });
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
            }
          } else if (error.response?.status === 403) {
            // Forbidden - user doesn't have permission
            set({
              isLoading: false,
              error: 'No tienes permisos para acceder a este recurso',
            });
          } else {
            set({
              isLoading: false,
              error: error.response?.data?.detail || 'Error al cargar usuario',
            });
          }
        }
      },

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: !!user });
      },

      setToken: (token: string | null) => {
        set({ token, isAuthenticated: !!token });
        if (token) {
          localStorage.setItem('access_token', token);
        } else {
          localStorage.removeItem('access_token');
        }
      },

      clearError: () => {
        set({ error: null });
      },

      refreshAccessToken: async () => {
        const currentRefreshToken = get().refreshToken || localStorage.getItem('refresh_token');
        if (!currentRefreshToken) {
          return null;
        }

        try {
          const response = await authService.refreshToken(currentRefreshToken);
          localStorage.setItem('access_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);
          set({
            token: response.access_token,
            refreshToken: response.refresh_token,
          });
          return response.access_token;
        } catch (error: any) {
          // Si el refresh token es inválido, limpiar todo
          if (error.response?.status === 401 || error.response?.status === 403) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            set({
              user: null,
              token: null,
              refreshToken: null,
              isAuthenticated: false,
            });
          }
          return null;
        }
      },

      // Verifica si el token actual es válido
      isTokenValid: () => {
        const token = get().token || localStorage.getItem('access_token');
        return !isTokenExpired(token);
      },

      // Obtiene el tiempo restante del token en ms
      getTokenTimeRemaining: () => {
        const token = get().token || localStorage.getItem('access_token');
        return getTokenTimeRemaining(token);
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
