# 📋 ATS Platform - Project Plan

## 📌 Resumen Ejecutivo

**Proyecto:** ATS Platform  
**Fecha de creación:** 2026-02-11  
**Estado:** Planning  
**Objetivo:** Resolver 9 issues críticos priorizando seguridad, estabilidad y calidad del código.

---

## 🎯 Milestones

| Milestone | Fecha Límite | Descripción |
|-----------|--------------|-------------|
| **M1 - Seguridad Crítica** | 2026-02-14 | Fixes de seguridad de alta prioridad desplegados |
| **M2 - Estabilidad Core** | 2026-02-18 | Fixes de funcionalidad core estabilizados |
| **M3 - Producción Ready** | 2026-02-25 | Mejoras implementadas y cobertura de tests establecida |

---

## 🚀 Fase 1: Fixes Críticos de Seguridad

**Objetivo:** Resolver vulnerabilidades de seguridad que ponen en riesgo la producción.

**Fecha inicio:** 2026-02-11  
**Deadline (M1):** 2026-02-14  
**Duración estimada:** 3 días

### Tareas

#### SEC-001: Reemplazar SECRET_KEY hardcodeada
- **ID:** SEC-001
- **Descripción:** Migrar SECRET_KEY desde backend/.env hardcodeada a variable de entorno segura con generación dinámica
- **Prioridad:** P0 (Crítico)
- **Dependencias:** Ninguna
- **Estimación:** 4 horas
- **Rol asignado:** Backend Security Engineer
- **Criterios de aceptación:**
  - [ ] SECRET_KEY leída de variable de entorno
  - [ ] Script de generación de clave segura creado
  - [ ] Documentación de deployment actualizada
  - [ ] Clave anterior rotada y revocada

#### SEC-002: Implementar Rate Limiting en Auth
- **ID:** SEC-002
- **Descripción:** Agregar rate limiting en endpoints /auth/login, /auth/register, /auth/refresh usando slowapi o similar
- **Prioridad:** P0 (Crítico)
- **Dependencias:** Ninguna
- **Estimación:** 6 horas
- **Rol asignado:** Backend Developer
- **Criterios de aceptación:**
  - [ ] Rate limiting implementado (5 intentos/minuto por IP)
  - [ ] Headers X-RateLimit-* incluidos en respuestas
  - [ ] Manejo de excepciones graceful
  - [ ] Tests unitarios para rate limiting

