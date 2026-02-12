# 📊 Performance Report - Frontend (ATS Platform)

**Fecha:** 2026-02-11  
**Framework:** Next.js 14.1.0  
**React:** 18.2.0  
**Analista:** Performance Engineer

---

## 📈 Métricas Actuales Estimadas

### Bundle Size Analysis

| Métrica | Valor | Estado |
|---------|-------|--------|
| **Total Build Size** | ~323 MB | ⚠️ Crítico |
| **Framework Chunk** | 138 KB | ✅ Aceptable |
| **Main Bundle** | 123 KB | ✅ Aceptable |
| **Polyfills** | 90 KB | ⚠️ Alto |
| **Vendor Chunks (varios)** | ~600 KB | ⚠️ Revisar |
| **LCP Estimado** | 2.5-3.5s | ⚠️ Necesita mejora |
| **FID Estimado** | 50-100ms | ✅ Aceptable |
| **CLS Estimado** | 0.05-0.1 | ⚠️ Mejorable |
| **TTFB Estimado** | 200-400ms | ✅ Aceptable |

### Análisis de Dependencias Principales

| Paquete | Tamaño Estimado | Uso |
|---------|-----------------|-----|
| `@radix-ui/*` (16 paquetes) | ~150 KB | UI Components |
| `@tanstack/react-query` | ~40 KB | Data Fetching |
| `axios` | ~30 KB | HTTP Client |
| `lucide-react` | ~50 KB | Icons (tree-shakeable) |
| `zustand` | ~5 KB | State Management |
| `react-hook-form` | ~25 KB | Forms |
| `zod` | ~15 KB | Validation |
| `date-fns` | ~30 KB | Date utilities |

---

## 🚨 Problemas Identificados

### 🔴 Prioridad Alta

#### 1. **Build Size Excesivo (323 MB)**
- **Problema:** El directorio `.next` tiene 323 MB, lo cual es excesivamente grande
- **Impacto:** Tiempos de despliegue lentos, mayor uso de almacenamiento
- **Causa probable:** Múltiples builds acumulados o caché no limpiado

#### 2. **Falta de Code Splitting en Componentes Pesados**
- **Archivos afectados:**
  - `src/app/dashboard/candidates/page.tsx` (carga EvaluationModal síncronamente)
  - `src/app/dashboard/jobs/page.tsx` (carga JobForm síncronamente)
  - `src/components/evaluations/EvaluationResult.tsx` (componente pesado)
- **Impacto:** Carga inicial innecesaria de código no utilizado inmediatamente

#### 3. **React Query Devtools en Producción**
- **Archivo:** `src/components/providers.tsx`
- **Problema:** `ReactQueryDevtools` se carga siempre, incluso en producción
- **Impacto:** ~20-30 KB adicionales en producción

#### 4. **Configuración de Imágenes No Optimizada**
- **Archivo:** `next.config.js`
- **Problema:** Falta configuración de `images` para optimización automática
- **Impacto:** Imágenes no optimizadas, mayor LCP

---

### 🟡 Prioridad Media

#### 5. **Sin prefetching Estratégico**
- **Archivos:** Hooks de servicios en `src/services/`
- **Problema:** No se implementa prefetching de datos para navegación anticipada
- **Impacto:** Tiempos de carga percibidos más lentos entre páginas

#### 6. **StaleTime Genérico en React Query**
- **Archivo:** `src/components/providers.tsx`
- **Problema:** `staleTime: 60 * 1000` (1 minuto) para todas las queries
- **Impacto:** Refetching innecesario de datos que no cambian frecuentemente

#### 7. **Re-renders Potenciales en Auth Store**
- **Archivo:** `src/store/auth.ts`
- **Problema:** Uso de `useAuthStore()` sin selectores específicos causa re-renders
- **Ejemplo:** `const { user } = useAuthStore()` selecciona todo el estado

#### 8. **CSS sin Purge Completo**
- **Archivo:** `tailwind.config.js`
- **Problema:** Content configura rutas que podrían no existir (`./pages/**/*`)
- **Impacto:** CSS bundle más grande de lo necesario

---

### 🟢 Prioridad Baja

#### 9. **Falta de Service Worker**
- **Problema:** No hay PWA ni Service Worker para offline
- **Impacto:** No hay caching offline ni experiencia app-like

#### 10. **Font Loading No Optimizado**
- **Archivo:** `src/app/layout.tsx`
- **Problema:** Fuente Inter cargada sin `display: swap`
- **Impacto:** Posible FOIT (Flash of Invisible Text)

---

## 💡 Recomendaciones Específicas

### 1. Implementar Code Splitting con Dynamic Imports

**Archivos a modificar:** `src/app/dashboard/candidates/page.tsx`

