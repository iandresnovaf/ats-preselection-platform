# Arquitectura del Producto - RH Suite

## 🏗️ Visión General

La plataforma ATS está compuesta por dos productos independientes pero integrables:

```
┌─────────────────────────────────────────────────────────────┐
│                    RH SUITE                                 │
├──────────────────────┬──────────────────────────────────────┤
│      RHMatch         │           RHTools                    │
│   (Sistema de IA)    │    (Gestión de Reclutamiento)        │
├──────────────────────┼──────────────────────────────────────┤
│ • Matching IA        │ • Gestión de Clientes                │
│ • Score 0-100        │ • Pipeline Visual (Kanban)           │
│ • Análisis de CVs    │ • Submissions de Candidatos          │
│ • Preguntas IA       │ • Documentos con OCR                 │
│ • Recomendaciones    │ • Procesamiento de CVs               │
└──────────────────────┴──────────────────────────────────────┘
           │                           │
           └───────────┬───────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
│  Zoho  │      │    Odoo     │    │   Standalone│
│Recruit │      │   HR Module │    │   (Sin CRM) │
└────────┘      └─────────────┘    └─────────────┘
```

---

## 🤖 RHMatch - Sistema de Matching IA

### Descripción
RHMatch es el **motor de inteligencia artificial** que analiza candidatos contra ofertas de trabajo.

### Funcionalidades Core
- **Análisis de Matching**: Compara CVs contra Job Descriptions usando OpenAI
- **Score Inteligente**: 0-100 con breakdown por skills, experiencia, educación
- **Recomendaciones**: PROCEED / REVIEW / REJECT automáticos
- **Preguntas de Entrevista**: Generadas por IA basadas en gaps y fortalezas
- **Análisis de CVs**: Extracción automática de datos (PDF, DOCX)

### Modos de Uso

#### 1. Standalone (Sin CRM externo)
```
RHMatch → Base de datos propia → Resultados
```
- Usa su propia base de datos de candidatos
- No requiere integraciones externas
- Ideal para empresas que empiezan o no usan CRM

#### 2. Conectado a Zoho Recruit
```
Zoho Recruit ←→ RHMatch ←→ Análisis IA
```
- Sincronización bidireccional de candidatos
- Jobs creados en Zoho, analizados en RHMatch
- Resultados visibles en ambos sistemas

#### 3. Conectado a Odoo HR
```
Odoo (hr.job, hr.applicant) ←→ RHMatch ←→ Análisis IA
```
- Integración con módulo de reclutamiento de Odoo
- Sync de puestos y aplicantes
- Funciona dentro del ecosistema Odoo

#### 4. Conectado a RHTools (modo híbrido completo)
```
RHTools (Clientes, Pipeline) + RHMatch (IA) = Suite completa
```
- La solución más completa
- Gestión de clientes + Pipeline + IA en una plataforma
- Recomendado para consultoras de reclutamiento

---

## 🛠️ RHTools - Sistema de Gestión de Reclutamiento

### Descripción
RHTools es el **CRM y sistema de operaciones** para consultoras de reclutamiento.

### Funcionalidades Core
- **Gestión de Clientes**: Empresas que contratan servicios
- **Pipeline Visual**: Kanban de candidatos por etapas
- **Submissions**: Envío de candidatos a clientes
- **Documentos**: Almacenamiento con OCR (PDF, DOCX, imágenes)
- **Procesamiento de CVs**: Extracción automática de información

### Uso Independiente
RHTools puede usarse **sin RHMatch** como un sistema de gestión de reclutamiento tradicional:
- Gestión de candidatos manual
- Pipeline sin análisis IA
- Documentos y submissions normales

### Uso Integrado (RHMatch + RHTools)
Cuando se usa junto con RHMatch:
- Cada candidato tiene score de matching automático
- El pipeline muestra recomendaciones IA (PROCEED/REVIEW/REJECT)
- Preguntas de entrevista generadas por IA para cada submission
- Análisis de ajuste cultural y técnico automático

---

## 🔌 Sistema de Integraciones

### Conectores Disponibles

