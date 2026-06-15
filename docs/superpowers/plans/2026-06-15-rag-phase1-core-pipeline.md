# RAG 客服对话系统 — 实现计划 (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建基础 RAG 管道，实现文档上传 → 解析分块 → 向量化 → 检索 → LLM 流式回答的完整链路

**Architecture:** FastAPI 后端提供 REST API，LangChain 1.x 编排 RAG 流程，ChromaDB 做向量存储，SQLite 存元数据，Vue3 前端提供对话界面和文档管理

**Tech Stack:** Python 3.11+, FastAPI, LangChain 1.x, ChromaDB, SQLite, Vue 3 + Vite, 火山引擎 API

---

## 文件结构

```
sprag/
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── config.py                # 配置管理
│   │   ├── database.py              # SQLite 连接 + ORM
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── document.py          # Document ORM
│   │   │   └── chunk.py             # Chunk ORM
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── document.py          # Pydantic schemas
│   │   │   └── chat.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py              # 对话 API
│   │   │   └── documents.py         # 文档管理 API
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── document_processor.py  # 解析+分块+向量化
│   │   │   ├── retriever.py           # 向量检索
│   │   │   └── generator.py           # Prompt+LLM+流式
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── vector_store.py        # ChromaDB 封装
│   │       └── llm_service.py         # 火山引擎 API
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_document_processor.py
│       ├── test_retriever.py
│       └── test_chat_api.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── api/
│       │   └── index.js
│       ├── views/
│       │   ├── ChatView.vue
│       │   └── AdminView.vue
│       └── components/
│           ├── chat/
│           │   ├── ChatWindow.vue
│           │   ├── MessageBubble.vue
│           │   └── SourceReference.vue
│           └── admin/
│               └── DocumentUploader.vue
```

---

### Task 1: 项目初始化与配置

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.2
pydantic-settings==2.1.0
python-multipart==0.0.6
langchain==0.1.0
langchain-community==0.0.10
langchain-chroma==0.0.4
chromadb==0.4.22
volcengine-python-sdk==1.0.0
pypdf==3.17.4
python-docx==1.1.0
markdown==3.5.1
beautifulsoup4==4.12.2
httpx==0.25.2
pytest==7.4.3
pytest-asyncio==0.23.2
```

- [ ] **Step 2: 创建 .env.example**

```env
VOLC_ACCESS_KEY=your_access_key
VOLC_SECRET_KEY=your_secret_key
VOLC_ENDPOINT=ark.cn-beijing.volces.com
LLM_MODEL_NAME=ep-xxxx-xxxxx
EMBEDDING_MODEL_NAME=ep-xxxx-xxxxx
CHROMA_PERSIST_DIR=./chroma_db
DATABASE_URL=sqlite:///./sprag.db
UPLOAD_DIR=./uploads
```

- [ ] **Step 3: 创建 config.py**

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    volc_access_key: str = ""
    volc_secret_key: str = ""
    volc_endpoint: str = "ark.cn-beijing.volces.com"
    llm_model_name: str = ""
    embedding_model_name: str = ""
    chroma_persist_dir: str = "./chroma_db"
    database_url: str = "sqlite:///./sprag.db"
    upload_dir: str = "./uploads"

    # RAG 参数
    chunk_size: int = 500
    chunk_overlap: int = 50
    retriever_top_k: int = 10
    reranker_top_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

# 确保目录存在
Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: 创建 database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 5: 创建 backend/app/__init__.py**（空文件）

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app/
git commit -m "feat: initialize project structure and configuration"
```

---

### Task 2: 数据模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/document.py`
- Create: `backend/app/models/chunk.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/schemas/chat.py`

- [ ] **Step 1: 创建 Document ORM 模型**

```python
# backend/app/models/document.py
import datetime
from sqlalchemy import String, Text, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(50))  # pdf, docx, md, html
    category: Mapped[str] = mapped_column(String(100), default="default")
    file_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.PENDING.value)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
```

- [ ] **Step 2: 创建 Chunk ORM 模型**

```python
# backend/app/models/chunk.py
import datetime
from sqlalchemy import String, Text, Integer, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    embedding_id: Mapped[str] = mapped_column(String(100), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
```

- [ ] **Step 3: 创建 models/__init__.py**

```python
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk

__all__ = ["Document", "DocumentStatus", "Chunk"]
```

