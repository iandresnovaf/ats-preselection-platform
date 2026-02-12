import axios from "axios";
import { authService } from "./auth";

// Usar el proxy de Next.js para evitar problemas de CORS y cookies cross-origin
// En desarrollo: /api/v1 -> http://localhost:8000/api/v1
// En producción: usa la URL del backend
const API_BASE_URL = typeof window !== 'undefined' 
  ? '/api/v1'  // Client-side: usar proxy de Next.js
  : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1");  // Server-side

// Flag para evitar múltiples refresh simultáneos
let isRefreshing = false;
let refreshSubscribers: ((success: boolean) => void)[] = [];

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  // Importante: incluir credenciales para que las cookies se envíen
  withCredentials: true,
});

// Helper para suscribirse a un refresh de token
function subscribeTokenRefresh(callback: (success: boolean) => void) {
  refreshSubscribers.push(callback);
}

// Helper para notificar a todos los suscriptores
function onTokenRefreshed(success: boolean) {
  refreshSubscribers.forEach((callback) => callback(success));
  refreshSubscribers = [];
}

// Response interceptor to handle errors y refresh automático
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si es 401 y no hemos intentado refresh aún
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (isRefreshing) {
        // Esperar a que termine el refresh en curso
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((success: boolean) => {
            if (success) {
              resolve(api(originalRequest));
            } else {
              reject(error);
            }
          });
        });
      }

      isRefreshing = true;

      try {
        // El backend refresca automáticamente usando la cookie httpOnly
        await authService.refreshToken();
        
        // Notificar éxito a todos los requests en cola
        onTokenRefreshed(true);

        // Reintentar el request original
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh falló, notificar fallo
        onTokenRefreshed(false);

        // Solo redirigir si estamos en el cliente
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Manejar error 403 (Forbidden) - No exponer detalles internos
    if (error.response?.status === 403) {
      console.error("Access forbidden");
      // No redirigir automáticamente, dejar que el componente maneje el error
    }

    // Manejar otros errores sin exponer información sensible
    if (error.response?.status >= 500) {
      console.error("Server error occurred");
    }

    return Promise.reject(error);
  }
);

export default api;
