"""
Script para crear datos de ejemplo en RHMatch 2.0
Ejecutar: python seed_headhunting_data.py
"""
import asyncio
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Importar modelos
import sys
sys.path.append('/home/andres/.openclaw/workspace/ats-platform/backend')

from app.core.database import Base
from app.models.core_ats import (
    HHCandidate, HHClient, HHRole, HHApplication,
    HHDocument, HHInterview, HHAssessment, HHAssessmentScore,
    HHFlag, HHAuditLog,
    RoleStatus, ApplicationStage, DocumentType, AssessmentType,
    FlagSeverity, FlagSource
)

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ats_platform"

async def seed_data():
    """Crear datos de ejemplo."""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("🌱 Creando datos de ejemplo...")
        
        # 1. CLIENTES
        print("📁 Creando clientes...")
        clients = [
            HHClient(
                client_id=uuid.uuid4(),
                client_name="TechCorp Colombia",
                industry="Tecnología",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHClient(
                client_id=uuid.uuid4(),
                client_name="Banco Financiero",
                industry="Banca",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHClient(
                client_id=uuid.uuid4(),
                client_name="RetailMax",
                industry="Retail",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        
        for client in clients:
            db.add(client)
        await db.commit()
        
        # Recuperar IDs
        result = await db.execute(select(HHClient))
        clients_db = result.scalars().all()
        techcorp = clients_db[0]
        banco = clients_db[1]
        retail = clients_db[2]
        
        # 2. VACANTES (ROLES)
        print("💼 Creando vacantes...")
        roles = [
            HHRole(
                role_id=uuid.uuid4(),
                client_id=techcorp.client_id,
                role_title="CTO - Chief Technology Officer",
                location="Bogotá",
                seniority="C-Level",
                status=RoleStatus.OPEN,
                date_opened=date.today() - timedelta(days=30),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHRole(
                role_id=uuid.uuid4(),
                client_id=banco.client_id,
                role_title="Director de Riesgos",
                location="Medellín",
                seniority="Director",
                status=RoleStatus.OPEN,
                date_opened=date.today() - timedelta(days=15),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHRole(
                role_id=uuid.uuid4(),
                client_id=retail.client_id,
                role_title="Gerente de Operaciones",
                location="Cali",
                seniority="Gerente",
                status=RoleStatus.OPEN,
                date_opened=date.today() - timedelta(days=45),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        
        for role in roles:
            db.add(role)
        await db.commit()
        
        result = await db.execute(select(HHRole))
        roles_db = result.scalars().all()
        cto_role = roles_db[0]
        riesgos_role = roles_db[1]
        ops_role = roles_db[2]
        
        # 3. CANDIDATOS
        print("👤 Creando candidatos...")
        candidates = [
            HHCandidate(
                candidate_id=uuid.uuid4(),
                full_name="Juan Carlos Martínez",
                national_id="1012345678",
                email="juan.martinez@email.com",
                phone="+57 300 123 4567",
                location="Bogotá",
                linkedin_url="https://linkedin.com/in/juanmartinez",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHCandidate(
                candidate_id=uuid.uuid4(),
                full_name="María Fernanda López",
                national_id="1023456789",
                email="maria.lopez@email.com",
                phone="+57 301 234 5678",
                location="Medellín",
                linkedin_url="https://linkedin.com/in/marialopez",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHCandidate(
                candidate_id=uuid.uuid4(),
                full_name="Carlos Andrés Rodríguez",
                national_id="1034567890",
                email="carlos.rodriguez@email.com",
                phone="+57 302 345 6789",
                location="Bogotá",
                linkedin_url="https://linkedin.com/in/carlosrodriguez",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHCandidate(
                candidate_id=uuid.uuid4(),
                full_name="Ana Patricia Gómez",
                national_id="1045678901",
                email="ana.gomez@email.com",
                phone="+57 303 456 7890",
                location="Cali",
                linkedin_url="https://linkedin.com/in/anagomez",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHCandidate(
                candidate_id=uuid.uuid4(),
                full_name="Pedro José Sánchez",
                national_id="1056789012",
                email="pedro.sanchez@email.com",
                phone="+57 304 567 8901",
                location="Barranquilla",
                linkedin_url="https://linkedin.com/in/pedrosanchez",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        
        for candidate in candidates:
            db.add(candidate)
        await db.commit()
        
        result = await db.execute(select(HHCandidate))
        candidates_db = result.scalars().all()
        juan = candidates_db[0]
        maria = candidates_db[1]
        carlos = candidates_db[2]
        ana = candidates_db[3]
        pedro = candidates_db[4]
        
        # 4. APLICACIONES (ENTIDAD CENTRAL)
        print("📝 Creando aplicaciones...")
        applications = [
            # CTO - Terna con 3 candidatos
            HHApplication(
                application_id=uuid.uuid4(),
                candidate_id=juan.candidate_id,
                role_id=cto_role.role_id,
                stage=ApplicationStage.TERNA,
                hired=False,
                overall_score=82.5,
                notes="Excelente candidato, muy técnico",
                created_at=datetime.utcnow() - timedelta(days=20),
                updated_at=datetime.utcnow()
            ),
            HHApplication(
                application_id=uuid.uuid4(),
                candidate_id=maria.candidate_id,
                role_id=cto_role.role_id,
                stage=ApplicationStage.TERNA,
                hired=False,
                overall_score=88.0,
                notes="Mejor candidata, perfil completo",
                created_at=datetime.utcnow() - timedelta(days=18),
                updated_at=datetime.utcnow()
            ),
            HHApplication(
                application_id=uuid.uuid4(),
                candidate_id=carlos.candidate_id,
                role_id=cto_role.role_id,
                stage=ApplicationStage.TERNA,
                hired=False,
                overall_score=75.0,
                notes="Buen candidato, necesita desarrollo",
                created_at=datetime.utcnow() - timedelta(days=15),
                updated_at=datetime.utcnow()
            ),
            # Director de Riesgos - En entrevista
            HHApplication(
                application_id=uuid.uuid4(),
                candidate_id=ana.candidate_id,
                role_id=riesgos_role.role_id,
                stage=ApplicationStage.INTERVIEW,
                hired=False,
                overall_score=79.0,
                notes="En proceso de entrevistas finales",
                created_at=datetime.utcnow() - timedelta(days=10),
                updated_at=datetime.utcnow()
            ),
            # Gerente de Operaciones - Contratado
            HHApplication(
                application_id=uuid.uuid4(),
                candidate_id=pedro.candidate_id,
                role_id=ops_role.role_id,
                stage=ApplicationStage.HIRED,
                hired=True,
                decision_date=date.today() - timedelta(days=5),
                overall_score=91.0,
                notes="Excelente match, contratado",
                created_at=datetime.utcnow() - timedelta(days=30),
                updated_at=datetime.utcnow()
            ),
        ]
        
        for app in applications:
            db.add(app)
        await db.commit()
        
        result = await db.execute(select(HHApplication))
        apps_db = result.scalars().all()
        
        # 5. DOCUMENTOS
        print("📄 Creando documentos...")
        docs = []
        for app in apps_db[:3]:  # Solo para CTO
            doc = HHDocument(
                document_id=uuid.uuid4(),
                application_id=app.application_id,
                doc_type=DocumentType.CV,
                original_filename=f"CV_{app.candidate_id}.pdf",
                storage_uri=f"/uploads/cv_{app.candidate_id}.pdf",
                sha256_hash=str(uuid.uuid4()),
                uploaded_by="admin@topmanagement.com",
                uploaded_at=datetime.utcnow()
            )
            docs.append(doc)
        for doc in docs:
            db.add(doc)
        await db.commit()
        
        # 6. EVALUACIONES PSICOMÉTRICAS (Factor Oscuro)
        print("🧠 Creando evaluaciones psicométricas...")
        assessments = []
        for i, app in enumerate(apps_db[:3]):
            assessment = HHAssessment(
                assessment_id=uuid.uuid4(),
                application_id=app.application_id,
                assessment_type=AssessmentType.FACTOR_OSCURO,
                assessment_date=date.today() - timedelta(days=10),
                sincerity_score=85.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            assessments.append(assessment)
        await db.add_all(assessments)
        await db.commit()
        
        result = await db.execute(select(HHAssessment))
        assessments_db = result.scalars().all()
        
        # 7. SCORES DE EVALUACIÓN (DINÁMICOS - FILAS)
        print("📊 Creando scores...")
        scores_data = [
            # Juan - CTO (Score 82.5)
            (assessments_db[0].assessment_id, "Egocentrismo", 45),
            (assessments_db[0].assessment_id, "Volatilidad", 38),
            (assessments_db[0].assessment_id, "Manipulación", 52),
            (assessments_db[0].assessment_id, "Riesgo de Conflicto", 41),
            (assessments_db[0].assessment_id, "Liderazgo Estratégico", 88),
            (assessments_db[0].assessment_id, "Toma de Decisiones", 85),
            # María - CTO (Score 88.0)
            (assessments_db[1].assessment_id, "Egocentrismo", 35),
            (assessments_db[1].assessment_id, "Volatilidad", 32),
            (assessments_db[1].assessment_id, "Manipulación", 40),
            (assessments_db[1].assessment_id, "Riesgo de Conflicto", 38),
            (assessments_db[1].assessment_id, "Liderazgo Estratégico", 92),
            (assessments_db[1].assessment_id, "Toma de Decisiones", 90),
            # Carlos - CTO (Score 75.0)
            (assessments_db[2].assessment_id, "Egocentrismo", 62),
            (assessments_db[2].assessment_id, "Volatilidad", 55),
            (assessments_db[2].assessment_id, "Manipulación", 68),
            (assessments_db[2].assessment_id, "Riesgo de Conflicto", 58),
            (assessments_db[2].assessment_id, "Liderazgo Estratégico", 78),
            (assessments_db[2].assessment_id, "Toma de Decisiones", 75),
        ]
        
        scores = []
        for assessment_id, dimension, value in scores_data:
            score = HHAssessmentScore(
                score_id=uuid.uuid4(),
                assessment_id=assessment_id,
                dimension=dimension,
                value=float(value),
                source_page=2
            )
            scores.append(score)
        await db.add_all(scores)
        await db.commit()
        
        # 8. FLAGS DE RIESGO
        print("🚩 Creando flags de riesgo...")
        flags = [
            # Juan - 1 flag medio
            HHFlag(
                flag_id=uuid.uuid4(),
                application_id=apps_db[0].application_id,
                category="riesgo_manipulacion",
                severity=FlagSeverity.MEDIUM,
                evidence="Score de manipulación de 52, ligeramente por encima del promedio",
                source=FlagSource.ASSESSMENT,
                created_at=datetime.utcnow()
            ),
            # María - Sin flags
            # Carlos - 2 flags
            HHFlag(
                flag_id=uuid.uuid4(),
                application_id=apps_db[2].application_id,
                category="riesgo_ego",
                severity=FlagSeverity.HIGH,
                evidence="Egocentrismo elevado (62), requiere validación en entrevista",
                source=FlagSource.ASSESSMENT,
                created_at=datetime.utcnow()
            ),
            HHFlag(
                flag_id=uuid.uuid4(),
                application_id=apps_db[2].application_id,
                category="riesgo_conflicto",
                severity=FlagSeverity.MEDIUM,
                evidence="Alta tendencia a manipulación (68)",
                source=FlagSource.ASSESSMENT,
                created_at=datetime.utcnow()
            ),
        ]
        await db.add_all(flags)
        await db.commit()
        
        # 9. ENTREVISTAS
        print("💬 Creando entrevistas...")
        interviews = [
            HHInterview(
                interview_id=uuid.uuid4(),
                application_id=apps_db[0].application_id,  # Juan
                interview_date=datetime.utcnow() - timedelta(days=5),
                interviewer="Consultor Senior A",
                summary_text="Excelente desempeño técnico. Muy buena comunicación. Demostró liderazgo en proyectos anteriores.",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            HHInterview(
                interview_id=uuid.uuid4(),
                application_id=apps_db[1].application_id,  # María
                interview_date=datetime.utcnow() - timedelta(days=4),
                interviewer="Consultor Senior A",
                summary_text="Candidata excepcional. Balance perfecto entre habilidades técnicas y blandas. Recomendada para avanzar.",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        await db.add_all(interviews)
        await db.commit()
        
        print("\n✅ Datos de ejemplo creados exitosamente!")
        print(f"\n📊 Resumen:")
        print(f"   • {len(clients_db)} Clientes")
        print(f"   • {len(roles_db)} Vacantes")
        print(f"   • {len(candidates_db)} Candidatos")
        print(f"   • {len(apps_db)} Aplicaciones")
        print(f"   • {len(assessments_db)} Evaluaciones")
        print(f"   • {len(scores)} Scores individuales")
        print(f"   • {len(flags)} Flags de riesgo")
        print(f"   • {len(interviews)} Entrevistas")
        
        print("\n🎉 Sistema listo para pruebas!")
        print("\n📌 URLs importantes:")
        print("   • http://localhost:3000/candidates")
        print("   • http://localhost:3000/roles")
        print("   • http://localhost:3000/terna-comparator")
        
if __name__ == "__main__":
    asyncio.run(seed_data())