- [ ] **Step 4: 创建 Pydantic schemas**

```python
# backend/app/schemas/__init__.py
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentListResponse
from app.schemas.chat import ChatRequest, ChatResponse, SourceReference

__all__ = [
    "DocumentCreate", "DocumentResponse", "DocumentListResponse",
    "ChatRequest", "ChatResponse", "SourceReference",
]
```

```python
# backend/app/schemas/document.py
import datetime
from pydantic import BaseModel
from typing import Optional


class DocumentCreate(BaseModel):
    title: str
    category: str = "default"


class DocumentResponse(BaseModel):
    id: int
    title: str
    doc_type: str
    category: str
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]
```

```python
# backend/app/schemas/chat.py
from pydantic import BaseModel
from typing import Optional


class SourceReference(BaseModel):
    chunk_id: int
    document_title: str
    content: str
    score: float
    page_number: Optional[int] = None


class ChatRequest(BaseModel):
    session_id: str
    query: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceReference]
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/
git commit -m "feat: add data models and Pydantic schemas"
```

---

### Task 3: LLM 服务与向量存储封装

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/llm_service.py`
- Create: `backend/app/services/vector_store.py`

- [ ] **Step 1: 创建 services/__init__.py**

```python
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService

__all__ = ["LLMService", "VectorStoreService"]
```

- [ ] **Step 2: 创建 LLMService（火山引擎 API 封装）**

```python
# backend/app/services/llm_service.py
from openai import OpenAI
from app.config import settings
from typing import Generator


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=f"{settings.volc_access_key}:{settings.volc_secret_key}",
            base_url=f"https://{settings.volc_endpoint}/api/v3",
        )
        self.model = settings.llm_model_name

    def chat_stream(
        self, messages: list[dict], temperature: float = 0.7
    ) -> Generator[str, None, None]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=settings.embedding_model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]
```

- [ ] **Step 3: 创建 VectorStoreService（ChromaDB 封装）**

```python
# backend/app/services/vector_store.py
import chromadb
from chromadb.config import Settings
from app.config import settings
from app.services.llm_service import LLMService


class VectorStoreService:
    def __init__(self, llm_service: LLMService):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.llm_service = llm_service
        self.collection = self.client.get_or_create_collection(
            name="sprag_docs",
            metadata={"hnsw:space": "cosine"},
        )

    def add_texts(self, ids: list[str], texts: list[str], metadatas: list[dict]):
        embeddings = self.llm_service.embed(texts)
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def similarity_search(
        self, query: str, k: int = 10
    ) -> list[dict]:
        query_embedding = self.llm_service.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        if not results["ids"]:
            return []

        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],  # cosine -> similarity
            })
        return items

    def delete_by_document(self, document_id: int):
        self.collection.delete(where={"document_id": str(document_id)})

    def delete_by_ids(self, ids: list[str]):
        self.collection.delete(ids=ids)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/
git commit -m "feat: add LLM service and ChromaDB vector store"
```

---

### Task 4: 文档处理流水线

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/document_processor.py`

- [ ] **Step 1: 创建 rag/__init__.py**

```python
from app.rag.document_processor import DocumentProcessor

__all__ = ["DocumentProcessor"]
```

- [ ] **Step 2: 创建 DocumentProcessor（文档解析+分块+向量化）**

```python
# backend/app/rag/document_processor.py
import os
import json
import uuid
from pathlib import Path
from typing import BinaryIO

from langchain.text_splitter import RecursiveCharacterTextSplitter
import pypdf
import docx
import markdown
from bs4 import BeautifulSoup

from app.config import settings
from app.models.document import Document, DocumentStatus
from app.services.vector_store import VectorStoreService


class DocumentProcessor:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

    def extract_text(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        elif ext == ".md":
            return self._extract_md(file_path)
        elif ext in (".html", ".htm"):
            return self._extract_html(file_path)
        elif ext == ".txt":
            return Path(file_path).read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, file_path: str) -> str:
        reader = pypdf.PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _extract_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    def _extract_md(self, file_path: str) -> str:
        raw = Path(file_path).read_text(encoding="utf-8")
        html = markdown.markdown(raw)
        return BeautifulSoup(html, "html.parser").get_text()

    def _extract_html(self, file_path: str) -> str:
        raw = Path(file_path).read_text(encoding="utf-8")
        return BeautifulSoup(raw, "html.parser").get_text()

    def process_document(self, document: Document) -> int:
        file_path = document.file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        raw_text = self.extract_text(file_path)
        chunks = self.text_splitter.split_text(raw_text)

        chunk_ids = []
        texts = []
        metadatas = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)
            texts.append(chunk_text)
            metadatas.append({
                "document_id": str(document.id),
                "document_title": document.title,
                "chunk_index": str(i),
                "doc_type": document.doc_type,
                "category": document.category,
            })

        # 写入向量库
        self.vector_store.add_texts(chunk_ids, texts, metadatas)
        return len(chunks)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/rag/
git commit -m "feat: add document processing pipeline"
```

