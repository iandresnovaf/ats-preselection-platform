# 📚 Core ATS - API Documentation

Documentación completa de la API REST del Core ATS.

---

## 📋 Información General

### Base URL

```
Desarrollo:  http://localhost:8000/api/v1
Producción:  https://api.ats-platform.com/api/v1
```

### Autenticación

Todas las APIs (excepto login) requieren un Bearer Token en el header:

```http
Authorization: Bearer <access_token>
```

Obtén el token mediante:
```http
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password"
}
```

### Headers Estándar

```http
Content-Type: application/json
Accept: application/json
X-Request-ID: <uuid>  # Opcional, para trazabilidad
```

### Formato de Respuesta

**Éxito (200-299):**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operación exitosa",
  "timestamp": "2026-02-11T14:13:00Z",
  "request_id": "uuid"
}
```

**Error (400-599):**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Datos inválidos",
    "details": {
      "field": "email",
      "issue": "Email inválido"
    }
  },
  "timestamp": "2026-02-11T14:13:00Z"
}
```

### Paginación

Los endpoints de listado soportan paginación:

```http
GET /api/v1/jobs?page=1&page_size=20
```

**Parámetros:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `page` | int | 1 | Número de página |
| `page_size` | int | 20 | Items por página (max 100) |

**Respuesta paginada:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": false
}
```

### Rate Limiting

- **Límite:** 100 requests/minuto por IP
- **Headers de respuesta:**
  ```http
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1644592800
  ```

---

## 🎯 Endpoints de Jobs

### Listar Ofertas

```http
GET /api/v1/jobs
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `status` | string | Filtrar por estado: `draft`, `active`, `closed`, `paused` |
| `search` | string | Buscar en título y descripción |
| `department` | string | Filtrar por departamento |
| `location` | string | Filtrar por ubicación |
| `assigned_to` | uuid | Filtrar por consultor asignado |
| `is_active` | bool | Filtrar por estado activo |
| `page` | int | Número de página |
| `page_size` | int | Items por página |

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Desarrollador Senior Python",
        "description": "Buscamos desarrollador con 5+ años de experiencia...",
        "department": "Ingeniería",
        "location": "Remoto",
        "seniority": "Senior",
        "sector": "Tecnología",
        "status": "active",
        "is_active": true,
        "assigned_consultant_id": "550e8400-e29b-41d4-a716-446655440001",
        "assigned_consultant": {
          "id": "550e8400-e29b-41d4-a716-446655440001",
          "full_name": "Ana García",
          "email": "ana@company.com"
        },
        "zoho_job_id": "ZJOB001",
        "created_at": "2026-02-01T10:00:00Z",
        "updated_at": "2026-02-11T08:00:00Z",
        "candidates_count": 15
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20,
    "pages": 3
  }
}
```

---

### Crear Oferta

```http
POST /api/v1/jobs
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Desarrollador Senior Python",
  "description": "Buscamos desarrollador con 5+ años de experiencia en Python...",
  "department": "Ingeniería",
  "location": "Remoto",
  "seniority": "Senior",
  "sector": "Tecnología",
  "assigned_consultant_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `title` | string | ✅ | Título del cargo (3-255 chars) |
| `description` | string | ✅ | Descripción completa del puesto |
| `department` | string | ❌ | Departamento/Área |
| `location` | string | ❌ | Ubicación del trabajo |
| `seniority` | string | ❌ | Nivel: Junior, Senior, Lead, etc. |
| `sector` | string | ❌ | Industria/Sector |
| `assigned_consultant_id` | uuid | ❌ | ID del consultor asignado |

