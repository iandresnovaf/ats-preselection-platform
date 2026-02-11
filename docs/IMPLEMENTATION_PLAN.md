# 📋 Core ATS - Implementation Plan

## 📌 Resumen

**Proyecto:** Core ATS - Sistema de Seguimiento de Candidatos
**Fecha:** 2026-02-11
**Versión:** 1.0
**Estado:** En Desarrollo

---

## 🎯 Fases de Implementación

### FASE 1: Base de Datos y Modelos ⛁
**Estado:** 🟡 En Progreso (40%)  
**Dependencias:** Ninguna (Fase Crítica)  
**Deadline:** 2026-02-12  
**Responsable:** Database Migration Developer

#### Tareas
| ID | Tarea | Estado | Prioridad |
|----|-------|--------|-----------|
| DB-001 | Alembic setup completo | ✅ Completado | P0 |
| DB-002 | Migration 001_initial | ✅ Completado | P0 |
| DB-003 | Migration 002_core_ats (Jobs, Candidates, Evaluations) | 🔄 En Progreso | P0 |
| DB-004 | Seed data de prueba | ⏳ Pendiente | P1 |
| DB-005 | Índices y optimizaciones | ⏳ Pendiente | P2 |

#### Entregables
- [ ] Migraciones ejecutables sin errores
- [ ] Seed data para testing
- [ ] Diagrama ER actualizado
- [ ] Documentación de schema

---

### FASE 2: APIs Backend 🔌
**Estado:** 🟡 En Progreso (25%)  
**Dependencias:** FASE 1 completada  
**Deadline:** 2026-02-14  
**Responsable:** Backend Developer

#### Módulos a Implementar

##### 2.1 Jobs API
| Endpoint | Método | Estado | Descripción |
|----------|--------|--------|-------------|
| `/api/v1/jobs` | GET | 🔄 En Progreso | Listar ofertas |
| `/api/v1/jobs` | POST | ⏳ Pendiente | Crear oferta |
| `/api/v1/jobs/{id}` | GET | ⏳ Pendiente | Obtener oferta |
| `/api/v1/jobs/{id}` | PUT | ⏳ Pendiente | Actualizar oferta |
| `/api/v1/jobs/{id}` | DELETE | ⏳ Pendiente | Eliminar oferta |
| `/api/v1/jobs/{id}/candidates` | GET | ⏳ Pendiente | Candidatos de oferta |

##### 2.2 Candidates API
| Endpoint | Método | Estado | Descripción |
|----------|--------|--------|-------------|
| `/api/v1/candidates` | GET | ⏳ Pendiente | Listar candidatos |
| `/api/v1/candidates` | POST | ⏳ Pendiente | Crear candidato |
| `/api/v1/candidates/{id}` | GET | ⏳ Pendiente | Obtener candidato |
| `/api/v1/candidates/{id}` | PUT | ⏳ Pendiente | Actualizar candidato |
| `/api/v1/candidates/{id}/evaluations` | GET | ⏳ Pendiente | Evaluaciones del candidato |

##### 2.3 Evaluations API
| Endpoint | Método | Estado | Descripción |
|----------|--------|--------|-------------|
| `/api/v1/evaluations` | GET | ⏳ Pendiente | Listar evaluaciones |
| `/api/v1/evaluations` | POST | ⏳ Pendiente | Crear evaluación |
| `/api/v1/evaluations/{id}` | GET | ⏳ Pendiente | Obtener evaluación |
| `/api/v1/evaluations/{id}/regenerate` | POST | ⏳ Pendiente | Re-generar con IA |

#### Entregables
- [ ] Todos los endpoints implementados
- [ ] Validaciones Pydantic completas
- [ ] Manejo de errores estandarizado
- [ ] Rate limiting aplicado
- [ ] Documentación Swagger actualizada

---

### FASE 3: Integraciones 🔗
**Estado:** 🟡 En Progreso (30%)  
**Dependencias:** FASE 2 en paralelo (no bloqueante)  
**Deadline:** 2026-02-15  
**Responsable:** Integration Developer

#### Servicios a Integrar

##### 3.1 LLM (OpenAI/Anthropic)
| Tarea | Estado | Prioridad |
|-------|--------|-----------|
| Configuración dinámica | ✅ Completado | P0 |
| Prompt de evaluación | 🔄 En Progreso | P0 |
| Parsing de respuestas | ⏳ Pendiente | P0 |
| Fallback entre providers | ⏳ Pendiente | P1 |