---

### Task 5: 检索与生成模块

**Files:**
- Create: `backend/app/rag/retriever.py`
- Create: `backend/app/rag/generator.py`

- [ ] **Step 1: 创建 Retriever**

```python
# backend/app/rag/retriever.py
from app.config import settings
from app.services.vector_store import VectorStoreService


class Retriever:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        top_k = k or settings.retriever_top_k
        results = self.vector_store.similarity_search(query, k=top_k)
        return results
```

- [ ] **Step 2: 创建 Generator**

```python
# backend/app/rag/generator.py
from typing import Generator
from app.services.llm_service import LLMService


SYSTEM_PROMPT = """你是一个专业的客服助手。请根据提供的参考文档内容回答用户的问题。

规则：
1. 只使用参考文档中的信息回答问题
2. 如果参考文档中没有相关信息，请明确告知用户你不知道
3. 在回答中引用参考来源，使用 [来源X] 的格式标注
4. 使用中文回答，语气专业友好
5. 回答要简洁准确，不要编造信息"""


class Generator:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def build_messages(
        self, query: str, contexts: list[dict], history: list[dict]
    ) -> list[dict]:
        context_text = "\n\n".join(
            f"[来源{i+1}] {item['content']}"
            for i, item in enumerate(contexts)
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 历史消息（保留最近 6 轮）
        for msg in history[-6:]:
            messages.append(msg)

        user_content = f"参考文档：\n{context_text}\n\n用户问题：{query}"
        messages.append({"role": "user", "content": user_content})
        return messages

    def generate_stream(
        self, query: str, contexts: list[dict], history: list[dict]
    ) -> Generator[str, None, None]:
        messages = self.build_messages(query, contexts, history)
        yield from self.llm_service.chat_stream(messages)
```

- [ ] **Step 3: 更新 rag/__init__.py**

```python
from app.rag.document_processor import DocumentProcessor
from app.rag.retriever import Retriever
from app.rag.generator import Generator

__all__ = ["DocumentProcessor", "Retriever", "Generator"]
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/rag/
git commit -m "feat: add retriever and generator modules"
```

---

### Task 6: FastAPI 入口与 API 路由

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/documents.py`

- [ ] **Step 1: 创建 main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import chat, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SPRAG - Customer Service RAG", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: 创建 api/__init__.py**

```python
from app.api import chat, documents
```

- [ ] **Step 3: 创建 documents API**

```python
# backend/app/api/documents.py
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentListResponse
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.rag.document_processor import DocumentProcessor
from app.config import settings

router = APIRouter(prefix="/documents", tags=["documents"])

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
    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".md", ".html", ".htm", ".txt"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    doc_title = title or Path(file.filename).stem
    save_path = Path(settings.upload_dir) / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

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

        chunk_count = doc_processor.process_document(document)

        # 写入 chunks 到关系库
        for i in range(chunk_count):
            db.add(Chunk(document_id=document.id, chunk_index=i, content="", metadata_json="{}"))
        db.commit()

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

    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    db.delete(document)
    db.commit()
    return {"message": "deleted"}
```

- [ ] **Step 4: 创建 chat API**

```python
# backend/app/api/chat.py
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRequest
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.rag.retriever import Retriever
from app.rag.generator import Generator

router = APIRouter(prefix="/chat", tags=["chat"])

llm_service = LLMService()
vector_store = VectorStoreService(llm_service)
retriever = Retriever(vector_store)
generator = Generator(llm_service)


