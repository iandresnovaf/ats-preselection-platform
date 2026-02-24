# Esquema de Base de Datos ATS - Documentación Técnica

## Resumen Ejecutivo

Este documento describe el esquema completo de base de datos del sistema ATS (Applicant Tracking System), incluyendo las nuevas tablas para procesamiento de CVs, historial de versiones y logs de procesamiento.

**Fecha de actualización:** 2026-02-17  
**Versión del esquema:** 2.0  
**Motor:** PostgreSQL 15+  
**ORM:** SQLAlchemy 2.0+ con asyncpg

---

## Diagrama Entidad-Relación (ER)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SISTEMA ATS - CORE MODELS                             │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   hh_clients    │     │    hh_roles     │     │  hh_candidates  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ PK client_id    │◄────┤ PK role_id      │     │ PK candidate_id │
│    client_name  │     │ FK client_id    │     │    full_name    │
│    industry     │     │    role_title   │     │    email        │
│    created_at   │     │    location     │     │    phone        │
│    updated_at   │     │    status       │     │    linkedin_url │
└─────────────────┘     │    date_opened  │     │    created_at   │
                        └─────────────────┘     └────────┬────────┘
                                 ▲                       │
                                 │                       │
                                 │    ┌──────────────────┴──────────────────┐
                                 │    │        hh_applications              │
                                 │    │        (ENTIDAD CENTRAL)            │
                                 │    ├─────────────────────────────────────┤
                                 │    │ PK application_id                   │
                                 └────┤ FK role_id                          │
                                      │ FK candidate_id ◄───────────────────┘
                                      │    stage                            │
                                      │    hired                            │
                                      │    overall_score                    │
                                      │    decision_date                    │
                                      │    created_at                       │
                                      └──────────────┬──────────────────────┘
                                                     │
         ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
         │                                           │                                           │
         ▼                                           ▼                                           ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  hh_interviews  │     │ hh_assessments  │     │   hh_flags      │     │  hh_documents   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ PK interview_id │     │ PK assessment_id│     │ PK flag_id      │     │ PK document_id  │
│ FK application_id│    │ FK application_id│    │ FK application_id│    │ FK application_id│
│    interview_date│    │    assessment_type│   │    category     │     │ FK role_id      │
│    interviewer   │     │    assessment_date│  │    severity     │     │ FK candidate_id │
│    summary_text  │     │    sincerity_score│  │    evidence     │     │    doc_type     │
│    created_at    │     │    created_at     │   │    source       │     │    storage_uri  │
└─────────────────┘     └────────┬────────┘     │    created_at   │     │    sha256_hash  │
                                 │              └─────────────────┘     │    uploaded_at  │
                                 ▼                                        └────────┬────────┘
                        ┌─────────────────┐                                         │
                        │hh_assessment_scores                                       │
                        ├─────────────────┤                                         │
                        │ PK score_id     │                                         │
                        │ FK assessment_id│                                         │
                        │    dimension    │                                         │
                        │    value        │                                         │
                        │    unit         │                                         ▼
                        │    created_at   │                              ┌─────────────────┐
                        └─────────────────┘                              │ hh_cv_processing│
                                                                         ├─────────────────┤
                                                                         │ PK processing_id│
                                                                         │ FK candidate_id │
                                                                         │ FK document_id ◄┘
                                                                         │    processing_status
                              ┌──────────────────────────────────────────┤    extraction_method
                              │                                          │    raw_text     │
                              ▼                                          │    extracted_json
                     ┌─────────────────┐                                 │    confidence_score
                     │ hh_cv_versions  │                                 │    processed_at
                     ├─────────────────┤                                 │    error_message
                     │ PK version_id   │                                 │    created_at   │
                     │ FK processing_id│◄────────────────────────────────│    updated_at   │
                     │ FK candidate_id │                                 └────────┬────────┘
                     │    version_number                                  │
                     │    version_status                                  ▼
                     │    previous_version_id                    ┌─────────────────┐
                     │    changes_summary                          │hh_cv_processing_logs
                     │    created_at                               ├─────────────────┤
                     └─────────────────┘                           │ PK log_id       │
                                                                    │ FK processing_id│◄┘
                                                                    │    log_level    │
                                                                    │    processing_stage
                                                                    │    step_order   │
                                                                    │    message      │
                                                                    │    duration_ms  │
                                                                    │    created_at   │
                                                                    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TABLAS AUXILIARES                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  hh_audit_log   │     │   users         │     │ communications  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ PK audit_id     │     │ PK id           │     │ PK id           │
