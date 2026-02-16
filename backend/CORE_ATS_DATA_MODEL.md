# Core ATS Data Model - Documentación

## Resumen

Modelo de datos completo implementado para el sistema ATS (Applicant Tracking System) siguiendo EXACTAMENTE el diseño especificado. La tabla `applications` es la **ENTIDAD CENTRAL** del sistema.

---

## Modelo de Datos

### 1. CANDIDATES (`candidates`)
Almacena la información de los candidatos.

**NOTA CRÍTICA:** Los scores NUNCA se guardan en esta tabla. Los scores van en `assessment_scores` vía `assessments → applications`.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `candidate_id` | UUID | PK |
| `full_name` | TEXT | NOT NULL |
| `national_id` | TEXT | UNIQUE, NULLABLE |
| `email` | TEXT | NULLABLE |
| `phone` | TEXT | NULLABLE |
| `location` | TEXT | NULLABLE |
| `linkedin_url` | TEXT | NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |
| `updated_at` | TIMESTAMP | NOT NULL |

**Índices:**
- `idx_candidates_email`
- `idx_candidates_national_id`
- `idx_candidates_name_search`
- `idx_candidates_created_at`

---

### 2. CLIENTS (`clients`)
Clientes/empresas que publican vacantes.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `client_id` | UUID | PK |
| `client_name` | TEXT | NOT NULL |
| `industry` | TEXT | NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |
| `updated_at` | TIMESTAMP | NOT NULL |

---

### 3. ROLES (`roles`) - Vacantes
Vacantes disponibles.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `role_id` | UUID | PK |
| `client_id` | UUID | FK → clients, NOT NULL |
| `role_title` | TEXT | NOT NULL |
| `location` | TEXT | NULLABLE |
| `seniority` | TEXT | NULLABLE |
| `status` | ENUM('open', 'hold', 'closed') | DEFAULT 'open' |
| `date_opened` | DATE | NULLABLE |
| `date_closed` | DATE | NULLABLE |
| `role_description_doc_id` | UUID | FK → documents, NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |
| `updated_at` | TIMESTAMP | NOT NULL |

**Índices:**
- `idx_roles_client_id`
- `idx_roles_status`
- `idx_roles_date_opened`
- `idx_roles_location`
- `idx_roles_seniority`
- `idx_roles_status_opened`

---

### 4. APPLICATIONS (`applications`) - **ENTIDAD CENTRAL**
Conexión Candidato ↔ Vacante. Toda la información del pipeline se conecta aquí.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `application_id` | UUID | PK |
| `candidate_id` | UUID | FK → candidates, NOT NULL |
| `role_id` | UUID | FK → roles, NOT NULL |
| `stage` | ENUM('sourcing', 'shortlist', 'terna', 'interview', 'offer', 'hired', 'rejected') | NOT NULL |
| `hired` | BOOLEAN | DEFAULT false |
| `decision_date` | DATE | NULLABLE |
| `overall_score` | NUMERIC(5,2) | NULLABLE (0-100) |
| `notes` | TEXT | NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |
| `updated_at` | TIMESTAMP | NOT NULL |

**Constraints:**
- UNIQUE(candidate_id, role_id) - Un candidato solo aplica una vez a cada vacante

**Índices:**
- `idx_applications_candidate_id`
- `idx_applications_role_id`
- `idx_applications_stage`
- `idx_applications_hired`
- `idx_applications_role_stage`
- `idx_applications_candidate_hired`
- `idx_applications_decision_date`
- `idx_applications_overall_score`

---

### 5. DOCUMENTS (`documents`) - Evidencia RAW
Documentos/evidencia del proceso. Puede estar asociado a application, role, o candidate.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `document_id` | UUID | PK |
| `application_id` | UUID | FK → applications, NULLABLE |
| `role_id` | UUID | FK → roles, NULLABLE |
| `candidate_id` | UUID | FK → candidates, NULLABLE |
| `doc_type` | ENUM('cv', 'interview', 'assessment', 'role_profile', 'other') | NOT NULL |
| `original_filename` | TEXT | NOT NULL |
| `storage_uri` | TEXT | NOT NULL |
| `sha256_hash` | TEXT | NULLABLE |
| `uploaded_by` | TEXT | NULLABLE |
| `uploaded_at` | TIMESTAMP | NOT NULL |

