"""Seed data para plantillas de mensajes."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MessageTemplate, TemplateVariable, MessageChannel


# Variables globales por defecto
DEFAULT_VARIABLES = [
    {"name": "candidate_name", "description": "Nombre completo del candidato", "example_value": "Juan Pérez", "category": "candidate"},
    {"name": "candidate_email", "description": "Correo electrónico del candidato", "example_value": "juan.perez@email.com", "category": "candidate"},
    {"name": "candidate_phone", "description": "Teléfono del candidato", "example_value": "+52 55 1234 5678", "category": "candidate"},
    {"name": "role_title", "description": "Título de la vacante", "example_value": "Desarrollador Senior Python", "category": "role"},
    {"name": "role_company", "description": "Nombre de la empresa", "example_value": "TechCorp", "category": "role"},
    {"name": "consultant_name", "description": "Nombre del consultor", "example_value": "María González", "category": "consultant"},
    {"name": "consultant_phone", "description": "Teléfono del consultor", "example_value": "+52 55 8765 4321", "category": "consultant"},
    {"name": "consultant_email", "description": "Email del consultor", "example_value": "maria@topmanagement.com", "category": "consultant"},
    {"name": "application_date", "description": "Fecha de aplicación", "example_value": "16 de febrero de 2025", "category": "system"},
    {"name": "current_date", "description": "Fecha actual", "example_value": "16 de febrero de 2025", "category": "system"},
]

# Plantillas por defecto
DEFAULT_TEMPLATES = [
    {
        "name": "Contacto Inicial WhatsApp",
        "description": "Primer contacto con candidato vía WhatsApp",
        "channel": MessageChannel.WHATSAPP,
        "subject": None,
        "body": """¡Hola {candidate_name}! 👋

Soy {consultant_name} de Top Management. Me comunico contigo porque vimos tu perfil y creemos que podrías ser un excelente candidato para la posición de {role_title} en {role_company}.

¿Tendrías disponibilidad para una breve conversación esta semana?

Quedo atento a tu respuesta.

Saludos,
{consultant_name}
📱 {consultant_phone}""",
        "variables": ["candidate_name", "consultant_name", "role_title", "role_company", "consultant_phone"],
    },
    {
        "name": "Contacto Inicial Email",
        "description": "Primer contacto con candidato vía correo electrónico",
        "channel": MessageChannel.EMAIL,
        "subject": "Oportunidad laboral: {role_title} en {role_company}",
        "body": """Estimado/a {candidate_name},

Espero que te encuentres muy bien. Mi nombre es {consultant_name} y soy consultor/a de reclutamiento en Top Management.

Me pongo en contacto contigo porque revisamos tu perfil profesional y consideramos que tu experiencia y habilidades podrían ser un excelente match para la posición de <strong>{role_title}</strong> que estamos gestionando para <strong>{role_company}</strong>.

<strong>Próximos pasos:</strong>
Si te interesa conocer más detalles sobre esta oportunidad, me encantaría agendar una breve llamada para contarte más sobre el rol y responder cualquier pregunta que tengas.

¿Tendrías disponibilidad para conversar esta semana? Puedes responder a este correo o contactarme directamente al {consultant_phone}.

Quedo atento/a a tu respuesta.

Saludos cordiales,

{consultant_name}
Consultor/a de Reclutamiento
Top Management
📧 {consultant_email}
📱 {consultant_phone}""",
        "variables": ["candidate_name", "consultant_name", "role_title", "role_company", "consultant_phone", "consultant_email"],
    },
    {
        "name": "Seguimiento No Respuesta",
        "description": "Seguimiento cuando el candidato no responde al primer contacto",
        "channel": MessageChannel.WHATSAPP,
        "subject": None,
        "body": """¡Hola {candidate_name}! 👋

Hace unos días te escribí sobre la oportunidad de {role_title} en {role_company}.

Entiendo que puedes estar ocupado/a, pero no quería dejar de insistir porque creo que esta posición podría interesarte mucho.

Si prefieres, podemos agendar una llamada rápida de 10 minutos para que conozcas los detalles. ¿Te funcionaría el jueves o viernes?

Quedo atento,
{consultant_name}
📱 {consultant_phone}""",
        "variables": ["candidate_name", "role_title", "role_company", "consultant_name", "consultant_phone"],
    },
]


async def seed_template_variables(db: AsyncSession) -> None:
    """Inserta las variables globales por defecto si no existen."""
    for var_data in DEFAULT_VARIABLES:
        # Verificar si ya existe
        result = await db.execute(
            select(TemplateVariable).where(TemplateVariable.name == var_data["name"])
        )
        if result.scalar_one_or_none():
            continue
        
        variable = TemplateVariable(
            variable_id=uuid.uuid4(),
            name=var_data["name"],
            description=var_data["description"],
            example_value=var_data.get("example_value"),
            category=var_data.get("category", "general"),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(variable)
    
    await db.commit()
    print("✅ Variables de plantilla creadas")


async def seed_default_templates(db: AsyncSession) -> None:
    """Inserta las plantillas por defecto si no existen."""
    for template_data in DEFAULT_TEMPLATES:
        # Verificar si ya existe
        result = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.name == template_data["name"],
                MessageTemplate.channel == template_data["channel"]
            )
        )
        if result.scalar_one_or_none():
            continue
        
        template = MessageTemplate(
            template_id=uuid.uuid4(),
            name=template_data["name"],
            description=template_data["description"],
            channel=template_data["channel"],
            subject=template_data["subject"],
            body=template_data["body"],
            variables=template_data["variables"],
            is_active=True,
            is_default=True,  # Marcar como plantilla del sistema
            created_by=None,  # Plantillas del sistema no tienen creador
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(template)
    
    await db.commit()
    print("✅ Plantillas por defecto creadas")


async def seed_message_templates(db: AsyncSession) -> None:
    """Ejecuta todos los seeds del módulo de plantillas."""
    await seed_template_variables(db)
    await seed_default_templates(db)
