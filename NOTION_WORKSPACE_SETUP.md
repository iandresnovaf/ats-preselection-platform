# 🚀 ATS Platform - Project Workspace

## Estructura para Notion

### 1. Databases Principales

#### 📋 Tasks Database
```
Nombre: Tasks
Propiedades:
- Name (Title)
- Status (Select): Backlog | In Progress | Review | Done
- Priority (Select): P0-Critical | P1-High | P2-Medium | P3-Low
- Assignee (Select): Planner | Developer-Backend | Developer-Frontend | Verifier | Tester | Reviewer | Security | QA
- Phase (Select): Fase 1 - Seguridad | Fase 2 - Funcionalidad | Fase 3 - Mejoras
- Dependencies (Relation to Tasks)
- Due Date (Date)
- Estimation (Number) - horas
- Tags (Multi-select): Bug | Feature | Security | Testing | Documentation
```

#### 🐛 Bugs/Issues Database
```
Nombre: Bugs
Propiedades:
- Name (Title)
- Severity (Select): Critical | High | Medium | Low
- Status (Select): New | In Progress | Fixed | Verified | Closed
- Found By (Select): Security | QA | Code Review | Testing
- Component (Select): Backend | Frontend | Database | DevOps
- Related Task (Relation to Tasks)
```

#### 📊 Sprints Database
```
Nombre: Sprints
Propiedades:
- Name (Title)
- Start Date (Date)
- End Date (Date)
- Status (Select): Planning | Active | Completed
- Tasks (Relation to Tasks)
- Goal (Text)
```

---

## Fases del Proyecto

### 🔴 Fase 1: Fixes Críticos de Seguridad
**Deadline:** Inmediato
**Paralelizable:** Sí

| ID | Tarea | Asignado | Prioridad | Estado |
|----|-------|----------|-----------|--------|
| SEC-001 | Mover SECRET_KEY a env vars | Developer-Backend | P0 | In Progress |
| SEC-002 | Implementar rate limiting | Developer-Backend | P0 | In Progress |
| SEC-003 | Agregar headers de seguridad | Developer-Backend | P0 | In Progress |
| SEC-004 | Fix CORS configuration | Developer-Backend | P0 | In Progress |
| SEC-005 | Revisar manejo de tokens en frontend | Developer-Frontend | P0 | In Progress |

### 🟠 Fase 2: Fixes de Funcionalidad
**Deadline:** +2 días
**Paralelizable:** Sí

| ID | Tarea | Asignado | Prioridad | Estado |
|----|-------|----------|-----------|--------|
| FUNC-001 | Fix UserStatus enum serialization | Developer-Backend | P0 | In Progress |
| FUNC-002 | Fix imports duplicados en main.py | Developer-Backend | P0 | In Progress |
| FUNC-003 | Alinear roles frontend/backend | Developer-Frontend | P0 | In Progress |
| FUNC-004 | Fix transformación de usuario | Developer-Frontend | P1 | In Progress |

### 🟡 Fase 3: Mejoras y Testing
**Deadline:** +5 días
**Paralelizable:** Sí

| ID | Tarea | Asignado | Prioridad | Estado |
|----|-------|----------|-----------|--------|
| IMP-001 | Implementar tests unitarios backend | Tester | P1 | In Progress |
| IMP-002 | Implementar tests frontend | Tester | P1 | In Progress |
| IMP-003 | Agregar rol "viewer" en backend | Developer-Backend | P2 | Backlog |
| IMP-004 | Documentación API | Developer-Backend | P2 | Backlog |
| IMP-005 | Optimizaciones de performance | Reviewer | P3 | Backlog |

---

## Workflow Paralelo

```
┌─────────────────────────────────────────────────────────────┐
│                        PLANNER                              │
│  Crea tareas → Asigna prioridades → Define dependencias    │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   DEVELOPER  │ │   DEVELOPER  │ │   TESTER     │
│   BACKEND    │ │   FRONTEND   │ │              │
│  (Seguridad) │ │  (Roles/UI)  │ │  (Tests)     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────┬───────┴───────┬────────┘
                ▼               ▼
         ┌──────────────┐ ┌──────────────┐
         │   REVIEWER   │ │   VERIFIER   │
         │  (Code Review│ │ (Requisitos) │
         └──────┬───────┘ └──────┬───────┘
                │                │
                └────────┬───────┘
                         ▼
                  ┌──────────────┐
                  │     QA       │
                  │ (Aprobación) │
                  └──────────────┘
```

---

## Integración con Equipo Existente

| Rol Original | Rol Nuevo | Colaboración |
|--------------|-----------|--------------|
| Security | Developer-Backend | Security audita → Backend implementa fixes |
| QA | Tester + Reviewer | QA define casos → Tester implementa |
| Code Review | Reviewer | Code Review es parte del Reviewer |

---

## Checklist de Producción

### Pre-Deploy
- [ ] Todos los P0 completados
- [ ] Todos los tests pasando
- [ ] Security audit passed
- [ ] Code review approved
- [ ] Documentation complete

### Post-Deploy
- [ ] Smoke tests en producción
- [ ] Monitoreo activo
- [ ] Rollback plan listo

---

## Notas para Notion

### Vistas Recomendadas
1. **Kanban Board** por Status
2. **Calendar View** por Due Date
3. **Table View** por Prioridad
4. **Board View** por Assignee

### Automatizaciones Sugeridas
- Cuando Task pase a "Done", notificar a Reviewer
- Cuando Bug se cree, asignar a Developer según componente
- Recordatorios 1 día antes de deadline

### Integraciones
- GitHub: Link commits a Tasks
- Slack: Notificaciones de cambios de estado
- Calendar: Sincronizar deadlines

---

## Acceso al Workspace

**URL del Proyecto:** (Configurar en Notion)
**Template:** Duplicar este workspace para nuevos proyectos

---

*Documento creado: 2026-02-11*
*Versión: 1.0*
