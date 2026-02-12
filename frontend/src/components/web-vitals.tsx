'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

// Tipos para Web Vitals
interface Metric {
  id: string;
  name: string;
  startTime: number;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  entries: PerformanceEntry[];
}

// Función para enviar métricas a analytics (placeholder)
function sendToAnalytics(metric: Metric) {
  // Aquí puedes enviar a Google Analytics, Sentry, etc.
  // Por ahora solo logueamos en desarrollo
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Web Vitals] ${metric.name}: ${metric.value} (${metric.rating})`);
  }
  
  // Ejemplo de envío a endpoint propio:
  // fetch('/api/metrics', {
  //   method: 'POST',
  //   body: JSON.stringify(metric),
  //   keepalive: true,
  // });
}

// Obtener rating basado en umbrales
function getRating(name: string, value: number): Metric['rating'] {
  switch (name) {
    case 'CLS':
      return value <= 0.1 ? 'good' : value <= 0.25 ? 'needs-improvement' : 'poor';
    case 'FCP':
      return value <= 1800 ? 'good' : value <= 3000 ? 'needs-improvement' : 'poor';
    case 'FID':
      return value <= 100 ? 'good' : value <= 300 ? 'needs-improvement' : 'poor';
    case 'LCP':
      return value <= 2500 ? 'good' : value <= 4000 ? 'needs-improvement' : 'poor';
    case 'TTFB':
      return value <= 800 ? 'good' : value <= 1800 ? 'needs-improvement' : 'poor';
    case 'INP':
      return value <= 200 ? 'good' : value <= 500 ? 'needs-improvement' : 'poor';
    default:
      return 'good';
  }
}

// Medir Web Vitals
function measureWebVitals() {
  // Verificar si estamos en el navegador
  if (typeof window === 'undefined' || !('performance' in window)) {
    return;
  }

  // CLS (Cumulative Layout Shift)
  let clsValue = 0;
  let clsEntries: PerformanceEntry[] = [];
  
  const clsObserver = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!(entry as any).hadRecentInput) {
        clsValue += (entry as any).value;
        clsEntries.push(entry);
      }
    }
  });
  
  try {
    clsObserver.observe({ entryTypes: ['layout-shift'] as any });
  } catch (e) {
    // Layout Shift observer no soportado
  }

  // LCP (Largest Contentful Paint)
  let lcpValue = 0;
  let lcpEntries: PerformanceEntry[] = [];
  
  const lcpObserver = new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    lcpValue = (lastEntry as any).startTime;
    lcpEntries = entries;
  });
  
  try {
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] as any });
  } catch (e) {
    // LCP observer no soportado
  }

  // FCP (First Contentful Paint)
  const fcpObserver = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if ((entry as any).name === 'first-contentful-paint') {
        const metric: Metric = {
          id: entry.name,
          name: 'FCP',
          startTime: entry.startTime,
          value: entry.startTime,
          rating: getRating('FCP', entry.startTime),
          delta: entry.startTime,
          entries: [entry],
        };
        sendToAnalytics(metric);
      }
    }
  });
  
  try {
    fcpObserver.observe({ entryTypes: ['paint'] as any });
  } catch (e) {
    // Paint observer no soportado
  }

  // TTFB (Time to First Byte)
  const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  if (navigation) {
    const ttfb = navigation.responseStart - navigation.startTime;
    const metric: Metric = {
      id: 'ttfb',
      name: 'TTFB',
      startTime: navigation.startTime,
      value: ttfb,
      rating: getRating('TTFB', ttfb),
      delta: ttfb,
      entries: [navigation],
    };
    sendToAnalytics(metric);
  }

  // Enviar CLS y LCP cuando el usuario abandona la página
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      if (clsValue > 0) {
        const metric: Metric = {
          id: 'cls',
          name: 'CLS',
          startTime: 0,
          value: clsValue,
          rating: getRating('CLS', clsValue),
          delta: clsValue,
          entries: clsEntries,
        };
        sendToAnalytics(metric);
      }
      
      if (lcpValue > 0) {
        const metric: Metric = {
          id: 'lcp',
          name: 'LCP',
          startTime: lcpValue,
          value: lcpValue,
          rating: getRating('LCP', lcpValue),
          delta: lcpValue,
          entries: lcpEntries,
        };
        sendToAnalytics(metric);
      }
      
      clsObserver.disconnect();
      lcpObserver.disconnect();
      fcpObserver.disconnect();
    }
  });
}

export function WebVitals() {
  const pathname = usePathname();

  useEffect(() => {
    measureWebVitals();
  }, [pathname]);

  return null; // Componente invisible, solo para medir
}

export default WebVitals;
