# backend/app/api/documents.py
import json
import shutil
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.rag.document_processor import DocumentProcessor
from app.rag.bm25_retriever import BM25Retriever
from app.models.user import User
from app.models.knowledge_base import document_knowledge_base
from app.models.chunk import Chunk
from app.services.auth_service import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".html", ".htm", ".txt"}
VALID_STORES = {"vector", "graph", "both"}

llm_service = LLMService()
vector_store = VectorStoreService(llm_service)
bm25_retriever = BM25Retriever()
doc_processor = DocumentProcessor(vector_store, bm25_retriever)

# KG 服务（由 main.py 注入）
_neo4j_service = None
_entity_extractor = None


def init_documents_kg(neo4j_service, entity_extractor):
    global _neo4j_service, _entity_extractor
    _neo4j_service = neo4j_service
    _entity_extractor = entity_extractor


@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("default"),
    store: str = Form("vector"),
    knowledge_base_ids: str = Form("[]"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if store not in VALID_STORES:
        raise HTTPException(status_code=400, detail=f"Invalid store value: {store}, must be vector/graph/both")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    doc_title = title or Path(file.filename).stem
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = Path(settings.upload_dir) / unique_name
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file.file.close()

    kb_ids = json.loads(knowledge_base_ids)

    document = Document(
        title=doc_title,
        doc_type=ext.lstrip("."),
        category=category,
        file_path=str(save_path),
        store=store,
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    for kb_id in kb_ids:
        db.execute(
            document_knowledge_base.insert().values(
                document_id=document.id, knowledge_base_id=kb_id
            )
        )
    db.commit()

    try:
        document.status = DocumentStatus.PROCESSING.value
        db.commit()

        # ── 按 store 类型决定处理流程 ──
        run_vector = store in ("vector", "both")
        run_graph = store in ("graph", "both") and settings.enable_knowledge_graph

        if run_vector:
            doc_processor.process_document(document)

        if run_graph:
            if _neo4j_service and _entity_extractor and settings.kg_extract_on_upload:
                _process_document_kg(document, db)

        document.status = DocumentStatus.READY.value
        db.commit()
    except Exception as e:
        document.status = DocumentStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return document


def _process_document_kg(document: Document, db: Session):
    """KG 处理：全文存 SQLite → LLM提取实体/关系 → 写入 Neo4j。"""
    try:
        raw_text = doc_processor.extract_text(document.file_path)
        if not raw_text.strip():
            logger.info("Doc %d: empty text, skipping KG", document.id)
            return

        # 全文存 SQLite（1条，不分块）
        chunk = Chunk(
            document_id=document.id,
            content=raw_text,
            chunk_index=0,
            metadata_json=json.dumps({"source": "kg_full_text"}),
        )
        db.add(chunk)
        db.flush()
        chunk_ids = [chunk.id]
        db.commit()

        # LLM 提取实体和关系
        result = _entity_extractor.extract(raw_text)

        if not result["entities"]:
            logger.info("Doc %d: no entities found", document.id)
            return

        logger.info(
            "Doc %d: %d entities, %d relations",
            document.id, len(result["entities"]),
            len(result["relationships"]),
        )

        # 写入 Neo4j
        _neo4j_service.import_extraction(
            chunk_ids=chunk_ids,
            entities=result["entities"],
            relationships=result["relationships"],
        )
    except Exception as e:
        logger.error("Doc %d KG processing failed (non-fatal): %s", document.id, e)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    category: str | None = None,
    status: str | None = None,
    store: str | None = Query(None, description="Filter by store type: vector, graph, both"),
    knowledge_base_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if category:
        query = query.filter(Document.category == category)
    if status:
        query = query.filter(Document.status == status)
    if store:
        query = query.filter(Document.store == store)
    if knowledge_base_id:
        query = query.join(document_knowledge_base).filter(
            document_knowledge_base.c.knowledge_base_id == knowledge_base_id
        )
    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    response_items = []
    for doc in items:
        kb_ids = [r.knowledge_base_id for r in db.execute(
            document_knowledge_base.select().where(
                document_knowledge_base.c.document_id == doc.id
            )
        ).all()]
        resp = DocumentResponse.model_validate(doc)
        resp.knowledge_base_ids = kb_ids
        response_items.append(resp)

    return DocumentListResponse(total=total, items=response_items)


@router.delete("/{document_id}")
def delete_document(document_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    vector_store.delete_by_document(document_id)
    bm25_retriever.delete_by_document(document_id)

    db.execute(
        document_knowledge_base.delete().where(
            document_knowledge_base.c.document_id == document_id
        )
    )

    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(document)
    db.commit()
    return {"message": "deleted"}


@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取指定文档的分块内容。

    向量存储的文档从 Milvus Lite 查询分块；
    图谱存储的文档从 SQLite chunks 表查询（全文一条）。
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = []

    if document.store in ("vector", "both"):
        try:
            chunks = vector_store.get_document_chunks(document_id)
        except Exception as e:
            logger.warning("ChromaDB chunk query failed for doc %d: %s", document_id, e)

    elif document.store == "graph":
        try:
            sql_chunks = (
                db.query(Chunk)
                .filter(Chunk.document_id == document_id)
                .order_by(Chunk.chunk_index)
                .all()
            )
            for c in sql_chunks:
                chunks.append({
                    "chunk_id": str(c.id),
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "metadata": json.loads(c.metadata_json) if c.metadata_json else {},
                })
        except Exception as e:
            logger.warning("SQLite chunk query failed for doc %d: %s", document_id, e)

    return {"document_id": document_id, "chunks": chunks}


# ── LLM 智能分块（调用大模型分块，不入库，仅预览）──

@router.post("/{document_id}/chunks/llm-preview")
def preview_llm_chunks(
    document_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Use LLM to chunk a document and return preview (no save)."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    raw_text = doc_processor.extract_text(document.file_path)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="提取的文本为空")

    # Use LLM to chunk (preview only, no save)
    chunks = llm_service.llm_chunk(raw_text)

    return {
        "chunks": chunks,
        "count": len(chunks),
    }


# ── LLM 智能分块（调用大模型分块并入库）──

@router.post("/{document_id}/chunks/llm-commit")
def commit_llm_chunks(
    document_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Use LLM to chunk a document and store in Milvus."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    raw_text = doc_processor.extract_text(document.file_path)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="提取的文本为空")

    # Use LLM to chunk
    chunks = llm_service.llm_chunk(raw_text)

    chunk_ids = []
    texts = []
    metadatas = []
    for i, chunk_text in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        chunk_ids.append(chunk_id)
        texts.append(chunk_text)
        metadatas.append({
            "document_id": document.id,
            "document_title": document.title,
            "chunk_index": i,
            "doc_type": document.doc_type,
            "category": document.category,
        })

    document.status = DocumentStatus.PROCESSING.value
    db.commit()

    try:
        vector_store.add_texts(chunk_ids, texts, metadatas)
    except Exception as ve:
        document.status = DocumentStatus.FAILED.value
        db.commit()
        logger.error("LLM chunk add_texts failed: %s", ve, exc_info=True)
        raise HTTPException(status_code=500, detail=f"向量入库失败: {ve}")

    document.status = DocumentStatus.READY.value
    db.commit()

    if bm25_retriever:
        bm25_retriever.rebuild_async(vector_store=vector_store)

    return {
        "message": "ok",
        "doc_id": document.id,
        "chunks_count": len(chunks),
    }


# ── 分块预览（调后端切分，不入库）──

@router.post("/preview-chunks")
def preview_chunks(data: dict):
    """按指定参数切分文本（不保存到 Milvus），用于前端预览。"""
    doc_id = data.get("doc_id")
    chunk_size = data.get("chunk_size", settings.chunk_size)
    chunk_overlap = data.get("chunk_overlap", settings.chunk_overlap)
    if not doc_id:
        raise HTTPException(status_code=400, detail="doc_id is required")

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        raw_text = doc_processor.extract_text(document.file_path)
        if not raw_text.strip():
            return {"chunks": [], "count": 0}
    finally:
        db.close()

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_text(raw_text)
    return {"chunks": chunks, "count": len(chunks)}


# ── 两步上传：第一步（预上传 + 提取文本，不切分）──

class PreviewResponse(BaseModel):
    doc_id: int
    file_name: str
    title: str
    text: str
    char_count: int


@router.post("/preview", response_model=PreviewResponse)
def preview_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("default"),
    store: str = Form("vector"),
    knowledge_base_ids: str = Form("[]"),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """上传文件 → 保存文件 → 提取文本 → 暂不切分入库。返回全文。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if store not in VALID_STORES:
        raise HTTPException(status_code=400, detail=f"Invalid store value: {store}")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    doc_title = title or Path(file.filename).stem
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = Path(settings.upload_dir) / unique_name
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file.file.close()

    kb_ids = json.loads(knowledge_base_ids)

    # 创建文档记录（PENDING 状态，暂不处理）
    document = Document(
        title=doc_title,
        doc_type=ext.lstrip("."),
        category=category,
        file_path=str(save_path),
        store=store,
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    for kb_id in kb_ids:
        db.execute(
            document_knowledge_base.insert().values(
                document_id=document.id, knowledge_base_id=kb_id
            )
        )
    db.commit()

    # 提取文本
    try:
        raw_text = doc_processor.extract_text(str(save_path))
    except Exception as e:
        document.status = DocumentStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=f"文本提取失败: {e}")

    return PreviewResponse(
        doc_id=document.id,
        file_name=file.filename,
        title=doc_title,
        text=raw_text,
        char_count=len(raw_text),
    )


# ── 两步上传：第二步（按指定参数切分并入库）──

@router.post("/commit-chunks")
def commit_chunks(
    data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """按指定分块参数切分文本并存入 Milvus。"""
    doc_id = data.get("doc_id")
    if not doc_id:
        raise HTTPException(status_code=400, detail="doc_id is required")

    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_size = data.get("chunk_size", settings.chunk_size)
    chunk_overlap = data.get("chunk_overlap", settings.chunk_overlap)
    custom_title = data.get("title", "")

    if custom_title:
        document.title = custom_title

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )

    try:
        raw_text = doc_processor.extract_text(document.file_path)
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="提取的文本为空")

        chunks = text_splitter.split_text(raw_text)
        chunk_ids = []
        texts = []
        metadatas = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)
            texts.append(chunk_text)
            metadatas.append({
                "document_id": document.id,
                "document_title": document.title,
                "chunk_index": i,
                "doc_type": document.doc_type,
                "category": document.category,
            })

        document.status = DocumentStatus.PROCESSING.value
        db.commit()

        # 向量入库（含 embedding）
        try:
            vector_store.add_texts(chunk_ids, texts, metadatas)
        except Exception as ve:
            document.status = DocumentStatus.FAILED.value
            db.commit()
            logger.error("add_texts failed: %s", ve, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"向量入库失败: {ve}",
            )

        document.status = DocumentStatus.READY.value
        db.commit()

        if bm25_retriever:
            bm25_retriever.rebuild_async(vector_store=vector_store)

        return {
            "message": "ok",
            "doc_id": document.id,
            "chunks_count": len(chunks),
        }
    except HTTPException:
        raise
    except Exception as e:
        document.status = DocumentStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bm25/rebuild")
def rebuild_bm25(
    user: User = Depends(require_admin),
):
    """Rebuild BM25 index synchronously."""
    from app.rag.bm25_retriever import BM25Retriever
    bm25 = BM25Retriever()
    bm25.rebuild_index(vector_store=vector_store)
    if bm25.initialized:
        return {"message": "BM25 index rebuilt", "terms": bm25.get_dim()}
    else:
        return {"message": "No documents to build BM25 index"}


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """重新处理已失败的文档。"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 重置状态并重新处理
    from app.rag.document_processor import DocumentProcessor
    document.status = DocumentStatus.PROCESSING.value
    db.commit()

    try:
        doc_processor.process_document(document)

        if document.store in ("graph", "both") and settings.enable_knowledge_graph:
            _process_document_kg(document, db)

        document.status = DocumentStatus.READY.value
        db.commit()
        return {"message": "reprocessed", "id": document.id}
    except Exception as e:
        document.status = DocumentStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{document_id}/knowledge-bases")
def update_document_knowledge_bases(
    document_id: int,
    data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update which knowledge bases a document belongs to."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    kb_ids = data.get("knowledge_base_ids", [])

    db.execute(
        document_knowledge_base.delete().where(
            document_knowledge_base.c.document_id == document_id
        )
    )
    for kb_id in kb_ids:
        db.execute(
            document_knowledge_base.insert().values(
                document_id=document_id, knowledge_base_id=kb_id
            )
        )
    db.commit()
    return {"message": "ok"}