@router.post("")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. 检索
    contexts = retriever.retrieve(request.query)

    # 2. 生成（流式）
    def stream_response():
        full_answer = ""
        for chunk in generator.generate_stream(request.query, contexts, request.history):
            full_answer += chunk
            yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

        # 发送来源引用
        sources = [
            {
                "chunk_id": 0,
                "document_title": ctx.get("metadata", {}).get("document_title", ""),
                "content": ctx["content"][:200],
                "score": round(ctx["score"], 4),
            }
            for ctx in contexts[:5]
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/api/
git commit -m "feat: add FastAPI entry point and API routes"
```

---

### Task 7: 后端测试

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_document_processor.py`
- Create: `backend/tests/test_retriever.py`
- Create: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 创建 conftest.py**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_sprag.db"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

- [ ] **Step 2: 创建 document_processor 测试**

```python
# backend/tests/test_document_processor.py
import tempfile
from pathlib import Path
import pytest


def test_extract_text_from_txt():
    from app.rag.document_processor import DocumentProcessor
    from app.services.vector_store import VectorStoreService
    from app.services.llm_service import LLMService

    llm = LLMService()
    vs = VectorStoreService(llm)
    dp = DocumentProcessor(vs)

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("这是测试文档内容。\n第二行内容。")
        f.flush()
        text = dp.extract_text(f.name)
        assert "这是测试文档内容" in text
        assert "第二行内容" in text
    Path(f.name).unlink()


def test_extract_text_unsupported():
    from app.rag.document_processor import DocumentProcessor
    from app.services.vector_store import VectorStoreService
    from app.services.llm_service import LLMService

    llm = LLMService()
    vs = VectorStoreService(llm)
    dp = DocumentProcessor(vs)

    with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
        f.write("test")
        f.flush()
        with pytest.raises(ValueError, match="Unsupported file type"):
            dp.extract_text(f.name)
    Path(f.name).unlink()
```

- [ ] **Step 3: 创建 retriever 测试**

```python
# backend/tests/test_retriever.py
def test_retriever_returns_list():
    from app.services.llm_service import LLMService
    from app.services.vector_store import VectorStoreService
    from app.rag.retriever import Retriever

    llm = LLMService()
    vs = VectorStoreService(llm)
    retriever = Retriever(vs)

    results = retriever.retrieve("test query", k=3)
    assert isinstance(results, list)
```

- [ ] **Step 4: 创建 chat API 测试**

```python
# backend/tests/test_chat_api.py
def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_unsupported_file(test_client):
    response = test_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.exe", b"fake content", "application/x-msdownload")},
        data={"title": "test"},
    )
    assert response.status_code == 400
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && pip install -r requirements.txt && python -m pytest tests/ -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "test: add backend tests for core modules"
```

---

### Task 8: Vue3 前端 — 项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/api/index.js`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "sprag-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.5",
    "axios": "^1.6.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.2",
    "vite": "^5.0.8"
  }
}
```

- [ ] **Step 2: 创建 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SPRAG 客服助手</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 4: 创建 main.js**

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

createApp(App).use(router).mount('#app')
```

- [ ] **Step 5: 创建 App.vue**

```vue
<template>
  <div id="app-root">
    <router-view />
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
</style>
```

- [ ] **Step 6: 创建 api/index.js**

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

export function uploadDocument(file, title, category) {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (category) form.append('category', category)
  return api.post('/documents/upload', form)
}