| Integración | Tipo | Estado | Descripción |
|-------------|------|--------|-------------|
| **Zoho Recruit** | CRM ATS | ✅ Listo | Sync bidireccional de jobs y candidatos |
| **Odoo HR** | ERP | ✅ Listo | Integración con módulo hr.applicant |
| **LinkedIn** | Red Social | ✅ Listo | Import de perfiles y extracción de datos |
| **RHTools** | Módulo interno | ✅ Listo | Comunicación directa vía API interna |

### Arquitectura de Integraciones

```
┌──────────────────────────────────────┐
│           RHMatch Core               │
│  (Matching Service, AI Analysis)     │
└──────────────┬───────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌──▼─────┐
│  Zoho  │ │  Odoo  │ │LinkedIn│ │RHTools │
│Adapter │ │Adapter │ │Adapter │ │Adapter │
└────────┘ └────────┘ └────────┘ └────────┘
```

Cada integración:
- Usa el patrón **Adapter** (mismo interface, diferentes implementaciones)
- Soporta **sync bidireccional** (lectura y escritura)
- Tiene **cache** para evitar llamadas repetidas
- Maneja **rate limiting** de APIs externas

---

## 📊 Matriz de Compatibilidad

| Funcionalidad | RHMatch Solo | RHMatch + Zoho | RHMatch + Odoo | RHMatch + RHTools |
|---------------|--------------|----------------|----------------|-------------------|
| Matching IA | ✅ | ✅ | ✅ | ✅ |
| Score 0-100 | ✅ | ✅ | ✅ | ✅ |
| Preguntas IA | ✅ | ✅ | ✅ | ✅ |
| Pipeline Kanban | ❌ | ❌ | ❌ | ✅ |
| Gestión Clientes | ❌ | ❌ | ❌ | ✅ |
| Submissions | ❌ | ⚠️ Parcial | ⚠️ Parcial | ✅ |
| Documentos OCR | ✅ | ⚠️ Parcial | ⚠️ Parcial | ✅ |

**Leyenda:**
- ✅ Completo
- ⚠️ Parcial (depende del CRM externo)
- ❌ No disponible

---

## 🚀 Recomendaciones de Uso

### Para Empresas Pequeñas (sin CRM)
**Opción**: RHMatch Standalone
- Rápido de implementar
- No requiere integraciones
- Base de datos propia

### Para Empresas con Zoho Recruit
**Opción**: RHMatch + Zoho Recruit
- Aprovecha inversión existente en Zoho
- Mejora el matching de candidatos
- Mantiene flujo de trabajo familiar

### Para Empresas con Odoo
**Opción**: RHMatch + Odoo HR
- Integración nativa con ERP
- Un solo sistema para todo
- Ideal si ya usan Odoo

### Para Consultoras de Reclutamiento
**Opción**: RHMatch + RHTools (Suite Completa)
- La solución más potente
- Gestión de clientes + IA avanzada
- Pipeline visual con análisis automático

---

## 🔧 Configuración por Modo

### Modo Standalone (RHMatch Solo)
```bash
# .env
ENVIRONMENT=production
RH_MODE=standalone
OPENAI_API_KEY=sk-...
```

### Modo Zoho Recruit
```bash
# .env
RH_MODE=zoho
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=...
```

### Modo Odoo
```bash
# .env
RH_MODE=odoo
ODOO_URL=https://miempresa.odoo.com
ODOO_DB=miempresa
ODOO_API_KEY=...
```

### Modo Completo (RHMatch + RHTools)
```bash
# .env
RH_MODE=full
ENABLE_RHTOOLS=true
```

---

## 📈 Roadmap de Integraciones

### Fase 1 (Actual) ✅
- Zoho Recruit
- Odoo HR
- LinkedIn
- RHTools

### Fase 2 (Próxima)
- Greenhouse
- Lever
- Workday
- SAP SuccessFactors

---

## 💡 Notas de Arquitectura

1. **Desacoplamiento**: RHMatch y RHTools son independientes
2. **Conectores**: Cada integración es un adapter intercambiable
3. **Cache**: Redis compartido para todas las integraciones
4. **Seguridad**: OAuth2 para todas las integraciones externas
5. **Escalabilidad**: Procesamiento async vía Celery

---

**Versión**: 1.1.0  
**Última actualización**: 2026-02-12  
**Autor**: Equipo de Desarrollo RH Suite
