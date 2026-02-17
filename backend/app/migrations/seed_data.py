"""
Seed Data para desarrollo
Carga datos de prueba en la base de datos.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models import (
    User, UserRole, UserStatus,
    JobOpening, 
    Candidate, CandidateStatus,
    Evaluation,
    Configuration
)
from app.migrations.seed_templates import seed_message_templates


async def seed_database():
    """Carga datos de prueba en la base de datos."""
    async with async_session_maker() as session:
        try:
            # 1. Crear consultores de prueba si no existen
            consultants = await _seed_consultants(session)
            
            # 2. Crear ofertas de trabajo
            job_openings = await _seed_job_openings(session, consultants)
            
            # 3. Crear candidatos
            candidates = await _seed_candidates(session, job_openings)
            
            # 4. Crear evaluaciones
            await _seed_evaluations(session, candidates)
            
            # 5. Crear configuraciones de ejemplo
            await _seed_configurations(session)
            
            # 6. Crear plantillas de mensajes por defecto
            await seed_message_templates(session)
            
            await session.commit()
            print("✅ Seed data cargado exitosamente")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error cargando seed data: {e}")
            raise


async def _seed_consultants(session: AsyncSession) -> list[User]:
    """Crea consultores de prueba."""
    consultants = []
    
    # Verificar si ya existen
    from sqlalchemy import select
    result = await session.execute(select(User).where(User.role == UserRole.CONSULTANT))
    existing = result.scalars().all()
    
    if existing:
        print(f"   ℹ️  {len(existing)} consultores ya existen")
        return list(existing)
    
    test_consultants = [
        {
            "email": "consultant1@example.com",
            "full_name": "Ana García",
            "phone": "+573001234567",
            "role": UserRole.CONSULTANT,
            "status": UserStatus.ACTIVE,
        },
        {
            "email": "consultant2@example.com",
            "full_name": "Carlos Martínez",
            "phone": "+573002345678",
            "role": UserRole.CONSULTANT,
            "status": UserStatus.ACTIVE,
        },
    ]
    
    from app.core.security import get_password_hash
    
    for data in test_consultants:
        consultant = User(
            id=uuid.uuid4(),
            email=data["email"],
            hashed_password=get_password_hash("password123"),
            full_name=data["full_name"],
            phone=data["phone"],
            role=data["role"],
            status=data["status"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(consultant)
        consultants.append(consultant)
    
    await session.flush()
    print(f"   ✅ {len(consultants)} consultores creados")
    return consultants


async def _seed_job_openings(session: AsyncSession, consultants: list[User]) -> list[JobOpening]:
    """Crea ofertas de trabajo de prueba."""
    from sqlalchemy import select
    result = await session.execute(select(JobOpening))
    existing = result.scalars().all()
    
    if existing:
        print(f"   ℹ️  {len(existing)} ofertas ya existen")
        return list(existing)
    
    job_openings = []
    
    test_jobs = [
        {
            "title": "Desarrollador Backend Senior",
            "description": """
Buscamos un Desarrollador Backend Senior con experiencia en:
- Python / FastAPI
- PostgreSQL y Redis
- Arquitectura de microservicios
- AWS o GCP

Requisitos:
- 5+ años de experiencia
- Inglés intermedio-avanzado
- Experiencia con sistemas de alta concurrencia
            """,
            "department": "Ingeniería",
            "location": "Remoto (LATAM)",
            "seniority": "Senior",
            "sector": "Tecnología",
            "status": "published",
        },
        {
            "title": "Product Manager",
            "description": """
Estamos buscando un Product Manager para liderar nuestro equipo de producto.

Responsabilidades:
- Definir roadmap de producto
- Trabajar con stakeholders
- Análisis de métricas y datos
- Priorización de features

Requisitos:
- 3+ años como PM
- Experiencia en SaaS B2B
- Conocimiento de metodologías ágiles
            """,
            "department": "Producto",
            "location": "Bogotá, Colombia",
            "seniority": "Mid-Senior",
            "sector": "Tecnología",
            "status": "published",
        },
        {
            "title": "Diseñador UX/UI",
            "description": """
Buscamos un Diseñador UX/UI creativo y orientado a resultados.

Habilidades requeridas:
- Figma avanzado
- Diseño de sistemas de diseño
- Prototipado interactivo
- Research de usuarios