```typescript
// ANTES - Carga síncrona
import { EvaluationModal } from '@/components/evaluations/EvaluationModal';
import { CandidateForm } from '@/components/candidates/CandidateForm';

// DESPUÉS - Lazy loading
import dynamic from 'next/dynamic';

const EvaluationModal = dynamic(
  () => import('@/components/evaluations/EvaluationModal').then(mod => mod.EvaluationModal),
  { 
    loading: () => <div className="p-4 text-center">Cargando...</div>,
    ssr: false 
  }
);

const CandidateForm = dynamic(
  () => import('@/components/candidates/CandidateForm').then(mod => mod.CandidateForm),
  { 
    loading: () => <div className="p-4"><Skeleton className="h-96" /></div> 
  }
);
```

**Estimación de mejora:** Reducir bundle inicial en ~40-60 KB (15-20%)

---

### 2. Configurar Optimización de Imágenes

**Archivo:** `next.config.js`

```javascript
const nextConfig = {
  // ... configuración existente
  
  images: {
    formats: ['image/webp', 'image/avif'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',
      },
    ],
    deviceSizes: [640, 750, 828, 1080, 1200],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 días
  },
  
  // Experimental: Compresión de build
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
}
```

**Estimación de mejora:** Reducir LCP en 0.5-1s en páginas con imágenes

---

### 3. Condicional para React Query Devtools

**Archivo:** `src/components/providers.tsx`

```typescript
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
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        // Optimización: Retry exponencial
        retry: (failureCount, error: any) => {
          if (error?.response?.status === 401 || error?.response?.status === 403) {
            return false;
          }
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Solo cargar devtools en desarrollo */}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
```

**Estimación de mejora:** Ahorro de ~20-30 KB en producción

---

### 4. Optimizar Selectores de Zustand

**Archivo:** `src/store/auth.ts` (ya está bien, pero uso en componentes)

```typescript
// ANTES - En componentes como dashboard/page.tsx
const { user } = useAuthStore(); // Re-render en cualquier cambio de estado

// DESPUÉS - Selectores específicos
const user = useAuthStore(state => state.user); // Solo re-render cuando user cambia
const isAuthenticated = useAuthStore(state => state.isAuthenticated);

// O usar selectors múltiples con shallow
import { shallow } from 'zustand/shallow';

const { user, isAuthenticated } = useAuthStore(
  state => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
  shallow
);
```

**Estimación de mejora:** Reducir re-renders innecesarios en ~30-50%

---

### 5. Implementar Prefetching en Navegación

**Nuevo archivo:** `src/hooks/usePrefetch.ts`

```typescript
import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { candidateService } from '@/services/candidates';
import { jobService } from '@/services/jobs';

export function usePrefetch() {
  const queryClient = useQueryClient();

  const prefetchCandidates = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['candidates'],
      queryFn: () => candidateService.getCandidates({}),
      staleTime: 5 * 60 * 1000, // 5 minutos
    });
  }, [queryClient]);

  const prefetchJobs = useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: ['jobs'],
      queryFn: () => jobService.getJobs({}),
      staleTime: 5 * 60 * 1000,
    });
  }, [queryClient]);

  return { prefetchCandidates, prefetchJobs };
}
```

**Uso en componentes:**

```typescript
// En Sidebar o Navbar
const { prefetchCandidates } = usePrefetch();

<Link 
  href="/dashboard/candidates" 
  onMouseEnter={prefetchCandidates} // Prefetch al hacer hover
>
  Candidatos
</Link>
```

**Estimación de mejora:** Reducir perceived load time en ~200-500ms

---

### 6. Configurar staleTime por Tipo de Dato

**Archivo:** `src/services/candidates.ts` (ejemplo de uso)

```typescript
// En componentes, ajustar staleTime según volatilidad de datos
const { data: candidates } = useQuery({
  queryKey: ['candidates', filters],
  queryFn: () => candidateService.getCandidates(filters),
  staleTime: 2 * 60 * 1000, // 2 minutos - datos semi-volátiles
  cacheTime: 10 * 60 * 1000, // 10 minutos en caché
});

// Para datos casi estáticos (configuración, etc.)
const { data: config } = useQuery({
  queryKey: ['config'],
  queryFn: () => configService.getConfig(),
  staleTime: 30 * 60 * 1000, // 30 minutos
  cacheTime: 60 * 60 * 1000, // 1 hora
});
```

**Estimación de mejora:** Reducir requests innecesarios en ~40-60%

---

### 7. Optimizar Tailwind CSS

**Archivo:** `tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    // Remover rutas que no existen
    // './pages/**/*.{ts,tsx}', // No usado (App Router)
    
    // Usar rutas específicas
    './src/app/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
  ],
  theme: {
    // ... configuración existente
  },
  plugins: [require("tailwindcss-animate")],
  
  // Optimización: Desactivar features no usadas
  corePlugins: {
    // Si no usas gradientes predefinidos
    // gradientColorStops: false,
    // opacity: false, // Si usas siempre opacidades custom
  },
}
```

