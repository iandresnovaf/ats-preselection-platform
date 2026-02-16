"""
Core ATS API - Documents Router
Endpoints para gestión de documentos/evidencia RAW.
"""
from typing import Optional
from uuid import UUID
import hashlib
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.core_ats import Document, Application, Role, Candidate
from app.schemas.core_ats import DocumentResponse, DocumentUploadRequest

router = APIRouter(prefix="/documents", tags=["Documents"])

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
    db: Session = Depends(get_db),
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
        app = db.query(Application).filter(Application.application_id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Aplicación no encontrada")
    
    if role_id:
        role = db.query(Role).filter(Role.role_id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    if candidate_id:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidato no encontrado")
    
    # Guardar archivo
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
    db_document = Document(
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
    db.commit()
    db.refresh(db_document)
    
    return db_document


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener información de un documento."""
    document = db.query(Document).filter(Document.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Descargar un documento."""
    document = db.query(Document).filter(Document.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    file_path = Path(document.storage_uri)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el sistema")
    
    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type="application/octet-stream"
    )


from datetime import datetime