**Índices:**
- `idx_documents_application_id`
- `idx_documents_role_id`
- `idx_documents_candidate_id`
- `idx_documents_doc_type`
- `idx_documents_uploaded_at`
- `idx_documents_sha256`

---

### 6. INTERVIEWS (`interviews`)
Entrevistas realizadas a candidatos.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `interview_id` | UUID | PK |
| `application_id` | UUID | FK → applications, NOT NULL |
| `interview_date` | TIMESTAMP | NULLABLE |
| `interviewer` | TEXT | NULLABLE |
| `summary_text` | TEXT | NULLABLE |
| `raw_doc_id` | UUID | FK → documents, NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |
| `updated_at` | TIMESTAMP | NOT NULL |

---

### 7. ASSESSMENTS (`assessments`)
Evaluaciones psicométricas aplicadas.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `assessment_id` | UUID | PK |
| `application_id` | UUID | FK → applications, NOT NULL |
| `assessment_type` | ENUM('factor_oscuro', 'inteligencia_ejecutiva', 'kompedisc', 'other') | NOT NULL |
| `assessment_date` | DATE | NULLABLE |
| `sincerity_score` | NUMERIC(5,2) | NULLABLE (0-100) |
| `raw_pdf_id` | UUID | FK → documents, NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |
| `updated_at` | TIMESTAMP | NOT NULL |

**Índices:**
- `idx_assessments_application_id`
- `idx_assessments_type`
- `idx_assessments_date`
- `idx_assessments_app_type`

---

### 8. ASSESSMENT_SCORES (`assessment_scores`) - **SCORES DINÁMICOS**
**NO HAY COLUMNAS FIJAS** - Cada dimensión es una fila. Esto permite soportar cualquier tipo de evaluación sin cambiar el schema.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `score_id` | UUID | PK |
| `assessment_id` | UUID | FK → assessments, NOT NULL |
| `dimension` | TEXT | NOT NULL |
| `value` | NUMERIC(5,2) | NOT NULL, CHECK(0-100) |
| `unit` | TEXT | DEFAULT 'score' |
| `source_page` | INT | NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |

**Check Constraint:** `value >= 0 AND value <= 100`

**Índices:**
- `idx_assessment_scores_assessment_id`
- `idx_assessment_scores_dimension`
- `idx_assessment_scores_assessment_dimension`

**Ejemplo de uso:**
```sql
-- Evaluación Factor Oscuro
INSERT INTO assessment_scores (assessment_id, dimension, value) VALUES
('uuid-assessment', 'narcisismo', 45.50),
('uuid-assessment', 'maquiavelismo', 30.00),
('uuid-assessment', 'psicopatía', 25.00);

-- Evaluación Inteligencia Ejecutiva
INSERT INTO assessment_scores (assessment_id, dimension, value) VALUES
('uuid-assessment', 'planificación', 85.00),
('uuid-assessment', 'organización', 90.00),
('uuid-assessment', 'decisión', 78.50);
```

---

### 9. FLAGS (`flags`) - Riesgos/Alertas
Flags/alertas de riesgo sobre candidatos.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `flag_id` | UUID | PK |
| `application_id` | UUID | FK → applications, NOT NULL |
| `category` | TEXT | NULLABLE |
| `severity` | ENUM('low', 'medium', 'high') | NOT NULL |
| `evidence` | TEXT | NULLABLE |
| `source` | ENUM('interview', 'assessment', 'cv') | NOT NULL |
| `source_doc_id` | UUID | FK → documents, NULLABLE |
| `created_at` | TIMESTAMP | NOT NULL |

**Índices:**
- `idx_flags_application_id`
- `idx_flags_severity`
- `idx_flags_category`
- `idx_flags_source`
- `idx_flags_app_severity`
- `idx_flags_created_at`

---