**Respuesta (201):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "title": "Desarrollador Senior Python",
    "description": "Buscamos desarrollador con 5+ años de experiencia en Python...",
    "department": "Ingeniería",
    "location": "Remoto",
    "seniority": "Senior",
    "sector": "Tecnología",
    "status": "draft",
    "is_active": true,
    "assigned_consultant_id": "550e8400-e29b-41d4-a716-446655440001",
    "zoho_job_id": null,
    "created_at": "2026-02-11T14:13:00Z",
    "updated_at": "2026-02-11T14:13:00Z"
  },
  "message": "Oferta creada exitosamente"
}
```

**Errores:**
- `400` - Datos inválidos
- `404` - Consultor asignado no existe

---

### Obtener Oferta

```http
GET /api/v1/jobs/{id}
```

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "title": "Desarrollador Senior Python",
    "description": "Buscamos desarrollador con 5+ años de experiencia...",
    "department": "Ingeniería",
    "location": "Remoto",
    "seniority": "Senior",
    "sector": "Tecnología",
    "status": "active",
    "is_active": true,
    "assigned_consultant": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "full_name": "Ana García",
      "email": "ana@company.com"
    },
    "zoho_job_id": "ZJOB001",
    "created_at": "2026-02-01T10:00:00Z",
    "updated_at": "2026-02-11T08:00:00Z",
    "candidates": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "full_name": "Juan Pérez",
        "email": "juan@email.com",
        "status": "in_review",
        "latest_score": 85.5,
        "latest_decision": "PROCEED"
      }
    ],
    "candidates_count": 15
  }
}
```

---

### Actualizar Oferta

```http
PUT /api/v1/jobs/{id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Lead Developer Python",
  "status": "active",
  "assigned_consultant_id": "550e8400-e29b-41d4-a716-446655440004"
}
```

> Nota: Todos los campos son opcionales. Solo se actualizan los proporcionados.

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "title": "Lead Developer Python",
    "status": "active",
    ...
  },
  "message": "Oferta actualizada exitosamente"
}
```

---

### Eliminar Oferta

```http
DELETE /api/v1/jobs/{id}
```

**Respuesta (200):**
```json
{
  "success": true,
  "message": "Oferta eliminada exitosamente"
}
```

> Nota: Los candidatos asociados NO se eliminan, quedan sin `job_opening_id`.

---

### Obtener Candidatos de una Oferta

```http
GET /api/v1/jobs/{id}/candidates
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `status` | string | Filtrar por estado del candidato |
| `search` | string | Buscar en nombre/email |
| `page` | int | Página |
| `page_size` | int | Items por página |

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "full_name": "Juan Pérez",
        "email": "juan@email.com",
        "status": "in_review",
        "latest_score": 85.5,
        "latest_decision": "PROCEED",
        "created_at": "2026-02-10T15:30:00Z"
      }
    ],
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 👥 Endpoints de Candidates

### Listar Candidatos

```http
GET /api/v1/candidates
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `job_id` | uuid | Filtrar por oferta |
| `status` | string | `new`, `in_review`, `shortlisted`, `interview`, `offer`, `hired`, `discarded` |
| `search` | string | Buscar en nombre, email, teléfono |
| `has_evaluation` | bool | Filtrar por si tiene evaluación |
| `min_score` | float | Score mínimo (0-100) |
| `is_duplicate` | bool | Filtrar duplicados |
| `source` | string | `webhook`, `manual`, `import` |
| `page` | int | Página |
| `page_size` | int | Items por página |

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "email": "juan.perez@email.com",
        "phone": "+56912345678",
        "full_name": "Juan Pérez",
        "job_opening_id": "550e8400-e29b-41d4-a716-446655440002",
        "job_title": "Desarrollador Senior Python",
        "status": "in_review",
        "zoho_candidate_id": "ZCAND001",
        "is_duplicate": false,
        "source": "webhook",
        "created_at": "2026-02-10T15:30:00Z",
        "latest_score": 85.5,
        "latest_decision": "PROCEED"
      }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20
  }
}
```

---

### Crear Candidato

```http
POST /api/v1/candidates
Content-Type: application/json
```