│    entity_type  │     │    email        │     │ FK candidate_id │
│    entity_id    │     │    full_name    │     │ FK application_id│
│    action       │     │    role         │     │    channel      │
│    changed_by   │     │    status       │     │    direction    │
│    changed_at   │     │    created_at   │     │    status       │
│    diff_json    │     └─────────────────┘     │    sent_at      │
└─────────────────┘                             └─────────────────┘
```

---

## Tablas del Sistema

### 1. hh_clients (Clientes)

Almacena información de las empresas clientes que contratan servicios de headhunting.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| client_id | UUID | NO | PK - Identificador único |
| client_name | TEXT | NO | Nombre de la empresa |
| industry | TEXT | SÍ | Industria/sector |
| created_at | TIMESTAMP | NO | Fecha de creación |
| updated_at | TIMESTAMP | NO | Fecha de última actualización |

**Índices:**
- `idx_hh_clients_name` en `client_name`

---

### 2. hh_roles (Vacantes/Cargos)

Representa las vacantes o posiciones que los clientes necesitan cubrir.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| role_id | UUID | NO | PK - Identificador único |
| client_id | UUID | NO | FK → hh_clients |
| role_title | TEXT | NO | Título del cargo |
| location | TEXT | SÍ | Ubicación geográfica |
| seniority | TEXT | SÍ | Nivel de seniority |
| status | ENUM | NO | Estado: open, hold, closed |
| date_opened | DATE | SÍ | Fecha de apertura |
| date_closed | DATE | SÍ | Fecha de cierre |
| role_description_doc_id | UUID | SÍ | FK → hh_documents |

**Índices:**
- `idx_hh_roles_client`, `idx_hh_roles_status`, `idx_hh_roles_title`
- `idx_hh_roles_status_opened` compuesto (status, date_opened)

---

### 3. hh_candidates (Candidatos)

Información básica de los candidatos al proceso de selección.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| candidate_id | UUID | NO | PK - Identificador único |
| full_name | TEXT | NO | Nombre completo |
| national_id | TEXT | SÍ | Documento de identidad |
| email | TEXT | SÍ | Correo electrónico |
| phone | TEXT | SÍ | Teléfono de contacto |
| location | TEXT | SÍ | Ubicación |
| linkedin_url | TEXT | SÍ | Perfil de LinkedIn |

**Índices:**
- `idx_hh_candidates_email`, `idx_hh_candidates_national_id`
- `idx_hh_candidates_name`, `idx_hh_candidates_created`

---

### 4. hh_applications (Aplicaciones) - **ENTIDAD CENTRAL**

Conecta candidatos con vacantes. Es la entidad central del sistema.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| application_id | UUID | NO | PK - Identificador único |
| candidate_id | UUID | NO | FK → hh_candidates |
| role_id | UUID | NO | FK → hh_roles |
| stage | ENUM | NO | Etapa del pipeline |
| hired | BOOLEAN | NO | ¿Fue contratado? |
| decision_date | DATE | SÍ | Fecha de decisión |
| overall_score | NUMERIC(5,2) | SÍ | Puntuación global 0-100 |
| notes | TEXT | SÍ | Notas del consultor |
| discard_reason | TEXT | SÍ | Razón de descarte |
| initial_contact_date | TIMESTAMP | SÍ | Fecha de contacto inicial |
| candidate_response_date | TIMESTAMP | SÍ | Fecha de respuesta |

**Índices:**
- `idx_hh_applications_candidate`, `idx_hh_applications_role`, `idx_hh_applications_stage`
- `idx_hh_applications_hired`, `idx_hh_applications_score`
- Unique: `uix_hh_applications_candidate_role` (candidate_id, role_id)

---

### 5. hh_documents (Documentos)

Referencia a archivos PDF/DOCX subidos al sistema.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| document_id | UUID | NO | PK - Identificador único |
| application_id | UUID | SÍ | FK → hh_applications |
| role_id | UUID | SÍ | FK → hh_roles |
| candidate_id | UUID | SÍ | FK → hh_candidates |
| doc_type | ENUM | NO | Tipo: cv, interview, assessment |
| original_filename | TEXT | NO | Nombre original del archivo |
| storage_uri | TEXT | NO | URI de almacenamiento |
| sha256_hash | TEXT | NO | Hash SHA256 para deduplicación |
| uploaded_by | TEXT | SÍ | Usuario que subió el archivo |
| uploaded_at | TIMESTAMP | NO | Fecha de subida |

**Índices:**
- `idx_hh_docs_application`, `idx_hh_docs_hash`, `idx_hh_docs_type`
- Unique: `uix_hh_documents_hash` en `sha256_hash`

---

### 6. hh_interviews (Entrevistas)

Registro de entrevistas realizadas a los candidatos.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| interview_id | UUID | NO | PK |
| application_id | UUID | NO | FK → hh_applications |
| interview_date | TIMESTAMP | SÍ | Fecha y hora de la entrevista |
| interviewer | TEXT | SÍ | Nombre del entrevistador |
| summary_text | TEXT | SÍ | Resumen de la entrevista |
| raw_doc_id | UUID | SÍ | FK → hh_documents (notas) |

**Índices:**
- `idx_hh_interviews_application`, `idx_hh_interviews_date`

---

### 7. hh_assessments (Evaluaciones Psicométricas)

Evaluaciones psicométricas realizadas a los candidatos.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| assessment_id | UUID | NO | PK |
| application_id | UUID | NO | FK → hh_applications |
| assessment_type | ENUM | NO | Tipo de evaluación |
| assessment_date | DATE | SÍ | Fecha de evaluación |
| sincerity_score | NUMERIC(5,2) | SÍ | Score de sinceridad 0-100 |
| raw_pdf_id | UUID | SÍ | FK → hh_documents |

**Tipos de evaluación:**
- `factor_oscuro`: Factor Oscuro
- `inteligencia_ejecutiva`: Inteligencia Ejecutiva
- `kompedisc`: KOMPEDISC
- `other`: Otros

**Índices:**
- `idx_hh_assessments_application`, `idx_hh_assessments_type`

---

### 8. hh_assessment_scores (Scores Dinámicos)

Almacena las dimensiones evaluadas de forma dinámica (filas, no columnas).

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| score_id | UUID | NO | PK |
| assessment_id | UUID | NO | FK → hh_assessments |
| dimension | TEXT | NO | Nombre de la dimensión |
| value | NUMERIC(5,2) | NO | Valor 0-100 |
| unit | TEXT | NO | Unidad (default: 'score') |
| source_page | INTEGER | SÍ | Página fuente en el PDF |
| created_at | TIMESTAMP | NO | Fecha de creación |

**Índices:**
- `idx_hh_scores_assessment`, `idx_hh_scores_dimension`
- `idx_hh_scores_assessment_dimension` compuesto

---

### 9. hh_flags (Riesgos y Alertas)

Flags de riesgo detectados durante el proceso.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| flag_id | UUID | NO | PK |
| application_id | UUID | NO | FK → hh_applications |
| category | TEXT | NO | Categoría del riesgo |
| severity | ENUM | NO | low, medium, high |
| evidence | TEXT | SÍ | Evidencia del riesgo |
| source | ENUM | NO | interview, assessment, cv |
| source_doc_id | UUID | SÍ | FK → hh_documents |
| created_at | TIMESTAMP | NO | Fecha de detección |

**Índices:**
- `idx_hh_flags_application`, `idx_hh_flags_severity`, `idx_hh_flags_category`

---

### 10. hh_cv_processing (Procesamiento de CVs) ⭐ NUEVO

Almacena el resultado del procesamiento de CVs con extracción de texto y datos estructurados.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| processing_id | UUID | NO | PK |
| candidate_id | UUID | NO | FK → hh_candidates |
| document_id | UUID | SÍ | FK → hh_documents |
| processing_status | ENUM | NO | pending, processing, completed, failed, partial |
| extraction_method | ENUM | SÍ | pdf_text, ocr, ai_extraction, hybrid, manual |
| raw_text | TEXT | SÍ | Texto plano extraído |
| extracted_json | JSONB | SÍ | Datos estructurados extraídos |
| confidence_score | NUMERIC(5,2) | SÍ | Confianza 0-100 |
| extraction_duration_ms | INTEGER | SÍ | Tiempo de procesamiento (ms) |
| pages_processed | INTEGER | SÍ | Número de páginas |
| file_size_bytes | INTEGER | SÍ | Tamaño del archivo |
| extracted_name | TEXT | SÍ | Nombre extraído del CV |
| extracted_email | TEXT | SÍ | Email extraído del CV |
| extracted_phone | TEXT | SÍ | Teléfono extraído |
| extracted_title | TEXT | SÍ | Cargo/título profesional |
| extracted_location | TEXT | SÍ | Ubicación extraída |
| years_experience | INTEGER | SÍ | Años de experiencia estimados |
| processed_by | TEXT | SÍ | Usuario/sistema que procesó |
| processed_at | TIMESTAMP | SÍ | Fecha de procesamiento |
| error_message | TEXT | SÍ | Mensaje de error |
| error_details | JSONB | SÍ | Detalles técnicos del error |
| created_at | TIMESTAMP | NO | Fecha de creación del registro |
| updated_at | TIMESTAMP | NO | Fecha de actualización |

**Índices recomendados:**
```sql
CREATE INDEX idx_hh_cv_processing_candidate ON hh_cv_processing(candidate_id);
CREATE INDEX idx_hh_cv_processing_document ON hh_cv_processing(document_id);
CREATE INDEX idx_hh_cv_processing_status ON hh_cv_processing(processing_status);
CREATE INDEX idx_hh_cv_processing_method ON hh_cv_processing(extraction_method);
CREATE INDEX idx_hh_cv_processing_created ON hh_cv_processing(created_at);
CREATE INDEX idx_hh_cv_processing_score ON hh_cv_processing(confidence_score);
CREATE INDEX idx_hh_cv_processing_extracted_email ON hh_cv_processing(extracted_email) 
    WHERE extracted_email IS NOT NULL;