**Estimación de mejora:** Reducir CSS bundle en ~10-20 KB

---

### 8. Optimizar Carga de Fuentes

**Archivo:** `src/app/layout.tsx`

```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from '@/components/ui/toaster'
import { Providers } from '@/components/providers'
import { Navbar } from '@/components/navbar'

const inter = Inter({ 
  subsets: ['latin'],
  display: 'swap', // Evita FOIT
  preload: true,
  variable: '--font-inter', // Para usar con CSS variable
})

export const metadata: Metadata = {
  title: 'ATS Preselection Platform',
  description: 'Plataforma de preselección automatizada de candidatos',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" className={inter.variable}>
      <body className={`${inter.className} antialiased`}>
        <Providers>
          <Navbar />
          {children}
        </Providers>
        <Toaster />
      </body>
    </html>
  )
}
```

---

### 9. Implementar Web Vitals Monitoring

**Nuevo archivo:** `src/components/WebVitals.tsx`

```typescript
'use client';

import { useReportWebVitals } from 'next/web-vitals';

export function WebVitals() {
  useReportWebVitals((metric) => {
    // Enviar a analytics
    console.log(metric);
    
    // Ejemplo: enviar a Google Analytics 4
    if (typeof window.gtag !== 'undefined') {
      window.gtag('event', metric.name, {
        value: Math.round(metric.value),
        event_category: 'Web Vitals',
        event_label: metric.id,
        non_interaction: true,
      });
    }
  });

  return null;
}
```

**Agregar en layout.tsx:**

```typescript
import { WebVitals } from '@/components/WebVitals';

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>
        <WebVitals />
        {/* ... */}
      </body>
    </html>
  );
}
```

---

### 10. Script de Análisis de Bundle

**Nuevo archivo:** `scripts/analyze-bundle.js`

```javascript
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ANALYZE = process.env.ANALYZE === 'true';

if (ANALYZE) {
  console.log('📊 Analyzing bundle...');
  
  try {
    execSync('npx next build', { 
      stdio: 'inherit',
      env: { ...process.env, ANALYZE: 'true' }
    });
  } catch (e) {
    console.error('Build failed:', e);
  }
}
```

**Package.json:**

```json
{
  "scripts": {
    "analyze": "cross-env ANALYZE=true next build"
  },
  "devDependencies": {
    "cross-env": "^7.0.3"
  }
}
```

---

## 📊 Estimación de Mejoras Totales

| Métrica | Actual | Después | Mejora |
|---------|--------|---------|--------|
| **Bundle Size** | ~700 KB | ~500 KB | **-28%** |
| **LCP** | 2.5-3.5s | 1.5-2s | **-40%** |
| **Re-renders** | Alto | Bajo | **-50%** |
| **Requests API** | 100/hr | 40/hr | **-60%** |
| **Build Size** | 323 MB | <50 MB | **-85%** |

---

## ✅ Checklist de Implementación

### Fase 1: Quick Wins (1-2 días)
- [ ] Configurar imágenes en `next.config.js`
- [ ] Mover React Query Devtools a development only
- [ ] Optimizar selectores de Zustand
- [ ] Limpiar caché de build (`.next`)
- [ ] Optimizar carga de fuentes

### Fase 2: Code Splitting (2-3 días)
- [ ] Implementar dynamic imports en modales
- [ ] Lazy loading para EvaluationModal
- [ ] Lazy loading para CandidateForm y JobForm
- [ ] Lazy loading para componentes pesados de terceros

### Fase 3: Data Optimization (2-3 días)
- [ ] Implementar prefetching en navegación
- [ ] Ajustar staleTime por tipo de dato
- [ ] Configurar caché estratégica

### Fase 4: Monitoreo (1 día)
- [ ] Implementar Web Vitals reporting
- [ ] Configurar bundle analyzer
- [ ] Setup de monitoreo de performance

---

## 🛠️ Herramientas Recomendadas

```bash
# Bundle analyzer
npm install --save-dev @next/bundle-analyzer cross-env

# Lighthouse CI
npm install --save-dev lighthouse @lhci/cli

# Performance budgets
npm install --save-dev bundlesize

# Prettier para Tailwind
npm install --save-dev prettier-plugin-tailwindcss
```

---

## 📚 Referencias

- [Next.js Performance Best Practices](https://nextjs.org/docs/app/building-your-application/optimizing)
- [React Query Performance](https://tanstack.com/query/latest/docs/react/guides/important-defaults)
- [Zustand Best Practices](https://docs.pmnd.rs/zustand/guides/prevent-rerenders-with-equality-fn)
- [Web Vitals](https://web.dev/vitals/)

---

**Nota:** Este reporte debe revisarse y actualizarse después de implementar las optimizaciones para medir el impacto real.
