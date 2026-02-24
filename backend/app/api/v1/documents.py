"""
Core ATS API - HHDocuments Router
Endpoints para gestión de documentos/evidencia RAW.
"""
from typing import Optional
from uuid import UUID
import hashlib
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.core_ats import HHDocument, HHApplication, HHRole, HHCandidate
from app.schemas.core_ats import DocumentResponse, DocumentUploadRequest

router = APIRouter(prefix="/documents", tags=["HHDocuments"])

# Configuración de almacenamiento
UPLOAD_DIR = Path(settings.UPLOAD_DIR) if hasattr(settings, 'UPLOAD_DIR') else Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def compute_sha256(file_path: Path) -> str:
    """Calcular hash SHA256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Archivo a subir"),
    doc_type: str = Form(..., description="Tipo de documento: cv, interview, assessment, role_profile, other"),
    application_id: Optional[str] = Form(None, description="ID de aplicación (opcional)"),
    role_id: Optional[str] = Form(None, description="ID de rol/vacante (opcional)"),
    candidate_id: Optional[str] = Form(None, description="ID de candidato (opcional)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Subir un documento/evidencia al sistema."""
    
    # Validar tipo de documento
    valid_types = ['cv', 'interview', 'assessment', 'role_profile', 'other']
    if doc_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Tipo de documento inválido. Use: {valid_types}")
    
    # Validar que al menos una entidad esté relacionada
    if not any([application_id, role_id, candidate_id]):
        raise HTTPException(status_code=400, detail="Debe especificar al menos una entidad (application_id, role_id o candidate_id)")
    
    # Validar que las entidades existan
    if application_id:
        result = await db.execute(
            select(HHApplication).where(HHApplication.application_id == application_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    if role_id:
        result = await db.execute(
            select(HHRole).where(HHRole.role_id == role_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    if candidate_id:
        result = await db.execute(
            select(HHCandidate).where(HHCandidate.candidate_id == candidate_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Guardar archivo
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")
    finally:
        file.file.close()
    
    # Calcular hash
    sha256_hash = compute_sha256(file_path)
    
    # Crear registro en BD
    db_document = HHDocument(
        application_id=UUID(application_id) if application_id else None,
        role_id=UUID(role_id) if role_id else None,
        candidate_id=UUID(candidate_id) if candidate_id else None,
        doc_type=doc_type,
        original_filename=file.filename,
        storage_uri=str(file_path),
        sha256_hash=sha256_hash,
        uploaded_by=current_user.get("email", "system")
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    return db_document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener información de un documento."""
    result = await db.execute(
        select(HHDocument).where(HHDocument.document_id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="HHDocumento no encontrado")
    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Descargar un documento."""
    result = await db.execute(
        select(HHDocument).where(HHDocument.document_id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="HHDocumento no encontrado")
    
    file_path = Path(document.storage_uri)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el sistema")
    
    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type="application/octet-stream"
    )


from datetime import datetime
import tempfile
import os


@router.post("/extract-cv", status_code=status.HTTP_200_OK)
async def extract_cv_info(
    file: UploadFile = File(..., description="Archivo CV (PDF, DOC, DOCX)"),
    candidate_id: Optional[str] = Form(None, description="ID del candidato (opcional, para guardar la extracción)"),
    save_extraction: bool = Form(True, description="Guardar la extracción en la base de datos"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extraer información de un CV usando IA avanzada. Guarda en BD si se proporciona candidate_id."""
    
    # Validar formato
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {file_ext}. Use: PDF, DOCX, DOC, TXT"
        )
    
    temp_path = None
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        
        print(f"📄 Archivo temporal creado: {temp_path}, tamaño: {len(content)} bytes")
        
        # Leer el contenido del archivo
        text_content = ""
        extraction_method = "text"
        
        if file_ext == '.pdf':
            try:
                import pypdf
                print("📖 Leyendo PDF con pypdf...")
                with open(temp_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    print(f"📄 PDF tiene {len(reader.pages)} páginas")
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
                            print(f"  Página {i+1}: {len(page_text)} caracteres")
                print(f"✅ Texto extraído del PDF: {len(text_content)} caracteres")
            except Exception as e:
                print(f"❌ Error reading PDF: {e}")
                import traceback
                traceback.print_exc()
                text_content = ""
        
        elif file_ext in ['.docx', '.doc']:
            try:
                import docx2txt
                print("📖 Leyendo DOCX con docx2txt...")
                text_content = docx2txt.process(temp_path)
                print(f"✅ Texto extraído del DOCX: {len(text_content)} caracteres")
            except Exception as e:
                print(f"❌ Error reading DOCX: {e}")
                import traceback
                traceback.print_exc()
                text_content = ""
        
        elif file_ext == '.txt':
            print("📖 Leyendo archivo TXT...")
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
            print(f"✅ Texto extraído del TXT: {len(text_content)} caracteres")
        
        # Si no se extrajo suficiente texto, intentar OCR
        if not text_content or len(text_content.strip()) < 100:
            print(f"⚠️ Poco texto extraído ({len(text_content)} caracteres). Intentando OCR...")
            try:
                from pdf2image import convert_from_path
                import pytesseract
                
                print("📸 Convirtiendo PDF a imágenes para OCR...")
                images = convert_from_path(temp_path, dpi=200, first_page=1, last_page=3)
                print(f"📄 Convertidas {len(images)} páginas")
                
                ocr_text = ""
                for i, image in enumerate(images):
                    print(f"🔍 Aplicando OCR a página {i+1}...")
                    page_text = pytesseract.image_to_string(image, lang='spa+eng')
                    ocr_text += page_text + "\n"
                    print(f"  Página {i+1}: {len(page_text)} caracteres")
                
                if len(ocr_text.strip()) > len(text_content.strip()):
                    text_content = ocr_text
                    extraction_method = "ocr"
                    print(f"✅ OCR exitoso: {len(text_content)} caracteres extraídos")
                else:
                    print("⚠️ OCR no mejoró la extracción")
                    
            except Exception as ocr_error:
                print(f"❌ Error en OCR: {ocr_error}")
                import traceback
                traceback.print_exc()
        
        # Si aún no hay texto suficiente, devolver advertencia
        if not text_content or len(text_content.strip()) < 50:
            print(f"⚠️ No se pudo extraer texto suficiente ({len(text_content)} caracteres)")
            return {
                "success": True,
                "filename": file.filename,
                "extracted_data": {
                    "full_name": "",
                    "email": "",
                    "phone": "",
                    "location": "",
                    "linkedin_url": "",
                    "summary": "",
                    "experiences": [],
                    "education": [],
                    "skills": [],
                    "raw_text_preview": text_content[:500] if text_content else ""
                },
                "warning": "El archivo parece ser una imagen escaneada o no contiene texto extraíble."
            }
        
        # Usar el nuevo extractor avanzado de CVs
        print("🤖 Iniciando extracción avanzada con CVExtractor...")
        from app.services.cv_extractor import CVExtractor
        
        extractor = CVExtractor()
        cv_data = extractor.extract_with_ai(text_content, file.filename)
        
        print(f"✅ Extracción completada. Score de confianza: {cv_data.confidence_score:.1f}%")
        print(f"📊 Datos extraídos:")
        print(f"  - Nombre: {cv_data.full_name}")
        print(f"  - Email: {cv_data.email}")
        print(f"  - Teléfono: {cv_data.phone}")
        print(f"  - Móvil: {cv_data.mobile}")
        print(f"  - Ubicación: {cv_data.location}")
        print(f"  - LinkedIn: {cv_data.linkedin_url}")
        print(f"  - GitHub: {cv_data.github_url}")
        print(f"  - Experiencias: {len(cv_data.experiences)}")
        print(f"  - Educación: {len(cv_data.education)}")
        print(f"  - Habilidades: {len(cv_data.skills)}")
        print(f"  - Certificaciones: {len(cv_data.certifications)}")
        print(f"  - Idiomas: {len(cv_data.languages)}")
        print(f"  - Años de experiencia: {cv_data.years_experience}")
        
        # Convertir a diccionario para la respuesta
        extracted_data = cv_data.to_dict()
        
        # Guardar en la base de datos si se proporciona candidate_id
        extraction_record = None
        if save_extraction and candidate_id:
            try:
                from app.models.core_ats import HHCVExtraction
                import hashlib
                
                # Calcular hash del archivo
                file_hash = hashlib.sha256(content).hexdigest()
                
                # Crear registro de extracción
                extraction_record = HHCVExtraction(
                    candidate_id=candidate_id,
                    raw_text=text_content[:50000],  # Limitar tamaño
                    extracted_json=extracted_data,
                    extraction_method=extraction_method if extraction_method != "text" else "pdf_text",
                    confidence_score=cv_data.confidence_score,
                    filename=file.filename,
                    file_hash=file_hash,
                    file_size_bytes=len(content),
                    mime_type=file.content_type or "application/pdf",
                    processing_status="completed"
                )
                
                db.add(extraction_record)
                await db.commit()
                await db.refresh(extraction_record)
                
                print(f"💾 Extracción guardada en BD: {extraction_record.extraction_id}")
                
            except Exception as db_error:
                print(f"⚠️ Error guardando en BD: {db_error}")
                await db.rollback()
                # No fallar la extracción si no se puede guardar en BD
        
        return {
            "success": True,
            "filename": file.filename,
            "extracted_data": extracted_data,
            "confidence_score": cv_data.confidence_score,
            "extraction_method": f"{extraction_method}_ai_enhanced",
            "fields_found": [k for k, v in extracted_data.items() if v and k not in ['raw_text', 'extraction_date']],
            "saved_to_db": extraction_record is not None,
            "extraction_id": str(extraction_record.extraction_id) if extraction_record else None
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando CV: {str(e)}")
    finally:
        # Limpiar archivo temporal
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            print(f"🧹 Archivo temporal eliminado: {temp_path}")
