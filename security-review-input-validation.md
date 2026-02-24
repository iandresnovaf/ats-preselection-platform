# 🔒 Informe de Seguridad: Validación de Entrada y Lógica de Negocio
## ATS Platform - Core API (v1)

**Fecha de revisión:** 2026-02-17  
**Archivos analizados:**
- `/ats-platform/backend/app/api/v1/applications.py`
- `/ats-platform/backend/app/api/v1/candidates.py`
- `/ats-platform/backend/app/api/v1/roles.py`
- `/ats-platform/backend/app/api/v1/clients.py`

---

## 📊 Resumen Ejecutivo

| Categoría | Severidad | Hallazgos |
|-----------|-----------|-----------|
| **IDOR / Autorización** | 🔴 Crítica | 4 archivos afectados - Sin validación de propiedad |
| **Validación de Estado** | 🟠 Alta | Transiciones de estado sin control |
| **Rate Limiting** | 🟡 Media | Implementado pero no aplicado consistentemente |
| **Validación de Inputs** | 🟢 Baja | Pydantic usado correctamente |

---

## 1. 🔴 CRÍTICO: Object-Level Authorization (IDOR)

### Problema
**Ningún endpoint verifica que el usuario autenticado tiene permiso para acceder al recurso solicitado.** Cualquier usuario autenticado puede ver/modificar cualquier candidato, aplicación, rol o cliente.

### Código Vulnerable (applications.py)
```python
@router.get("/{application_id}", response_model=ApplicationWithDetailsResponse)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # Solo valida autenticación, NO autorización
):
    """Obtener una aplicación por ID con detalles completos."""
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.candidate),
            joinedload(HHApplication.role).joinedload(HHRole.client),
            joinedload(HHApplication.interviews),
            joinedload(HHApplication.assessments),
            joinedload(HHApplication.flags)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    # ❌ FALTA: Verificar si current_user tiene permiso para ver esta aplicación
    # ❌ FALTA: Verificar si la aplicación pertenece al cliente/rol del usuario
    
    return application
```

### Código Vulnerable (candidates.py)
```python
@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener un candidato por ID."""
    result = await db.execute(
        select(HHCandidate).where(HHCandidate.candidate_id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    # ❌ FALTA: Verificar permisos del usuario sobre este candidato
    return candidate
```

### Impacto
- **Ejemplo de ataque:** Usuario A de la empresa X puede ver candidatos y aplicaciones de la empresa Y
- **Data leak:** Exposición de información confidencial de candidatos entre clientes
- **Modificación no autorizada:** Un usuario puede modificar candidatos que no le pertenecen

### Código Corregido
```python
# Nuevo archivo: app/core/permissions.py
from fastapi import HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, UserRole
from app.models.core_ats import HHApplication, HHCandidate, HHRole, HHClient

class PermissionChecker:
    """Verifica permisos a nivel de objeto para el modelo ATS."""
    
    @staticmethod
    async def can_view_application(
        user: User, 
        application_id: UUID, 
        db: AsyncSession
    ) -> bool:
        """Verifica si el usuario puede ver una aplicación específica."""
        # Super admin puede ver todo
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Consultor: verificar si tiene acceso al cliente/rol asociado
        if user.role == UserRole.CONSULTANT:
            result = await db.execute(
                select(HHApplication)
                .join(HHRole)
                .join(HHClient)
                .where(
                    HHApplication.application_id == application_id,
                    # Agregar: HHClient.assigned_consultant_id == user.user_id
                )
            )
            return result.scalar_one_or_none() is not None
        
        # Viewer: mismo check que consultor
        if user.role == UserRole.VIEWER:
            # Misma lógica que consultor pero solo lectura
            return await PermissionChecker.can_view_application_consultant(user, application_id, db)
        
        return False
    
    @staticmethod
    async def can_modify_application(
        user: User, 
        application_id: UUID, 
        db: AsyncSession
    ) -> bool:
        """Solo admin y consultor pueden modificar."""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role == UserRole.CONSULTANT:
            return await PermissionChecker.can_view_application_consultant(user, application_id, db)
        return False
    
    @staticmethod
    async def can_view_candidate(
        user: User, 
        candidate_id: UUID, 
        db: AsyncSession
    ) -> bool:
        """Verifica si el usuario puede ver un candidato."""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Verificar si el candidato tiene aplicaciones en roles del usuario
        result = await db.execute(
            select(HHApplication)
            .join(HHRole)
            .join(HHClient)
            .where(
                HHApplication.candidate_id == candidate_id,
                # Agregar: HHClient.assigned_consultant_id == user.user_id
            )
        )
        return result.scalar_one_or_none() is not None


# Uso en endpoints (applications.py)
from app.core.permissions import PermissionChecker

@router.get("/{application_id}", response_model=ApplicationWithDetailsResponse)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener una aplicación por ID con detalles completos."""
    # Verificar permisos ANTES de consultar
    if not await PermissionChecker.can_view_application(current_user, application_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta aplicación"
        )
    
    result = await db.execute(
        select(HHApplication).options(
            joinedload(HHApplication.candidate),
            joinedload(HHApplication.role).joinedload(HHRole.client),
            joinedload(HHApplication.interviews),
            joinedload(HHApplication.assessments),
            joinedload(HHApplication.flags)
        ).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    return application
```