export function listDocuments(params) {
  return api.get('/documents', { params })
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

export function sendChatMessage(sessionId, query, history) {
  return api.post('/chat', { session_id: sessionId, query, history }, {
    responseType: 'stream',
    adapter: 'fetch',
  })
}

export default api
```

- [ ] **Step 7: 创建 router/index.js**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import AdminView from '../views/AdminView.vue'

const routes = [
  { path: '/', name: 'chat', component: ChatView },
  { path: '/admin', name: 'admin', component: AdminView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Vue3 frontend project"
```

---

### Task 9: Vue3 前端 — 对话界面

**Files:**
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/components/chat/ChatWindow.vue`
- Create: `frontend/src/components/chat/MessageBubble.vue`
- Create: `frontend/src/components/chat/SourceReference.vue`

- [ ] **Step 1: 创建 ChatView.vue（主页面）**

```vue
<template>
  <div class="chat-page">
    <header class="chat-header">
      <h1>SPRAG 客服助手</h1>
      <router-link to="/admin" class="admin-link">管理后台</router-link>
    </header>
    <ChatWindow />
  </div>
</template>

<script setup>
import ChatWindow from '../components/chat/ChatWindow.vue'
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}
.chat-header h1 {
  font-size: 18px;
  color: #333;
}
.admin-link {
  color: #1976d2;
  text-decoration: none;
  font-size: 14px;
}
</style>
```

- [ ] **Step 2: 创建 ChatWindow.vue**

```vue
<template>
  <div class="chat-window">
    <div class="messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        您好！我是客服助手，请描述您遇到的问题。
      </div>
      <MessageBubble
        v-for="(msg, i) in messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
        :sources="msg.sources"
      />
    </div>
    <div class="input-area">
      <textarea
        v-model="input"
        @keydown.enter.exact="send"
        placeholder="请输入您的问题..."
        :disabled="loading"
        rows="2"
      />
      <button @click="send" :disabled="loading || !input.trim()">
        {{ loading ? '思考中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { sendChatMessage } from '../../api/index.js'

const input = ref('')
const loading = ref(false)
const messages = ref([])
const messagesRef = ref(null)
const sessionId = ref('session_' + Date.now())

async function send() {
  if (!input.value.trim() || loading.value) return
  const query = input.value
  messages.value.push({ role: 'user', content: query })
  input.value = ''
  loading.value = true

  const history = messages.value.slice(-12, -1).map(m => ({
    role: m.role,
    content: m.content,
  }))

  messages.value.push({ role: 'assistant', content: '', sources: [] })

  try {
    const response = await sendChatMessage(sessionId.value, query, history)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') continue
        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'token') {
            messages.value[messages.value.length - 1].content += parsed.content
          } else if (parsed.type === 'sources') {
            messages.value[messages.value.length - 1].sources = parsed.sources
          }
        } catch { /* skip partial lines */ }
      }
    }
  } catch (err) {
    messages.value[messages.value.length - 1].content = '抱歉，发生了错误，请稍后重试。'
  } finally {
    loading.value = false
    await nextTick()
    messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: 'smooth' })
  }
}
</script>

<style scoped>
.chat-window { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 16px 20px; }
.empty-state { text-align: center; color: #999; margin-top: 40px; font-size: 15px; }
.input-area {
  display: flex; gap: 8px; padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
}
.input-area textarea {
  flex: 1; resize: none; padding: 10px; border: 1px solid #d0d0d0;
  border-radius: 8px; font-size: 14px; outline: none;
}
.input-area button {
  padding: 10px 20px; background: #1976d2; color: #fff;
  border: none; border-radius: 8px; cursor: pointer; font-size: 14px;
}
.input-area button:disabled { background: #ccc; cursor: not-allowed; }
</style>
```

- [ ] **Step 3: 创建 MessageBubble.vue**

```vue
<template>
  <div :class="['message', role]">
    <div class="avatar">{{ role === 'user' ? 'U' : 'A' }}</div>
    <div class="bubble">
      <div class="content" v-html="renderedContent" />
      <SourceReference v-if="sources && sources.length > 0" :sources="sources" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SourceReference from './SourceReference.vue'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  sources: { type: Array, default: () => [] },
})

const renderedContent = computed(() => {
  return props.content
    .replace(/\n/g, '<br>')
    .replace(/\[来源(\d+)\]/g, '<sup class="source-ref">[$1]</sup>')
})
</script>

