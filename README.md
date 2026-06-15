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