```

---

### 11. hh_cv_versions (Versiones de CV) ⭐ NUEVO

Histórico de versiones de CV procesados para un candidato.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| version_id | UUID | NO | PK |
| processing_id | UUID | NO | FK → hh_cv_processing |
| candidate_id | UUID | NO | FK → hh_candidates |
| version_number | INTEGER | NO | Número secuencial (1, 2, 3...) |
| version_status | ENUM | NO | active, archived, superceded |
| previous_version_id | UUID | SÍ | FK → hh_cv_versions (auto-referencia) |
| version_raw_text | TEXT | SÍ | Texto de esta versión |
| version_extracted_json | JSONB | SÍ | JSON de esta versión |
| changes_summary | TEXT | SÍ | Resumen de cambios |
| changes_json | JSONB | SÍ | Diff estructurado |
| created_by | TEXT | SÍ | Usuario que creó la versión |
| created_at | TIMESTAMP | NO | Fecha de creación |
| archived_at | TIMESTAMP | SÍ | Fecha de archivado |
| archive_reason | TEXT | SÍ | Razón de archivado |

**Índices recomendados:**
```sql
CREATE INDEX idx_hh_cv_versions_processing ON hh_cv_versions(processing_id);
CREATE INDEX idx_hh_cv_versions_candidate ON hh_cv_versions(candidate_id);
CREATE INDEX idx_hh_cv_versions_status ON hh_cv_versions(version_status);
CREATE INDEX idx_hh_cv_versions_number ON hh_cv_versions(candidate_id, version_number);
CREATE UNIQUE INDEX idx_hh_cv_versions_active ON hh_cv_versions(candidate_id, version_number) 
    WHERE version_status = 'active';