<style scoped>
.message { display: flex; gap: 10px; margin-bottom: 16px; }
.message.user { flex-direction: row-reverse; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: bold; flex-shrink: 0;
}
.user .avatar { background: #1976d2; color: #fff; }
.assistant .avatar { background: #e0e0e0; color: #333; }
.bubble { max-width: 75%; }
.user .bubble {
  background: #1976d2; color: #fff; padding: 10px 14px;
  border-radius: 12px 4px 12px 12px; font-size: 14px;
}
.assistant .bubble {
  background: #f5f5f5; padding: 10px 14px;
  border-radius: 4px 12px 12px 12px; font-size: 14px; color: #333;
}
.content { line-height: 1.6; }
.source-ref { font-size: 11px; color: #1976d2; cursor: pointer; }
</style>
```

- [ ] **Step 4: 创建 SourceReference.vue**

```vue
<template>
  <div class="source-references">
    <div class="label">来源引用：</div>
    <div class="items">
      <div
        v-for="(src, i) in sources"
        :key="i"
        class="source-item"
        @click="expanded[i] = !expanded[i]"
      >
        <span class="badge">{{ i + 1 }}</span>
        <span class="title">{{ src.document_title }}</span>
        <span class="score">{{ (src.score * 100).toFixed(0) }}%</span>
        <div v-if="expanded[i]" class="preview">{{ src.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ sources: { type: Array, required: true } })
const expanded = ref({})
</script>

<style scoped>
.source-references { margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; }
.label { font-size: 12px; color: #666; margin-bottom: 4px; }
.items { display: flex; flex-wrap: wrap; gap: 6px; }
.source-item {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; background: #e3f2fd; border-radius: 4px;
  font-size: 12px; cursor: pointer;
}
.badge { font-weight: bold; color: #1976d2; }
.title { color: #555; }
.score { color: #999; font-size: 11px; }
.preview { margin-top: 4px; padding: 4px; background: #fff; border-radius: 4px; font-size: 12px; color: #666; width: 100%; }
</style>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ChatView.vue frontend/src/components/chat/
git commit -m "feat: add customer chat interface"
```

---

### Task 10: Vue3 前端 — 后台管理界面

**Files:**
- Create: `frontend/src/views/AdminView.vue`
- Create: `frontend/src/components/admin/DocumentUploader.vue`

- [ ] **Step 1: 创建 AdminView.vue**

```vue
<template>
  <div class="admin-page">
    <header class="admin-header">
      <h1>知识库管理</h1>
      <router-link to="/">返回对话</router-link>
    </header>
    <div class="admin-content">
      <DocumentUploader @uploaded="loadDocuments" />
      <div class="doc-list">
        <h2>文档列表</h2>
        <table>
          <thead>
            <tr>
              <th>标题</th><th>类型</th><th>分类</th><th>状态</th><th>上传时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in documents" :key="doc.id">
              <td>{{ doc.title }}</td>
              <td>{{ doc.doc_type }}</td>
              <td>{{ doc.category }}</td>
              <td>
                <span :class="['status', doc.status]">
                  {{ statusMap[doc.status] || doc.status }}
                </span>
              </td>
              <td>{{ new Date(doc.created_at).toLocaleString() }}</td>
              <td>
                <button @click="remove(doc.id)" class="delete-btn">删除</button>
              </td>
            </tr>
            <tr v-if="documents.length === 0">
              <td colspan="6" class="empty">暂无文档</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DocumentUploader from '../components/admin/DocumentUploader.vue'
import { listDocuments, deleteDocument } from '../api/index.js'

const documents = ref([])
const statusMap = { pending: '待处理', processing: '处理中', ready: '就绪', failed: '失败' }

async function loadDocuments() {
  const res = await listDocuments({ limit: 100 })
  documents.value = res.data.items
}

async function remove(id) {
  if (!confirm('确定删除此文档？')) return
  await deleteDocument(id)
  await loadDocuments()
}

onMounted(loadDocuments)
</script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; padding: 20px; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.admin-header h1 { font-size: 22px; }
.admin-header a { color: #1976d2; text-decoration: none; font-size: 14px; }
.admin-content { display: flex; flex-direction: column; gap: 24px; }
.doc-list h2 { font-size: 16px; margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
th { background: #f5f5f5; font-weight: 600; }
.status { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.status.ready { background: #e8f5e9; color: #2e7d32; }
.status.failed { background: #ffebee; color: #c62828; }
.status.processing { background: #fff3e0; color: #ef6c00; }
.status.pending { background: #f5f5f5; color: #666; }
.delete-btn { padding: 4px 12px; background: #ef5350; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.empty { text-align: center; color: #999; padding: 24px; }
</style>
```

- [ ] **Step 2: 创建 DocumentUploader.vue**

```vue
<template>
  <div class="uploader">
    <h2>上传文档</h2>
    <div class="form">
      <input type="file" @change="onFileChange" accept=".pdf,.docx,.md,.html,.htm,.txt" />
      <input v-model="title" placeholder="文档标题（可选）" />
      <input v-model="category" placeholder="分类（默认 default）" />
      <button @click="upload" :disabled="!file || uploading">
        {{ uploading ? '上传中...' : '上传' }}
      </button>
      <span v-if="message" :class="['msg', msgType]">{{ message }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { uploadDocument } from '../../api/index.js'

const emit = defineEmits(['uploaded'])
const file = ref(null)
const title = ref('')
const category = ref('')
const uploading = ref(false)
const message = ref('')
const msgType = ref('')

function onFileChange(e) {
  file.value = e.target.files[0] || null
}

async function upload() {
  if (!file.value) return
  uploading.value = true
  message.value = ''
  try {
    await uploadDocument(file.value, title.value, category.value)
    message.value = '上传成功！'
    msgType.value = 'success'
    file.value = null
    title.value = ''
    category.value = ''
    emit('uploaded')
  } catch (err) {
    message.value = err.response?.data?.detail || '上传失败'
    msgType.value = 'error'
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.uploader { padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; }
.uploader h2 { font-size: 16px; margin-bottom: 12px; }
.form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.form input[type="file"] { font-size: 14px; }
.form input[type="text"] { padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px; }
.form button { padding: 8px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.form button:disabled { background: #ccc; }
.msg { font-size: 13px; }
.msg.success { color: #2e7d32; }
.msg.error { color: #c62828; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/AdminView.vue frontend/src/components/admin/
git commit -m "feat: add admin dashboard with document management"
```

---

### Task 11: 启动脚本与 README

**Files:**
- Create: `backend/run.py`
- Create: `README.md`

- [ ] **Step 1: 创建 run.py**

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 2: 创建 README.md**

```markdown
# SPRAG — 客服对话 RAG 系统

面向终端客户的智能客服问答系统，基于 RAG（检索增强生成）架构。

## 技术栈

- 后端：Python, FastAPI, LangChain 1.x, ChromaDB
- 前端：Vue 3, Vite
- LLM：火山引擎 API（豆包大模型）

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 编辑 .env 填入火山引擎密钥
python run.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 进入对话界面，/admin 进入管理后台。

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── database.py          # 数据库
│   ├── models/              # ORM 模型
│   ├── schemas/             # Pydantic 模式
│   ├── api/                 # API 路由
│   ├── rag/                 # RAG 引擎
│   └── services/            # 基础设施服务
└── tests/
frontend/
├── src/
│   ├── views/               # 页面
│   ├── components/          # 组件
│   └── api/                 # API 客户端
```
```

- [ ] **Step 3: 创建 .gitignore**

```
__pycache__/
*.pyc
.env
chroma_db/
uploads/
*.db
node_modules/
dist/
```

- [ ] **Step 4: Commit**

```bash
git add backend/run.py README.md .gitignore
git commit -m "docs: add startup script and README"
```

---

## Self-Review: 覆盖度检查

对照 spec 检查 Phase 1 实现覆盖：

| Spec 需求 | 对应 Task |
|-----------|-----------|
| 文档格式解析（PDF/Word/MD/HTML/TXT） | Task 4 — DocumentProcessor.extract_text |
| 智能分块 | Task 4 — RecursiveCharacterTextSplitter |
| 向量化入库 ChromaDB | Task 3 — VectorStoreService, Task 4 — process_document |
| 向量检索 | Task 5 — Retriever |
| Prompt 组装 + LLM 调用 | Task 5 — Generator |
| 流式输出 | Task 5 — Generator, Task 6 — chat API SSE |
| 引用注入 | Task 5 — SYSTEM_PROMPT [来源X] 格式 |
| 文档上传 API | Task 6 — documents/upload |
| 文档列表/删除 API | Task 6 — list_documents, delete_document |
| FastAPI CORS | Task 6 — main.py CORS middleware |
| 客户对话界面（流式+来源） | Task 9 — ChatWindow, MessageBubble, SourceReference |
| 后台文档管理界面 | Task 10 — AdminView, DocumentUploader |
| 配置管理 | Task 1 — config.py, .env.example |
| 数据模型 | Task 2 — Document, Chunk ORM + Pydantic schemas |
| 测试 | Task 7 — document_processor, retriever, chat API |

未覆盖（Phase 2-4 范围）：
- Query 重写（Phase 2）
- 指代消解（Phase 2）
- 混合检索 BM25（Phase 2）
- 重排序（Phase 2）
- 日志收集与可观测性仪表盘（Phase 4）
- 用户反馈收集（Phase 4）