##### 3.2 Email (SMTP)
| Tarea | Estado | Prioridad |
|-------|--------|-----------|
| Servicio base | ✅ Completado | P0 |
| Templates dinámicos | ⏳ Pendiente | P1 |
| Queue con Celery | ⏳ Pendiente | P1 |

##### 3.3 Zoho Recruit
| Tarea | Estado | Prioridad |
|-------|--------|-----------|
| OAuth2 flow | ⏳ Pendiente | P1 |
| Sync bidireccional jobs | ⏳ Pendiente | P1 |
| Sync candidatos | ⏳ Pendiente | P1 |
| Webhook handlers | ⏳ Pendiente | P2 |

##### 3.4 WhatsApp Business API
| Tarea | Estado | Prioridad |
|-------|--------|-----------|
| Configuración base | ⏳ Pendiente | P1 |
| Templates aprobados | ⏳ Pendiente | P1 |
| Envío de mensajes | ⏳ Pendiente | P1 |
| Webhook recepción | ⏳ Pendiente | P2 |

#### Entregables
- [ ] Servicios de integración funcionando
- [ ] Manejo de errores y retries
- [ ] Logging de integraciones
- [ ] Documentación de configuración

---

### FASE 4: Frontend 🎨
**Estado:** 🟡 En Progreso (15%)  
**Dependencias:** FASE 2 (APIs disponibles)  
**Deadline:** 2026-02-17  
**Responsable:** Frontend Developer

#### Módulos a Implementar

##### 4.1 Tipos TypeScript
| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `types/jobs.ts` | ✅ Completado | Interfaces de Jobs |
| `types/candidates.ts` | ✅ Completado | Interfaces de Candidates |
| `types/evaluations.ts` | ✅ Completado | Interfaces de Evaluations |

##### 4.2 Servicios API
| Servicio | Estado | Descripción |
|----------|--------|-------------|
| `services/jobs.ts` | ✅ Completado | CRUD de Jobs |
| `services/candidates.ts` | ✅ Completado | CRUD de Candidates |
| `services/evaluations.ts` | ✅ Completado | CRUD de Evaluations |

##### 4.3 Páginas
| Página | Estado | Prioridad |
|--------|--------|-----------|
| `/dashboard/jobs` - Listado | 🔄 En Progreso | P0 |
| `/dashboard/jobs/new` - Crear | 🔄 En Progreso | P0 |
| `/dashboard/jobs/[id]` - Detalle | ⏳ Pendiente | P0 |
| `/dashboard/candidates` - Listado | ⏳ Pendiente | P0 |
| `/dashboard/candidates/[id]` - Detalle | ⏳ Pendiente | P0 |
| `/dashboard/evaluations` - Listado | ⏳ Pendiente | P1 |
| `/dashboard/evaluations/[id]` - Detalle | ⏳ Pendiente | P1 |

##### 4.4 Componentes
| Componente | Estado | Descripción |
|------------|--------|-------------|
| `jobs/JobList.tsx` | 🔄 En Progreso | Lista de ofertas |
| `jobs/JobForm.tsx` | ⏳ Pendiente | Formulario de oferta |
| `jobs/JobDetail.tsx` | ⏳ Pendiente | Detalle de oferta |
| `candidates/CandidateList.tsx` | ⏳ Pendiente | Lista de candidatos |
| `candidates/CandidateDetail.tsx` | ⏳ Pendiente | Detalle de candidato |
| `evaluations/EvaluationCard.tsx` | ⏳ Pendiente | Card de evaluación |

#### Entregables
- [ ] Todas las páginas funcionales
- [ ] Componentes reutilizables
- [ ] Manejo de estados de carga/error
- [ ] Responsive design
- [ ] Navegación fluida

---

### FASE 5: Tests 🧪
**Estado:** ⏳ Pendiente (0%)  
**Dependencias:** FASE 2 y FASE 4 completadas  
**Deadline:** 2026-02-19  
**Responsable:** Tester & QA

#### Backend Tests
| Tipo | Cobertura Target | Estado |
|------|------------------|--------|
| Unit Tests (Services) | 70% | ⏳ Pendiente |
| Integration Tests (APIs) | 80% | ⏳ Pendiente |
| Model Tests | 60% | ⏳ Pendiente |