```

---

### 12. hh_cv_processing_logs (Logs de Procesamiento) ⭐ NUEVO

Logs detallados del pipeline de procesamiento de CVs.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| log_id | UUID | NO | PK |
| processing_id | UUID | NO | FK → hh_cv_processing |
| log_level | TEXT | NO | DEBUG, INFO, WARNING, ERROR |
| processing_stage | TEXT | NO | upload, extraction, parsing, validation |
| step_order | INTEGER | NO | Orden secuencial |
| message | TEXT | NO | Mensaje del log |
| details | JSONB | SÍ | Datos adicionales |
| duration_ms | INTEGER | SÍ | Duración del paso |
| memory_mb | INTEGER | SÍ | Uso de memoria aproximado |
| created_at | TIMESTAMP | NO | Fecha del log |

**Índices recomendados:**
```sql
CREATE INDEX idx_hh_cv_logs_processing ON hh_cv_processing_logs(processing_id);
CREATE INDEX idx_hh_cv_logs_level ON hh_cv_processing_logs(log_level);
CREATE INDEX idx_hh_cv_logs_stage ON hh_cv_processing_logs(processing_stage);
CREATE INDEX idx_hh_cv_logs_created ON hh_cv_processing_logs(created_at);
CREATE INDEX idx_hh_cv_logs_step ON hh_cv_processing_logs(processing_id, step_order);
```

---

### 13. hh_audit_log (Auditoría)

Registro de auditoría para trazabilidad completa.

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| audit_id | UUID | NO | PK |
| entity_type | TEXT | NO | Tipo de entidad |
| entity_id | UUID | NO | ID de la entidad |
| action | ENUM | NO | create, update, delete |
| changed_by | TEXT | SÍ | Usuario que realizó el cambio |
| changed_at | TIMESTAMP | NO | Fecha del cambio |
| diff_json | JSONB | SÍ | Diferencias en formato JSON |

**Índices:**
- `idx_hh_audit_entity` compuesto (entity_type, entity_id)
- `idx_hh_audit_changed_at`

---

## Relaciones entre Tablas

```
hh_clients (1) ───< (N) hh_roles
                        │
                        ▼