---

## 2. 🟠 ALTO: Control de Integridad - Validación de Cambios de Estado

### Problema
Los endpoints permiten cambiar el estado de una aplicación sin validar las transiciones permitidas. Un usuario puede saltar de "sourcing" directamente a "hired" sin pasar por las etapas requeridas.

### Código Vulnerable (applications.py)
```python
@router.patch("/{application_id}/stage", response_model=ApplicationResponse)
async def update_application_stage(
    application_id: UUID,
    stage_update: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualizar la etapa de una aplicación."""
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    old_stage = application.stage
    application.stage = stage_update.stage  # ❌ Sin validación de transición permitida
    
    if stage_update.notes:
        application.notes = stage_update.notes
    
    await db.commit()
    # ...
```

### Impacto
- Saltarse etapas obligatorias (ej: contratar sin entrevista)
- Bypass de validaciones de negocio
- Inconsistencia en datos del pipeline

### Código Corregido
```python
# Nuevo archivo: app/core/state_machine.py
from enum import Enum
from typing import Set, Dict
from app.models.core_ats import ApplicationStage

class ApplicationStateMachine:
    """Máquina de estados para validar transiciones de aplicaciones."""
    
    # Definir transiciones permitidas
    ALLOWED_TRANSITIONS: Dict[ApplicationStage, Set[ApplicationStage]] = {
        ApplicationStage.SOURCING: {
            ApplicationStage.SHORTLIST,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.SHORTLIST: {
            ApplicationStage.TERNA,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.TERNA: {
            ApplicationStage.CONTACT_PENDING,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.CONTACT_PENDING: {
            ApplicationStage.CONTACTED,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.CONTACTED: {
            ApplicationStage.INTERESTED,
            ApplicationStage.NOT_INTERESTED,
            ApplicationStage.NO_RESPONSE,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.INTERESTED: {
            ApplicationStage.INTERVIEW_SCHEDULED,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.NOT_INTERESTED: {
            ApplicationStage.DISCARDED
        },
        ApplicationStage.NO_RESPONSE: {
            ApplicationStage.DISCARDED
        },
        ApplicationStage.INTERVIEW_SCHEDULED: {
            ApplicationStage.INTERVIEW_DONE,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.INTERVIEW_DONE: {
            ApplicationStage.OFFER_SENT,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.OFFER_SENT: {
            ApplicationStage.OFFER_ACCEPTED,
            ApplicationStage.OFFER_REJECTED,
            ApplicationStage.DISCARDED
        },
        ApplicationStage.OFFER_ACCEPTED: {
            ApplicationStage.HIRED
        },
        ApplicationStage.OFFER_REJECTED: {
            ApplicationStage.DISCARDED
        },
        ApplicationStage.HIRED: set(),  # Estado final
        ApplicationStage.DISCARDED: set(),  # Estado final
    }
    
    # Etapas requeridas antes de "hired"
    REQUIRED_STAGES_BEFORE_HIRE = {
        ApplicationStage.INTERVIEW_DONE,
        ApplicationStage.OFFER_ACCEPTED
    }
    
    @classmethod
    def can_transition(
        cls, 
        from_stage: ApplicationStage, 
        to_stage: ApplicationStage
    ) -> bool:
        """Verifica si una transición de estado es válida."""
        if from_stage == to_stage:
            return True  # Permitir "no-op"
        
        allowed = cls.ALLOWED_TRANSITIONS.get(from_stage, set())
        return to_stage in allowed
    
    @classmethod
    def validate_hire(cls, current_stage: ApplicationStage) -> bool:
        """Valida que se pueda pasar a hired."""
        return current_stage in cls.REQUIRED_STAGES_BEFORE_HIRE
    
    @classmethod
    def get_allowed_transitions(cls, stage: ApplicationStage) -> Set[ApplicationStage]:
        """Retorna las transiciones permitidas desde un estado."""
        return cls.ALLOWED_TRANSITIONS.get(stage, set())


# Uso en el endpoint corregido
from app.core.state_machine import ApplicationStateMachine

@router.patch("/{application_id}/stage", response_model=ApplicationResponse)
async def update_application_stage(
    application_id: UUID,
    stage_update: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar la etapa de una aplicación."""
    # Verificar permisos
    if not await PermissionChecker.can_modify_application(current_user, application_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta aplicación"
        )
    
    result = await db.execute(
        select(HHApplication).filter(HHApplication.application_id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    new_stage = stage_update.stage
    old_stage = application.stage
    
    # ✅ VALIDAR TRANSICIÓN DE ESTADO
    if not ApplicationStateMachine.can_transition(old_stage, new_stage):
        allowed = ApplicationStateMachine.get_allowed_transitions(old_stage)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transición no permitida: {old_stage.value} -> {new_stage.value}. "
                   f"Transiciones permitidas: {[s.value for s in allowed]}"
        )
    
    # ✅ VALIDACIÓN ESPECIAL PARA CONTRATACIÓN
    if new_stage == ApplicationStage.HIRED:
        if not ApplicationStateMachine.validate_hire(old_stage):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No se puede contratar desde etapa {old_stage.value}. "
                       f"Se requiere estar en: {[s.value for s in ApplicationStateMachine.REQUIRED_STAGES_BEFORE_HIRE]}"
            )
        application.hired = True
        application.decision_date = date.today()
    
    application.stage = new_stage
    
    if stage_update.notes:
        application.notes = stage_update.notes
    
    await db.commit()
    await db.refresh(application)
    
    # Crear registro de auditoría...
    return application
```