#### Frontend Tests
| Tipo | Cobertura Target | Estado |
|------|------------------|--------|
| Unit Tests (Services) | 60% | 🔄 En Progreso |
| Component Tests | 50% | ⏳ Pendiente |
| Store Tests | 60% | ✅ Completado |

#### E2E Tests
| Flujo | Estado | Prioridad |
|-------|--------|-----------|
| Crear Job → Agregar Candidate | ⏳ Pendiente | P0 |
| Evaluar Candidate con IA | ⏳ Pendiente | P0 |
| Sincronizar con Zoho | ⏳ Pendiente | P1 |
| Enviar WhatsApp | ⏳ Pendiente | P1 |

#### Entregables
- [ ] Tests unitarios ejecutándose
- [ ] Tests de integración pasando
- [ ] Tests E2E automatizados
- [ ] Reporte de cobertura >70%

---

### FASE 6: Documentación y Deploy 🚀
**Estado:** ⏳ Pendiente (0%)  
**Dependencias:** Todas las fases anteriores  
**Deadline:** 2026-02-20  
**Responsable:** Todo el equipo

#### Documentación
| Documento | Estado | Responsable |
|-----------|--------|-------------|
| `USER_GUIDE.md` | ⏳ Pendiente | Planner |
| `API_DOCUMENTATION.md` | ⏳ Pendiente | Backend Dev |
| `DEPLOYMENT.md` | ⏳ Pendiente | Backend Dev |
| `TROUBLESHOOTING.md` | ⏳ Pendiente | QA |

#### Deploy
| Tarea | Estado | Descripción |
|-------|--------|-------------|
| Docker compose producción | ⏳ Pendiente | Configuración final |
| CI/CD pipeline | ⏳ Pendiente | GitHub Actions |
| Variables de entorno | ⏳ Pendiente | Documentación |
| Backup strategy | ⏳ Pendiente | PostgreSQL + S3 |

#### Entregables
- [ ] Documentación completa
- [ ] Ambiente de producción listo
- [ ] Pipeline CI/CD funcionando
- [ ] Rollback plan documentado

---

## 📊 Timeline Visual

```
Feb 11    Feb 12    Feb 13    Feb 14    Feb 15    Feb 16    Feb 17    Feb 18    Feb 19    Feb 20
  |         |         |         |         |         |         |         |         |         |
  ├─[FASE 1: Database]──────────────────────────────┤
  |         ├─[FASE 2: Backend APIs]───────────────────────────────────┤
  |         |         ├─[FASE 3: Integrations]───────────────────────────────────────────────┤
  |         |         |         ├─[FASE 4: Frontend]─────────────────────────────────────────┤
  |         |         |         |         |         ├─[FASE 5: Tests]────────────────────────┤
  |         |         |         |         |         |         |         ├─[FASE 6: Deploy]───┤
  ▼         ▼         ▼         ▼         ▼         ▼         ▼         ▼         ▼         ▼
```

---

## 🚨 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Retraso en FASE 1 (Database) | Media | Alto | Backend puede usar mocks temporales |
| APIs no listas para Frontend | Media | Alto | Frontend usar datos mock/fake |
| Integraciones con LLM fallan | Baja | Alto | Implementar fallback a múltiples providers |
| Cobertura de tests insuficiente | Media | Medio | Priorizar tests de integración sobre unitarios |
| Problemas de CORS en deploy | Baja | Medio | Configurar CORS dinámico desde env vars |

---

## ✅ Definition of Done

### Por Fase
- **FASE 1:** Migraciones ejecutan sin errores, seed data funciona
- **FASE 2:** Todos los endpoints responden correctamente, tests de integración pasan
- **FASE 3:** Servicios de integración funcionan con credenciales reales de prueba
- **FASE 4:** Todas las páginas son navegables, responsive, sin errores de consola
- **FASE 5:** Cobertura >70%, todos los tests pasan en CI
- **FASE 6:** Deploy en staging exitoso, documentación completa

### General
- [ ] Code review aprobado
- [ ] Tests pasando
- [ ] Documentación actualizada
- [ ] No hay TODOs críticos en el código
- [ ] Logging apropiado implementado
- [ ] Manejo de errores completo

---

**Última actualización:** 2026-02-11 14:13 GMT-5  
**Próxima revisión:** 2026-02-11 14:23 GMT-5