**Request Body:**
```json
{
  "job_opening_id": "550e8400-e29b-41d4-a716-446655440002",
  "raw_data": {
    "nombre": "Juan Pérez",
    "email": "juan.perez@email.com",
    "telefono": "+56912345678",
    "cv_text": "Ingeniero con 5 años de experiencia en desarrollo Python...",
    "experiencia": [
      {
        "empresa": "Tech Corp",
        "cargo": "Senior Developer",
        "periodo": "2020-2024"
      }
    ],
    "educacion": [
      {
        "institucion": "Universidad de Chile",
        "titulo": "Ingeniero Civil Informático",
        "año": "2019"
      }
    ],
    "habilidades": ["Python", "FastAPI", "PostgreSQL", "Docker"]
  },
  "source": "manual"
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `job_opening_id` | uuid | ✅ | ID de la oferta asociada |
| `raw_data` | object | ✅ | Datos del CV en formato flexible |
| `source` | string | ❌ | Origen: `manual`, `webhook`, `import` (default: manual) |

**Respuesta (201):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "email": "juan.perez@email.com",
    "email_normalized": "juan.perez@email.com",
    "phone": "+56912345678",
    "phone_normalized": "56912345678",
    "full_name": "Juan Pérez",
    "job_opening_id": "550e8400-e29b-41d4-a716-446655440002",
    "status": "new",
    "is_duplicate": false,
    "source": "manual",
    "created_at": "2026-02-11T14:13:00Z",
    "evaluation_queued": true
  },
  "message": "Candidato creado exitosamente. Evaluación en proceso."
}
```

> Nota: Si se detecta un duplicado, se retornará `is_duplicate: true` y `duplicate_of_id` con el ID del candidato original.

---

### Obtener Candidato

```http
GET /api/v1/candidates/{id}
```

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "email": "juan.perez@email.com",
    "phone": "+56912345678",
    "full_name": "Juan Pérez",
    "job_opening_id": "550e8400-e29b-41d4-a716-446655440002",
    "job_opening": {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "title": "Desarrollador Senior Python"
    },
    "status": "in_review",
    "extracted_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "extracted_experience": [...],
    "extracted_education": [...],
    "raw_data": {...},
    "zoho_candidate_id": "ZCAND001",
    "is_duplicate": false,
    "duplicate_of_id": null,
    "source": "webhook",
    "created_at": "2026-02-10T15:30:00Z",
    "updated_at": "2026-02-11T10:00:00Z",
    "evaluations": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "score": 85.5,
        "decision": "PROCEED",
        "created_at": "2026-02-10T15:31:00Z"
      }
    ],
    "communications": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440006",
        "type": "email",
        "status": "sent",
        "subject": "Bienvenido al proceso",
        "sent_at": "2026-02-10T16:00:00Z"
      }
    ]
  }
}
```

---

### Actualizar Candidato

```http
PUT /api/v1/candidates/{id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "shortlisted",
  "email": "nuevo@email.com",
  "full_name": "Juan Pérez González"
}
```

**Campos actualizables:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | string | Nuevo estado del candidato |
| `email` | string | Nuevo email |
| `phone` | string | Nuevo teléfono |
| `full_name` | string | Nuevo nombre |

---

### Obtener Evaluaciones de un Candidato

```http
GET /api/v1/candidates/{id}/evaluations
```

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "score": 85.5,
        "decision": "PROCEED",
        "strengths": ["5+ años Python", "Experiencia en startups"],
        "gaps": ["No tiene AWS"],
        "red_flags": [],
        "created_at": "2026-02-10T15:31:00Z"
      }
    ],
    "total": 2
  }
}
```

---

## 🧠 Endpoints de Evaluations

### Listar Evaluaciones

```http
GET /api/v1/evaluations
```

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `candidate_id` | uuid | Filtrar por candidato |
| `job_id` | uuid | Filtrar por oferta |
| `decision` | string | `PROCEED`, `REVIEW`, `REJECT_HARD` |
| `min_score` | float | Score mínimo |
| `max_score` | float | Score máximo |
| `llm_provider` | string | `openai`, `anthropic` |

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "candidate_id": "550e8400-e29b-41d4-a716-446655440003",
        "candidate_name": "Juan Pérez",
        "job_title": "Desarrollador Senior Python",
        "score": 85.5,
        "decision": "PROCEED",
        "strengths": ["5+ años Python", "Experiencia en startups", "Liderazgo técnico"],
        "gaps": ["No tiene experiencia con AWS", "Inglés intermedio"],
        "red_flags": [],
        "evidence": "El candidato menciona 5 años de experiencia en Python...",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "prompt_version": "v1.0",
        "hard_filters_passed": true,
        "created_at": "2026-02-11T10:00:00Z",
        "evaluation_time_ms": 2500
      }
    ],
    "total": 45,
    "page": 1
  }
}
```

---

### Crear Evaluación (Manual)

```http
POST /api/v1/evaluations
Content-Type: application/json
```

**Request Body:**
```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440003",
  "prompt_override": null
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `candidate_id` | uuid | ✅ | ID del candidato a evaluar |
| `prompt_override` | string | ❌ | Prompt personalizado (opcional) |