hh_candidates (1) ───< (N) hh_applications (N) >─── (1) hh_roles
         │                    │
         │                    ├──< (N) hh_interviews
         │                    ├──< (N) hh_assessments (1) >───< (N) hh_assessment_scores
         │                    ├──< (N) hh_flags
         │                    └──< (N) hh_documents
         │
         ├──< (N) hh_documents
         │
         └──< (N) hh_cv_processing (1) >───< (N) hh_cv_versions
                    │
                    └──< (N) hh_cv_processing_logs
```

**Cardinalidades:**
- `1:N` = Uno a Muchos
- `N:M` = Implementado mediante tabla intermedia (no aplica en este modelo)
- `(1)` = Lado "uno" de la relación
- `<` = Dirección de la FK

---

## Optimizaciones y Recomendaciones de Performance

### 1. Índices GIN para JSONB

Para búsquedas eficientes dentro de los campos JSONB:

```sql
-- Índice GIN para búsquedas en extracted_json
CREATE INDEX idx_hh_cv_processing_extracted_json_gin 
ON hh_cv_processing USING GIN (extracted_json);

-- Índice GIN para búsquedas en error_details
CREATE INDEX idx_hh_cv_processing_error_details_gin 
ON hh_cv_processing USING GIN (error_details);
```

### 2. Índices Parciales

Mejoran performance filtrando solo registros activos:

```sql
-- Solo versiones activas
CREATE UNIQUE INDEX idx_hh_cv_versions_active_unique 
ON hh_cv_versions(candidate_id, version_number) 
WHERE version_status = 'active';

-- Solo procesamientos completados exitosamente
CREATE INDEX idx_hh_cv_processing_completed 
ON hh_cv_processing(processed_at) 
WHERE processing_status = 'completed';
```

### 3. Índices para Full-Text Search

Para búsquedas de texto en CVs:

```sql
-- Crear columna de búsqueda
ALTER TABLE hh_cv_processing 
ADD COLUMN search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('spanish', raw_text)) STORED;