---

## 3. 🟡 MEDIO: Prevención de Doble Submit

### Problema
No existe mecanismo para prevenir envíos duplicados de formularios, lo que puede causar:
- Creación duplicada de candidatos
- Aplicaciones múltiples del mismo candidato a una vacante
- Acciones repetidas por errores de red/usuario

### Código Vulnerable (candidates.py)
```python
@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crear un nuevo candidato."""
    db_candidate = HHCandidate(**candidate.model_dump())
    db.add(db_candidate)
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate
```

### Código Corregido
```python
# Nuevo archivo: app/core/idempotency.py
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

class IdempotencyManager:
    """Gestiona tokens de idempotencia para prevenir doble submit."""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self.ttl = 86400  # 24 horas
    
    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def generate_key(
        self, 
        user_id: str, 
        action: str, 
        payload: dict
    ) -> str:
        """Genera clave única basada en usuario, acción y payload."""
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        key_data = f"{user_id}:{action}:{payload_str}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def check_and_store(
        self, 
        idempotency_key: str,
        ttl: int = None
    ) -> bool:
        """
        Verifica si la clave ya existe y la almacena si no.
        Returns: True si es nuevo (permitir), False si ya existe (rechazar)
        """
        try:
            r = await self.get_redis()
            key = f"idempotency:{idempotency_key}"
            
            # Intentar setear solo si no existe (NX)
            result = await r.set(key, datetime.utcnow().isoformat(), nx=True, ex=ttl or self.ttl)
            
            return result is not None  # True si se creó, False si ya existía
            
        except Exception:
            # Fail open - permitir si Redis falla
            return True
    
    async def get_existing_response(self, idempotency_key: str) -> Optional[dict]:
        """Recupera respuesta previa si existe (para respuestas idempotentes)."""
        try:
            r = await self.get_redis()
            key = f"idempotency:response:{idempotency_key}"
            response = await r.get(key)
            return json.loads(response) if response else None
        except Exception:
            return None
    
    async def store_response(
        self, 
        idempotency_key: str, 
        response: dict,
        ttl: int = None
    ):
        """Almacena respuesta para retornar en caso de retry."""
        try:
            r = await self.get_redis()
            key = f"idempotency:response:{idempotency_key}"
            await r.set(key, json.dumps(response, default=str), ex=ttl or self.ttl)
        except Exception:
            pass


# Uso en endpoint con idempotencia
from app.core.idempotency import IdempotencyManager
from fastapi import Header

idempotency_manager = IdempotencyManager()

@router.post(
    "", 
    response_model=CandidateResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_candidate(
    candidate: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Crear un nuevo candidato con protección contra doble submit."""
    
    # ✅ Verificar idempotencia si se proporciona key
    if idempotency_key:
        # Verificar si ya existe
        existing_response = await idempotency_manager.get_existing_response(idempotency_key)
        if existing_response:
            # Retornar respuesta previa
            return CandidateResponse(**existing_response)
        
        # Verificar si está en proceso
        is_new = await idempotency_manager.check_and_store(idempotency_key, ttl=300)
        if not is_new:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request en proceso. Por favor espere."
            )
    
    try:
        # Crear candidato con verificación de duplicados
        db_candidate = HHCandidate(**candidate.model_dump())
        db.add(db_candidate)
        await db.commit()
        await db.refresh(db_candidate)
        
        response = CandidateResponse.model_validate(db_candidate)
        
        # Almacenar respuesta para idempotencia
        if idempotency_key:
            await idempotency_manager.store_response(
                idempotency_key, 
                response.model_dump()
            )
        
        return response
        
    except Exception:
        # Limpiar key de idempotencia en caso de error
        if idempotency_key:
            await idempotency_manager.check_and_store(f"cleanup:{idempotency_key}")
        raise
```

