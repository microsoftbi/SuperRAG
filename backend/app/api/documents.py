# backend/app/api/documents.py
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.rag.document_processor import DocumentProcessor

router = APIRouter(prefix="/documents", tags=["documents"])

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".html", ".htm", ".txt"}

llm_service = LLMService()
vector_store = VectorStoreService(llm_service)
doc_processor = DocumentProcessor(vector_store)


@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("default"),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    doc_title = title or Path(file.filename).stem
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = Path(settings.upload_dir) / unique_name
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file.file.close()

    document = Document(
        title=doc_title,
        doc_type=ext.lstrip("."),
        category=category,
        file_path=str(save_path),
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        document.status = DocumentStatus.PROCESSING.value
        db.commit()

        doc_processor.process_document(document)

        document.status = DocumentStatus.READY.value
        db.commit()
    except Exception as e:
        document.status = DocumentStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return document


@router.get("", response_model=DocumentListResponse)
def list_documents(
    category: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if category:
        query = query.filter(Document.category == category)
    if status:
        query = query.filter(Document.status == status)
    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    return DocumentListResponse(total=total, items=items)


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    vector_store.delete_by_document(document_id)

    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(document)
    db.commit()
    return {"message": "deleted"}