Requisitos:
- Portfolio demostrable
- 2+ años de experiencia
- Conocimiento de HTML/CSS (deseable)
            """,
            "department": "Diseño",
            "location": "Remoto",
            "seniority": "Mid",
            "sector": "Tecnología",
            "status": "draft",
        },
    ]
    
    for i, data in enumerate(test_jobs):
        job = JobOpening(
            id=uuid.uuid4(),
            title=data["title"],
            description=data["description"].strip(),
            department=data["department"],
            location=data["location"],
            seniority=data["seniority"],
            sector=data["sector"],
            status=data["status"],
            assigned_consultant_id=consultants[i % len(consultants)].id if consultants else None,
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=i * 5),
            updated_at=datetime.utcnow(),
        )
        session.add(job)
        job_openings.append(job)
    
    await session.flush()
    print(f"   ✅ {len(job_openings)} ofertas creadas")
    return job_openings


async def _seed_candidates(session: AsyncSession, job_openings: list[JobOpening]) -> list[Candidate]:
    """Crea candidatos de prueba."""
    from sqlalchemy import select
    result = await session.execute(select(Candidate))
    existing = result.scalars().all()
    
    if existing:
        print(f"   ℹ️  {len(existing)} candidatos ya existen")
        return list(existing)
    
    candidates = []
    
    test_candidates = [
        {
            "full_name": "Juan Pérez López",
            "email": "juan.perez@email.com",
            "phone": "+573111234567",
            "status": CandidateStatus.NEW,
            "source": "web",
            "raw_data": {
                "experiencia": [
                    {"empresa": "TechCorp", "cargo": "Backend Dev", "años": 3},
                    {"empresa": "StartupXYZ", "cargo": "Full Stack", "años": 2},
                ],
                "educacion": [
                    {"institucion": "Universidad Nacional", "titulo": "Ingeniería de Sistemas", "año": 2019}
                ],
                "habilidades": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            },
            "extracted_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        },
        {
            "full_name": "María González",
            "email": "maria.gonzalez@email.com",
            "phone": "+573222345678",
            "status": CandidateStatus.IN_REVIEW,
            "source": "linkedin",
            "raw_data": {
                "experiencia": [
                    {"empresa": "ProductInc", "cargo": "Product Owner", "años": 4},
                ],
                "educacion": [
                    {"institucion": "Universidad de los Andes", "titulo": "Administración de Empresas", "año": 2018}
                ],
                "habilidades": ["Product Management", "Agile", "Scrum", "Analytics", "Figma"],
            },
            "extracted_skills": ["Product Management", "Agile", "Scrum", "Analytics"],
        },
        {
            "full_name": "Pedro Rodríguez",
            "email": "pedro.rodriguez@email.com",
            "phone": "+573333456789",
            "status": CandidateStatus.SHORTLISTED,
            "source": "referral",
            "raw_data": {
                "experiencia": [
                    {"empresa": "DesignStudio", "cargo": "UX Designer", "años": 3},
                    {"empresa": "AgencyABC", "cargo": "UI Designer", "años": 2},
                ],
                "educacion": [
                    {"institucion": "Universidad Javeriana", "titulo": "Diseño Gráfico", "año": 2017}
                ],
                "habilidades": ["Figma", "Adobe XD", "Sketch", "Prototyping", "User Research"],
            },
            "extracted_skills": ["Figma", "Adobe XD", "Sketch", "Prototyping"],
        },
        {
            "full_name": "Laura Hernández",
            "email": "laura.hernandez@email.com",
            "phone": "+573444567890",
            "status": CandidateStatus.NEW,
            "source": "web",
            "raw_data": {
                "experiencia": [
                    {"empresa": "DevCompany", "cargo": "Software Engineer", "años": 6},
                ],
                "educacion": [
                    {"institucion": "EAFIT", "titulo": "Ingeniería de Software", "año": 2016}
                ],
                "habilidades": ["Python", "Django", "React", "Node.js", "MongoDB"],
            },
            "extracted_skills": ["Python", "Django", "React", "Node.js"],
        },
        {
            "full_name": "Andrés Silva",
            "email": "andres.silva@email.com",
            "phone": "+573555678901",
            "status": CandidateStatus.INTERVIEW,
            "source": "linkedin",
            "raw_data": {
                "experiencia": [
                    {"empresa": "BigTech", "cargo": "Senior Backend Engineer", "años": 5},
                    {"empresa": "ScaleUp", "cargo": "Tech Lead", "años": 2},
                ],
                "educacion": [
                    {"institucion": "MIT", "titulo": "Computer Science", "año": 2015}
                ],
                "habilidades": ["Python", "Go", "Kubernetes", "Microservices", "System Design"],
            },
            "extracted_skills": ["Python", "Go", "Kubernetes", "Microservices"],
        },
    ]
    
    for i, data in enumerate(test_candidates):
        # Normalizar email y teléfono básico
        email_normalized = data["email"].lower().strip() if data["email"] else None
        phone_normalized = data["phone"].replace(" ", "").replace("-", "") if data["phone"] else None
        
        candidate = Candidate(
            id=uuid.uuid4(),
            full_name=data["full_name"],
            email=data["email"],
            email_normalized=email_normalized,
            phone=data["phone"],
            phone_normalized=phone_normalized,
            status=data["status"],
            source=data["source"],
            raw_data=data["raw_data"],
            extracted_skills=data["extracted_skills"],
            job_opening_id=job_openings[i % len(job_openings)].id if job_openings else None,
            is_duplicate=False,
            created_at=datetime.utcnow() - timedelta(days=i * 2, hours=i * 3),
            updated_at=datetime.utcnow() - timedelta(days=i),
        )
        session.add(candidate)
        candidates.append(candidate)
    
    await session.flush()
    print(f"   ✅ {len(candidates)} candidatos creados")
    return candidates


async def _seed_evaluations(session: AsyncSession, candidates: list[Candidate]):
    """Crea evaluaciones de prueba para candidatos."""
    from sqlalchemy import select
    result = await session.execute(select(Evaluation))
    existing = result.scalars().all()
    
    if existing:
        print(f"   ℹ️  {len(existing)} evaluaciones ya existen")
        return
    
    evaluations = []
    
    # Crear evaluaciones para algunos candidatos
    for i, candidate in enumerate(candidates[:4]):  # Solo para los primeros 4
        score = 65 + (i * 8)  # Scores variados: 65, 73, 81, 89
        
        decisions = ["REVIEW", "PROCEED", "PROCEED", "PROCEED"]
        decision = decisions[i]
        
        evaluation = Evaluation(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            score=score,
            decision=decision,
            strengths=[
                "Experiencia relevante en el sector",
                "Conocimiento técnico sólido",
                "Buena comunicación escrita"
            ],
            gaps=[
                "Podría fortalecer conocimientos en cloud",
                "Experiencia liderando equipos limitada"
            ] if i % 2 == 0 else [],
            red_flags=[] if decision != "REJECT_HARD" else ["Inconsistencias en experiencia"],
            evidence="El candidato demuestra experiencia sólida en Python y frameworks modernos. "
                    "Tiene proyectos relevantes que demuestran capacidad técnica.",
            llm_provider="openai",
            llm_model="gpt-4",
            prompt_version="v1.0",
            hard_filters_passed=True,
            hard_filters_failed={},
            evaluation_time_ms=2500 + (i * 500),
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        session.add(evaluation)
        evaluations.append(evaluation)
    
    await session.flush()
    print(f"   ✅ {len(evaluations)} evaluaciones creadas")


async def _seed_configurations(session: AsyncSession):
    """Crea configuraciones de ejemplo."""
    from sqlalchemy import select
    result = await session.execute(select(Configuration))
    existing = result.scalars().all()
    
    if existing:
        print(f"   ℹ️  {len(existing)} configuraciones ya existen")
        return
    
    # Nota: Estos son valores de ejemplo, en producción estarían encriptados
    test_configs = [
        {
            "category": "llm",
            "key": "default_provider",
            "value_encrypted": "openai",
            "description": "Proveedor de LLM por defecto",
            "is_encrypted": False,
            "is_json": False,
        },
        {
            "category": "llm",
            "key": "default_model",
            "value_encrypted": "gpt-4",
            "description": "Modelo de LLM por defecto",
            "is_encrypted": False,
            "is_json": False,
        },
        {
            "category": "notifications",
            "key": "email_enabled",
            "value_encrypted": "true",
            "description": "Habilitar notificaciones por email",
            "is_encrypted": False,
            "is_json": False,
        },
    ]
    
    for data in test_configs:
        config = Configuration(
            id=uuid.uuid4(),
            category=data["category"],
            key=data["key"],
            value_encrypted=data["value_encrypted"],
            description=data["description"],
            is_encrypted=data["is_encrypted"],
            is_json=data["is_json"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(config)
    
    await session.flush()
    print(f"   ✅ {len(test_configs)} configuraciones creadas")


if __name__ == "__main__":
    asyncio.run(seed_database())