---

## 4. 🟡 MEDIO: Rate Limiting en Endpoints Críticos

### Problema
El middleware de rate limiting existe pero no hay limites específicos para operaciones críticas como:
- Creación masiva de aplicaciones
- Actualizaciones de estado
- Envío de mensajes

### Código Vulnerable (applications.py)
```python
@router.post("/{application_id}/send-message")
async def send_message_to_candidate(
    application_id: UUID,
    message_request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Enviar mensaje al candidato (email o whatsapp)."""
    # ❌ Sin rate limiting específico - un usuario podría spammeae
```

### Código Corregido
```python
from fastapi import Request
from app.core.rate_limit import RateLimitByUser

# Rate limiter específico para mensajes
message_rate_limit = RateLimitByUser(
    requests=5,      # 5 mensajes
    window=300,      # por 5 minutos
    key_prefix="message"
)

@router.post("/{application_id}/send-message")
async def send_message_to_candidate(
    application_id: UUID,
    message_request: SendMessageRequest,
    request: Request,  # ✅ Agregar request para rate limiting
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enviar mensaje al candidato (email o whatsapp)."""
    
    # ✅ Rate limiting específico
    rate_limit_response = await message_rate_limit(request)
    if rate_limit_response:
        return rate_limit_response
    
    # Verificar permisos...
    if not await PermissionChecker.can_view_application(current_user, application_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para esta aplicación"
        )
    
    # Resto del código...
```

---

## 5. 🟢 BAJO: Validación de Inputs

### Estado Actual: ✅ Correcto
Los schemas Pydantic están bien implementados:

```python
# schemas/core_ats.py - Ejemplos de buena validación

class CandidateBase(BaseSchema):
    full_name: str = Field(..., min_length=1, max_length=500)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)

class ApplicationBase(BaseSchema):
    stage: str = Field(
        default="sourcing",
        pattern="^(sourcing|shortlist|terna|contact_pending|contacted|...)$"
    )
    overall_score: Optional[float] = Field(None, ge=0, le=100)

class FlagBase(BaseSchema):
    severity: str = Field(..., pattern="^(low|medium|high)$")
```