**Respuesta (202):**
```json
{
  "success": true,
  "message": "Evaluación iniciada",
  "data": {
    "evaluation_id": "550e8400-e29b-41d4-a716-446655440007",
    "status": "processing",
    "estimated_time_seconds": 5
  }
}
```

> Nota: La evaluación es asíncrona. El resultado se obtiene mediante polling o webhook.

---

### Obtener Evaluación

```http
GET /api/v1/evaluations/{id}
```

**Respuesta (200):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440005",
    "candidate_id": "550e8400-e29b-41d4-a716-446655440003",
    "candidate": {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "full_name": "Juan Pérez",
      "email": "juan.perez@email.com"
    },
    "score": 85.5,
    "decision": "PROCEED",
    "strengths": ["5+ años Python", "Experiencia en startups"],
    "gaps": ["No tiene AWS"],
    "red_flags": [],
    "evidence": "El candidato menciona 5 años de experiencia...",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "prompt_version": "v1.0",
    "hard_filters_passed": true,
    "hard_filters_failed": [],
    "raw_llm_response": {...},
    "created_at": "2026-02-11T10:00:00Z",
    "evaluation_time_ms": 2500
  }
}
```

---

### Re-generar Evaluación

```http
POST /api/v1/evaluations/{id}/regenerate
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt_override": "Enfócate específicamente en experiencia con liderazgo técnico y arquitectura de sistemas. Ignora experiencia frontend."
}
```

**Respuesta (202):**
```json
{
  "success": true,
  "message": "Re-evaluación iniciada",
  "data": {
    "evaluation_id": "550e8400-e29b-41d4-a716-446655440008",
    "status": "processing"
  }
}
```

---

## 🔌 Webhooks

El sistema puede notificar eventos a URLs configuradas:

### Eventos Disponibles

| Evento | Descripción |
|--------|-------------|
| `candidate.created` | Nuevo candidato creado |
| `candidate.evaluation.completed` | Evaluación finalizada |
| `job.synced_to_zoho` | Job sincronizado con Zoho |
| `communication.sent` | Mensaje enviado |

### Formato del Webhook

```http
POST https://tu-servidor.com/webhook
Content-Type: application/json
X-Webhook-Signature: sha256=<signature>

{
  "event": "candidate.evaluation.completed",
  "timestamp": "2026-02-11T14:13:00Z",
  "data": {
    "candidate_id": "550e8400-e29b-41d4-a716-446655440003",
    "evaluation_id": "550e8400-e29b-41d4-a716-446655440005",
    "score": 85.5,
    "decision": "PROCEED"
  }
}
```

---

## 📊 Códigos de Error

| Código | HTTP | Descripción |
|--------|------|-------------|
| `VALIDATION_ERROR` | 400 | Datos de entrada inválidos |
| `UNAUTHORIZED` | 401 | Token inválido o expirado |
| `FORBIDDEN` | 403 | Sin permisos para esta acción |
| `NOT_FOUND` | 404 | Recurso no encontrado |
| `CONFLICT` | 409 | Conflicto (ej: duplicado) |
| `RATE_LIMITED` | 429 | Demasiadas requests |
| `INTERNAL_ERROR` | 500 | Error interno del servidor |

---

## 🧪 Ejemplos con cURL

### Login y obtener token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "password"
  }'
```

### Crear un Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Senior Developer",
    "description": "Looking for experienced developer...",
    "department": "Engineering",
    "location": "Remote"
  }'
```

### Listar candidatos con filtros
```bash
curl "http://localhost:8000/api/v1/candidates?job_id=<id>&status=in_review&min_score=80" \
  -H "Authorization: Bearer <token>"
```

---

**Versión API:** 1.0  
**Última actualización:** 2026-02-11  
**Contacto:** api-support@ats-platform.com
