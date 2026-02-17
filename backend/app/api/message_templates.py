"""API endpoints para Plantillas de Mensajes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models import User, MessageTemplate, TemplateVariable, MessageChannel
from app.schemas import (
    MessageTemplateCreate, MessageTemplateUpdate, MessageTemplateResponse,
    MessageTemplateListResponse, TemplatePreviewRequest, TemplatePreviewResponse,
    TemplateVariableCreate, TemplateVariableUpdate, TemplateVariableResponse,
    MessageChannel as MessageChannelEnum,
)
from app.services.template_renderer import get_template_renderer


router = APIRouter(prefix="/message-templates", tags=["Message Templates"])


# ============== TEMPLATE ENDPOINTS ==============

@router.post("", response_model=MessageTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: MessageTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear una nueva plantilla de mensaje."""
    # Verificar si ya existe una plantilla con el mismo nombre y canal
    result = await db.execute(
        select(MessageTemplate).where(
            and_(
                MessageTemplate.name == template_data.name,
                MessageTemplate.channel == template_data.channel
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una plantilla con el nombre '{template_data.name}' para el canal {template_data.channel}"
        )
    
    # Extraer variables del body y subject si no se proporcionaron
    if not template_data.variables:
        renderer = get_template_renderer()
        body_vars = renderer.extract_variables(template_data.body)
        subject_vars = renderer.extract_variables(template_data.subject or "")
        variables = list(set(body_vars + subject_vars))
    else:
        variables = template_data.variables
    
    # Crear plantilla
    template = MessageTemplate(
        name=template_data.name,
        description=template_data.description,
        channel=template_data.channel,
        subject=template_data.subject,
        body=template_data.body,
        variables=variables,
        is_active=template_data.is_active,
        is_default=False,
        created_by=current_user.id,
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    return template


@router.get("", response_model=MessageTemplateListResponse)
async def list_templates(
    channel: Optional[MessageChannelEnum] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar plantillas de mensajes con filtros opcionales."""
    # Construir query base
    query = select(MessageTemplate)
    
    # Aplicar filtros
    if channel:
        query = query.where(MessageTemplate.channel == channel)
    if is_active is not None:
        query = query.where(MessageTemplate.is_active == is_active)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            and_(
                MessageTemplate.name.ilike(search_filter),
                MessageTemplate.description.ilike(search_filter)
            )
        )
    
    # Contar total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Aplicar paginación
    query = query.order_by(MessageTemplate.name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size
    
    return MessageTemplateListResponse(
        items=list(templates),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
    )


@router.get("/variables", response_model=list[TemplateVariableResponse])
async def list_available_variables(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar variables disponibles globalmente para plantillas."""
    query = select(TemplateVariable).where(TemplateVariable.is_active == True)
    
    if category:
        query = query.where(TemplateVariable.category == category)
    
    query = query.order_by(TemplateVariable.category, TemplateVariable.name)
    result = await db.execute(query)
    variables = result.scalars().all()
    
    return list(variables)


@router.get("/{template_id}", response_model=MessageTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener una plantilla por ID."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.template_id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada"
        )
    
    return template


@router.patch("/{template_id}", response_model=MessageTemplateResponse)
async def update_template(
    template_id: UUID,
    template_data: MessageTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar una plantilla existente."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.template_id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada"
        )
    
    # No permitir modificar plantillas del sistema (is_default=True)
    if template.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pueden modificar las plantillas del sistema"
        )
    
    # Verificar conflicto de nombre si se está cambiando
    if template_data.name and template_data.name != template.name:
        channel = template_data.channel or template.channel
        result = await db.execute(
            select(MessageTemplate).where(
                and_(
                    MessageTemplate.name == template_data.name,
                    MessageTemplate.channel == channel,
                    MessageTemplate.template_id != template_id
                )
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una plantilla con el nombre '{template_data.name}' para el canal {channel}"
            )
    
    # Actualizar campos
    update_data = template_data.model_dump(exclude_unset=True)
    
    # Si se actualiza body o subject, actualizar variables automáticamente
    if "body" in update_data or "subject" in update_data:
        renderer = get_template_renderer()
        body = update_data.get("body", template.body)
        subject = update_data.get("subject", template.subject)
        body_vars = renderer.extract_variables(body)
        subject_vars = renderer.extract_variables(subject or "")
        update_data["variables"] = list(set(body_vars + subject_vars))
    
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar una plantilla."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.template_id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada"
        )
    
    # No permitir eliminar plantillas del sistema
    if template.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pueden eliminar las plantillas del sistema"
        )
    
    await db.delete(template)
    await db.commit()
    
    return None


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: UUID,
    preview_data: TemplatePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generar preview de una plantilla con variables."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.template_id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada"
        )
    
    renderer = get_template_renderer()
    rendered = renderer.preview(template, preview_data.variables)
    
    return TemplatePreviewResponse(
        subject=rendered.get("subject"),
        body=rendered.get("body"),
        rendered_variables=rendered.get("rendered_variables"),
        missing_variables=rendered.get("missing_variables"),
        extra_variables=rendered.get("extra_variables"),
    )


@router.post("/{template_id}/duplicate", response_model=MessageTemplateResponse)
async def duplicate_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Duplicar una plantilla existente."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.template_id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada"
        )
    
    # Crear copia
    new_template = MessageTemplate(
        name=f"{template.name} (Copia)",
        description=template.description,
        channel=template.channel,
        subject=template.subject,
        body=template.body,
        variables=template.variables.copy() if template.variables else [],
        is_active=True,
        is_default=False,
        created_by=current_user.id,
    )
    
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    return new_template


# ============== VARIABLE ADMIN ENDPOINTS ==============

@router.post("/admin/variables", response_model=TemplateVariableResponse, status_code=status.HTTP_201_CREATED)
async def create_variable(
    variable_data: TemplateVariableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear una nueva variable global (solo admin)."""
    # Verificar si ya existe
    result = await db.execute(
        select(TemplateVariable).where(TemplateVariable.name == variable_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una variable con el nombre '{variable_data.name}'"
        )
    
    variable = TemplateVariable(
        name=variable_data.name,
        description=variable_data.description,
        example_value=variable_data.example_value,
        category=variable_data.category,
        is_active=True,
    )
    
    db.add(variable)
    await db.commit()
    await db.refresh(variable)
    
    return variable


@router.patch("/admin/variables/{variable_id}", response_model=TemplateVariableResponse)
async def update_variable(
    variable_id: UUID,
    variable_data: TemplateVariableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar una variable global."""
    result = await db.execute(
        select(TemplateVariable).where(TemplateVariable.variable_id == variable_id)
    )
    variable = result.scalar_one_or_none()
    
    if not variable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable no encontrada"
        )
    
    update_data = variable_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variable, field, value)
    
    await db.commit()
    await db.refresh(variable)
    
    return variable