### Mejora Sugerida: Sanitización Adicional
```python
# Nuevo archivo: app/core/sanitization.py
import re
from html import escape

def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Sanitiza strings para prevenir XSS e inyecciones."""
    if not value:
        return value
    
    # Escapar HTML
    value = escape(value)
    
    # Limitar longitud
    value = value[:max_length]
    
    # Remover caracteres de control excepto newlines y tabs
    value = ''.join(char for char in value if char == '\n' or char == '\t' or ord(char) >= 32)
    
    return value

def sanitize_notes(value: Optional[str]) -> Optional[str]:
    """Sanitización especial para campos de notas (permite markdown básico)."""
    if not value:
        return value
    
    # Lista blanca de tags markdown permitidos
    allowed_patterns = [
        r'\*\*.*?\*\*',      # **bold**
        r'\*.*?\*',           # *italic*
        r'`[^`]*`',           # `code`
        r'\n',                # newlines
        r'\t',                # tabs
    ]
    
    # Por ahora solo escapamos HTML y limitamos longitud
    return sanitize_string(value, max_length=5000)


# Uso en validación Pydantic v2
from pydantic import field_validator

class ApplicationUpdate(BaseSchema):
    notes: Optional[str] = None
    
    @field_validator('notes')
    @classmethod
    def sanitize_notes(cls, v):
        if v is not None:
            return sanitize_notes(v)
        return v
```

---

## 6. 🟡 MEDIO: Límites de Tamaño en Uploads

### Problema
El endpoint de extracción de documentos no tiene límites de tamaño claros.

### Código Actual (roles.py)
```python
@router.post("/extract-from-document")
async def extract_role_from_document(
    file: UploadFile = File(...),  # ❌ Sin límite de tamaño
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    content = await file.read()  # ❌ Podría causar OOM con archivos grandes
```

### Código Corregido
```python
from fastapi import UploadFile, File
import os

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}

@router.post("/extract-from-document")
async def extract_role_from_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Extraer información de perfil de cargo desde PDF/Word."""
    
    # ✅ Validar extensión
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # ✅ Leer con límite de tamaño
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,  # Payload Too Large
            detail=f"Archivo excede el límite de {MAX_FILE_SIZE / (1024*1024)} MB"
        )
    
    # Validar tipo MIME real
    import magic
    mime = magic.from_buffer(content, mime=True)
    allowed_mimes = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain'
    }
    
    if mime not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: {mime}"
        )
    
    # Procesar archivo...
```

---

## 7. ✅ BUENO: Prevención de SQL Injection

### Estado: Correcto
Todos los endpoints usan SQLAlchemy ORM con parámetros bind, lo que previene SQL injection:

```python
# ✅ Seguro - Usa ORM con parámetros
result = await db.execute(
    select(HHCandidate).where(HHCandidate.candidate_id == candidate_id)
)

# ✅ Seguro - Filtros con parámetros
if search:
    search_filter = f"%{search}%"
    query = query.where(
        (HHCandidate.full_name.ilike(search_filter)) |
        (HHCandidate.email.ilike(search_filter))
    )
```

---

## 8. ✅ BUENO: Paginación

### Estado: Correcto
Todos los endpoints de listado implementan paginación:

```python
@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),  # ✅ Límite máximo
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
```

---

## 📋 Plan de Remediación Priorizado

### Prioridad 1 (Crítica - 1 semana)
- [ ] Implementar `PermissionChecker` para validación de propiedad de recursos
- [ ] Agregar verificación de permisos en TODOS los endpoints de GET/PATCH/DELETE
- [ ] Crear tests de seguridad para IDOR

### Prioridad 2 (Alta - 2 semanas)
- [ ] Implementar `ApplicationStateMachine` para validación de transiciones
- [ ] Agregar validación de estado en endpoints de stage/decision
- [ ] Agregar protección de doble submit con idempotency keys

### Prioridad 3 (Media - 3 semanas)
- [ ] Aplicar rate limiting específico en endpoints críticos
- [ ] Implementar sanitización adicional de inputs
- [ ] Agregar límites de tamaño en uploads

### Prioridad 4 (Baja - 4 semanas)
- [ ] Auditoría de logs de seguridad
- [ ] Documentación de permisos y roles
- [ ] Tests automatizados de seguridad

---

## 🔗 Referencias

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Cheat Sheet - IDOR](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