#### SEC-003: Agregar Headers de Seguridad
- **ID:** SEC-003
- **Descripción:** Implementar headers de seguridad HTTP (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
- **Prioridad:** P0 (Crítico)
- **Dependencias:** Ninguna
- **Estimación:** 4 horas
- **Rol asignado:** Backend Security Engineer
- **Criterios de aceptación:**
  - [ ] Middleware de seguridad implementado
  - [ ] Headers configurados siguiendo OWASP guidelines
  - [ ] CSP policy definida y documentada
  - [ ] Verificación con securityheaders.com

#### SEC-004: Migrar Tokens de localStorage a httpOnly Cookies
- **ID:** SEC-004
- **Descripción:** Reemplazar almacenamiento de JWT en localStorage por cookies httpOnly con SameSite=Strict
- **Prioridad:** P0 (Crítico)
- **Dependencias:** Ninguna
- **Estimación:** 8 horas
- **Roles asignados:** Full Stack Developer, Frontend Developer
- **Criterios de aceptación:**
  - [ ] Backend configurado para enviar tokens en cookies httpOnly
  - [ ] Frontend actualizado para no usar localStorage
  - [ ] CSRF protection implementada
  - [ ] Flujo de refresh token actualizado
  - [ ] Testing en múltiples browsers

---

## 🔧 Fase 2: Fixes de Funcionalidad Core

**Objetivo:** Resolver bugs que impiden el correcto funcionamiento del sistema.

**Fecha inicio:** 2026-02-14 (tras M1)  
**Deadline (M2):** 2026-02-18  
**Duración estimada:** 4 días

### Tareas

#### FIX-001: Corregir Serialización UserStatus Enum
- **ID:** FIX-001
- **Descripción:** Fix 500 error en activar/desactivar usuarios causado por serialización incorrecta del enum UserStatus
- **Prioridad:** P1 (Alta)
- **Dependencias:** Ninguna (puede trabajarse en paralelo con Fase 1)
- **Estimación:** 3 horas
- **Rol asignado:** Backend Developer
- **Criterios de aceptación:**
  - [ ] Identificar causa root del error 500
  - [ ] Implementar serialización correcta del enum
  - [ ] Validar request/response schemas con Pydantic
  - [ ] Tests de integración para el endpoint

#### FIX-002: Eliminar Imports Duplicados en main.py
- **ID:** FIX-002
- **Descripción:** Limpiar imports duplicados de auth y users en main.py, refactorizar estructura de routers
- **Prioridad:** P1 (Alta)
- **Dependencias:** Ninguna
- **Estimación:** 2 horas
- **Rol asignado:** Backend Developer
- **Criterios de aceptación:**
  - [ ] Identificar todos los imports duplicados
  - [ ] Refactorizar estructura de routers si es necesario
  - [ ] Aplicar linter (flake8/pylint) sin warnings
  - [ ] Verificar que la app inicia correctamente

#### FIX-003: Auditar y Corregir CORS Configuration
- **ID:** FIX-003
- **Descripción:** Reemplazar CORS wildcard (*) por origenes explícitos y configuración segura
- **Prioridad:** P1 (Alta)
- **Dependencias:** SEC-003 (headers de seguridad)
- **Estimación:** 3 horas
- **Rol asignado:** Backend Developer
- **Criterios de aceptación:**
  - [ ] Lista de orígenes permitidos definida por entorno
  - [ ] CORS configurado con origins explícitos
  - [ ] Métodos y headers restringidos a lo necesario
  - [ ] Documentación de política CORS

---

## 📈 Fase 3: Mejoras y Deuda Técnica

**Objetivo:** Mejorar calidad del código, extensibilidad y mantenibilidad.

**Fecha inicio:** 2026-02-18 (tras M2)  
**Deadline (M3):** 2026-02-25  
**Duración estimada:** 7 días

### Tareas

#### IMP-001: Implementar Rol "viewer"
- **ID:** IMP-001
- **Descripción:** Agregar rol "viewer" en backend con permisos de solo lectura, actualizar middleware de autorización
- **Prioridad:** P2 (Media)
- **Dependencias:** FIX-001 (UserStatus funcionando)
- **Estimación:** 6 horas
- **Rol asignado:** Backend Developer
- **Criterios de aceptación:**
  - [ ] Enum de roles actualizado con "viewer"
  - [ ] Middleware de autorización soporta nuevo rol
  - [ ] Permisos de solo lectura definidos
  - [ ] Actualizar/seeder de roles existentes
  - [ ] Documentación de matriz de permisos

#### IMP-002: Establecer Infraestructura de Testing
- **ID:** IMP-002
- **Descripción:** Configurar pytest, coverage, crear tests unitarios y de integración base
- **Prioridad:** P1 (Alta)
- **Dependencias:** FIX-001, FIX-002 (funcionalidad core estable)
- **Estimación:** 12 horas
- **Rol asignado:** QA Engineer / Backend Developer
- **Criterios de aceptación:**
  - [ ] pytest configurado con fixtures
  - [ ] Base de datos de test configurada (SQLite/memory)
  - [ ] Tests unitarios para servicios críticos (>60% coverage)
  - [ ] Tests de integración para endpoints auth
  - [ ] CI pipeline ejecutando tests
  - [ ] Badge de coverage en README

#### IMP-003: Tests E2E para Flujos Críticos
- **ID:** IMP-003
- **Descripción:** Implementar tests end-to-end para flujos de autenticación y gestión de usuarios
- **Prioridad:** P2 (Media)
- **Dependencias:** IMP-002 (infraestructura de testing), SEC-004 (tokens en cookies)
- **Estimación:** 10 horas
- **Rol asignado:** QA Engineer
- **Criterios de aceptación:**
  - [ ] Tests E2E para login/logout
  - [ ] Tests E2E para CRUD de usuarios
  - [ ] Tests E2E para activar/desactivar usuarios
  - [ ] playwright o similar configurado
  - [ ] Tests ejecutables en CI

---

## 📊 Diagrama de Dependencias

```
FASE 1 (Seguridad Crítica)        FASE 2 (Funcionalidad)          FASE 3 (Mejoras)
═══════════════════════          ══════════════════════          ════════════════

SEC-001 ──┐
            ├──→ M1 (Feb 14) ──┐
SEC-002 ──┤                    │
            │                  ├──→ M2 (Feb 18) ──┐
SEC-003 ──┤                    │                  │
            │                  │                  ├──→ M3 (Feb 25)
SEC-004 ──┘                  FIX-001 ─────────────┘                  │
            (paralelo)         FIX-002 ─────────────┐                │
                               FIX-003 (dep SEC-003)┘                │
                                                                     │
                                                  IMP-001 (dep FIX-001)
                                                  IMP-002 (dep FIX-001, FIX-002)
                                                  IMP-003 (dep IMP-002, SEC-004)
```

---

## 👥 Asignación de Roles

| Rol | Responsabilidades | Tareas Asignadas |
|-----|------------------|------------------|
| **Backend Security Engineer** | Vulnerabilidades, headers, keys | SEC-001, SEC-003 |
| **Backend Developer** | Lógica de negocio, APIs | SEC-002, FIX-001, FIX-002, FIX-003, IMP-001 |
| **Frontend Developer** | Cambios en cliente | SEC-004 (parte frontend) |
| **Full Stack Developer** | Integración, cookies | SEC-004 |
| **QA Engineer** | Testing, cobertura | IMP-002, IMP-003 |

---

## 🏃 Plan de Ejecución Paralela

### Día 1-3 (Fase 1 - Sprint de Seguridad)

**Equipo Backend Security:**
- SEC-001 + SEC-003 (8 horas)

**Equipo Backend:**
- SEC-002 (6 horas)

**Equipo Full Stack:**
- SEC-004 (8 horas)

### Día 4-7 (Fase 2 - Sprint de Estabilidad)

**Equipo Backend:**
- FIX-001 + FIX-002 (5 horas, paralelo con seguridad)
- FIX-003 (3 horas, post M1)

### Día 8-14 (Fase 3 - Sprint de Calidad)

**Equipo Backend:**
- IMP-001 (6 horas)

**Equipo QA + Backend:**
- IMP-002 (12 horas)
- IMP-003 (10 horas, paralelo con IMP-002)

---

## 📈 Métricas de Éxito

| Métrica | Target | Actual | Notas |
|---------|--------|--------|-------|
| Cobertura de tests | >70% | 0% | Medir post IMP-002 |
| Vulnerabilidades críticas | 0 | 4 | SEC-001, SEC-002, SEC-003, SEC-004 |
| Bugs P0/P1 abiertos | 0 | 2 | FIX-001, FIX-002 |
| Tiempo de respuesta API | <200ms | - | Medir post Fase 2 |
| Score Security Headers | A+ | F | Medir post SEC-003 |

---

## 📝 Notas y Riesgos

### Riesgos Identificados

1. **Riesgo:** Cambio de tokens a cookies puede romper integración frontend  
   **Mitigación:** SEC-004 debe incluir tiempo de testing cross-browser

2. **Riesgo:** Rate limiting puede afectar usuarios legítimos  
   **Mitigación:** Implementar whitelist para IPs internas, monitoreo de logs

3. **Riesgo:** Falta de tiempo para cobertura de tests  
   **Mitigación:** Priorizar tests de integración sobre unitarios en IMP-002

### Decisiones de Diseño

- **Rate Limiting:** Usar slowapi con Redis backend para producción
- **Cookies:** Usar librería python `itsdangerous` para firmar cookies
- **Testing:** pytest + pytest-asyncio + httpx para tests async
- **CORS:** Configurar via environment variables, no hardcodear

---

## ✅ Checklist de Release

- [ ] Todos los items P0 completados
- [ ] Todos los items P1 completados
- [ ] Security audit pasado (headers, secrets, cookies)
- [ ] Tests pasando en CI (>70% coverage)
- [ ] Documentación actualizada (API, deployment)
- [ ] Variables de entorno documentadas
- [ ] Rollback plan documentado

---

**Plan creado por:** PLanner Agent  
**Revisado por:** [Pendiente]  
**Aprobado por:** [Pendiente]