### 10. AUDIT_LOG (`audit_logs`) - Trazabilidad
Log de auditoría para trazabilidad completa.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| `audit_id` | UUID | PK |
| `entity_type` | TEXT | NOT NULL |
| `entity_id` | UUID | NOT NULL |
| `action` | ENUM('create', 'update', 'delete') | NOT NULL |
| `changed_by` | TEXT | NULLABLE |
| `changed_at` | TIMESTAMP | NOT NULL |
| `diff_json` | JSONB | NULLABLE |

**Índices:**
- `idx_audit_logs_entity` (entity_type, entity_id)
- `idx_audit_logs_action`
- `idx_audit_logs_changed_by`
- `idx_audit_logs_changed_at`
- `idx_audit_logs_entity_action`

---

## API REST Endpoints

### Candidates
```
POST   /api/v1/candidates
GET    /api/v1/candidates
GET    /api/v1/candidates/{id}
PATCH  /api/v1/candidates/{id}
GET    /api/v1/candidates/{id}/applications
```

### Clients
```
POST   /api/v1/clients
GET    /api/v1/clients
GET    /api/v1/clients/{id}
PATCH  /api/v1/clients/{id}
```

### Roles (Vacantes)
```
POST   /api/v1/roles
GET    /api/v1/roles
GET    /api/v1/roles/{id}
PATCH  /api/v1/roles/{id}
GET    /api/v1/roles/{id}/applications
GET    /api/v1/roles/{id}/terna  # Comparador de terna
```

### Applications (Entidad Central)
```
POST   /api/v1/applications
GET    /api/v1/applications
GET    /api/v1/applications/{id}
PATCH  /api/v1/applications/{id}/stage
PATCH  /api/v1/applications/{id}/decision
GET    /api/v1/applications/{id}/timeline
GET    /api/v1/applications/{id}/scores
GET    /api/v1/applications/{id}/flags
```

### Documents
```
POST   /api/v1/documents/upload
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/download
```

### Assessments
```
POST   /api/v1/assessments
GET    /api/v1/assessments/{id}
POST   /api/v1/assessments/{id}/scores  # Batch insert scores
GET    /api/v1/assessments/{id}/scores
```

### Reports
```
GET    /api/v1/reports/terna?role_id={id}&candidate_ids=[]
GET    /api/v1/reports/role-analytics/{role_id}
GET    /api/v1/reports/candidate-history/{candidate_id}
```

---

## Vistas SQL

### v_applications_summary
Resumen de aplicaciones con conteos de entrevistas, evaluaciones y flags.

### v_roles_summary
Resumen de vacantes con conteos de aplicaciones, contratados y rechazados.

### v_candidates_summary
Resumen de candidatos con conteos de aplicaciones y contrataciones.

---

## Archivos Creados

### Migraciones (Alembic)
- `migrations/versions/20260216_001_core_ats_data_model.py`

### Modelos SQLAlchemy
- `app/models/core_ats.py` - Todos los modelos

### Schemas Pydantic
- `app/schemas/core_ats.py` - Todos los schemas

### API REST
- `app/api/v1/candidates.py` - Endpoints de candidatos
- `app/api/v1/clients.py` - Endpoints de clientes
- `app/api/v1/roles.py` - Endpoints de vacantes
- `app/api/v1/applications.py` - Endpoints de aplicaciones (central)
- `app/api/v1/documents.py` - Endpoints de documentos
- `app/api/v1/assessments.py` - Endpoints de evaluaciones
- `app/api/v1/reports.py` - Endpoints de reportes
- `app/api/v1/__init__.py` - Router principal

### Tests
- `tests/test_core_ats.py` - Tests unitarios completos

---

## Notas de Arquitectura

1. **Applications es la entidad central** - Todo el pipeline de selección se conecta a través de esta tabla.

2. **Scores dinámicos** - La tabla `assessment_scores` usa un diseño EAV (Entity-Attribute-Value) que permite guardar cualquier dimensión sin modificar el schema.

3. **Integridad referencial** - Todas las FKs tienen `ON DELETE` configurado apropiadamente (CASCADE para entidades fuertes, SET NULL para documentos).

4. **Auditoría** - Todos los cambios importantes se registran en `audit_logs` con diff en formato JSONB.

5. **Triggers** - Las tablas con `updated_at` tienen triggers automáticos para mantener el timestamp actualizado.