-- Crear índice GIN
CREATE INDEX idx_hh_cv_processing_search 
ON hh_cv_processing USING GIN (search_vector);
```

### 4. Particionamiento (para tablas grandes)

Para tablas que crecerán mucho (logs):

```sql
-- Particionar hh_cv_processing_logs por mes
CREATE TABLE hh_cv_processing_logs (
    LIKE hh_cv_processing_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Crear particiones mensuales
CREATE TABLE hh_cv_processing_logs_2026_02 
PARTITION OF hh_cv_processing_logs
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

### 5. Vistas Materializadas

Para reportes y dashboards:

```sql
-- Vista materializada de candidatos con último CV procesado
CREATE MATERIALIZED VIEW mv_candidates_cv_summary AS
SELECT 
    c.candidate_id,
    c.full_name,
    c.email,
    cvp.processing_id as last_cv_processing_id,
    cvp.processed_at as last_cv_processed_at,
    cvp.extraction_method as last_cv_method,
    cvp.confidence_score as last_cv_confidence,
    cvp.years_experience,
    cvp.extracted_title
FROM hh_candidates c
LEFT JOIN LATERAL (
    SELECT * FROM hh_cv_processing
    WHERE candidate_id = c.candidate_id
    AND processing_status = 'completed'
    ORDER BY processed_at DESC
    LIMIT 1
) cvp ON true;

-- Índice en la vista materializada
CREATE UNIQUE INDEX idx_mv_candidates_cv_summary_id 
ON mv_candidates_cv_summary(candidate_id);

-- Refrescar vista
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_candidates_cv_summary;
```

---

## Estrategia de Retención de Datos

### Políticas de Retención

| Tabla | Retención | Acción |
|-------|-----------|--------|
| hh_cv_processing_logs | 90 días | Archivar/eliminar logs antiguos |
| hh_cv_versions | 2 años | Archivar versiones antiguas |
| hh_cv_processing (failed) | 30 días | Eliminar registros fallidos |
| hh_audit_log | 1 año | Archivar en storage frío |

### Script de limpieza (ejemplo):

```sql
-- Archivar logs antiguos
INSERT INTO hh_cv_processing_logs_archive 
SELECT * FROM hh_cv_processing_logs 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Eliminar logs archivados
DELETE FROM hh_cv_processing_logs 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Archivar versiones antiguas
UPDATE hh_cv_versions 
SET version_status = 'archived', archived_at = NOW()
WHERE created_at < NOW() - INTERVAL '2 years' 
AND version_status = 'superceded';
```

---

## Migración de Datos

### Flujo de migración desde sistema legacy:

1. **Backup completo** de base de datos actual
2. **Crear nuevas tablas** usando migración Alembic
3. **Migrar datos existentes:**
   - Documentos existentes → hh_documents
   - Datos de CV parseados → hh_cv_processing
4. **Validar integridad** de datos migrados
5. **Crear índices** adicionales post-migración

---

## Seguridad y Acceso

### Políticas de Row Level Security (RLS)

```sql
-- Habilitar RLS en tablas sensibles
ALTER TABLE hh_cv_processing ENABLE ROW LEVEL SECURITY;

-- Política: consultores solo ven CVs de sus candidatos asignados
CREATE POLICY cv_processing_consultant_policy ON hh_cv_processing
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM hh_applications a
        JOIN hh_candidates c ON a.candidate_id = c.candidate_id
        WHERE a.application_id = hh_cv_processing.application_id
        AND a.assigned_consultant_id = current_user_id()
    )
);
```

---

## Glosario

| Término | Definición |
|---------|------------|
| **ATS** | Applicant Tracking System - Sistema de seguimiento de candidatos |
| **JSONB** | Tipo de dato PostgreSQL para JSON binario, permite índices y búsquedas |
| **FK** | Foreign Key - Clave foránea |
| **PK** | Primary Key - Clave primaria |
| **UUID** | Universal Unique Identifier - Identificador único universal |
| **ENUM** | Enumeración - Tipo de dato con valores predefinidos |
| **GIN** | Generalized Inverted Index - Índice para búsquedas de texto completo |
| **OCR** | Optical Character Recognition - Reconocimiento óptico de caracteres |

---

## Changelog

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2026-02-17 | 2.0 | Agregadas tablas hh_cv_processing, hh_cv_versions, hh_cv_processing_logs |
| 2026-02-16 | 1.5 | Modelo Core ATS con applications como entidad central |
| 2026-02-11 | 1.0 | Migración inicial del sistema |

---

## Contacto

Para consultas sobre el esquema de base de datos, contactar al equipo de Data Architecture.
