# 文档上传 → 向量数据库 测试用例

## 基本信息

| 项目 | 值 |
|---|---|
| 测试文件 | `backend/tests/test_document_upload.py` |
| 测试框架 | pytest 9.0 + FastAPI TestClient |
| 测试策略 | HTTP 端到端(走完整路由) + mock LLM 避免真实 API |
| 数据库隔离 | 每个用例独立 Milvus Lite 数据库(`tmp_path`) |
| 依赖 mock | `LLMService.embed()` 返回全零向量(1024 维) |

---

## 测试用例清单

总计 **16 个用例**,分 5 个场景类。

---

### 一、`TestDocumentUpload` — 文档上传基础校验(5)

| # | 用例 | 验证内容 | 步骤 |
|:--:|:---|---|:--:|
| 1 | `test_upload_txt_success` | 上传 .txt 文件,返回就绪状态 | ①POST `/upload` → ②断言 200 + status=ready + doc_type=txt |
| 2 | `test_upload_without_title_uses_filename` | 不传 title 时自动用文件名 | ①POST `/upload`(无 title) → ②断言 title==文件名 |
| 3 | `test_upload_unsupported_file_type` | 不支持的文件类型 → 400 | ①POST `/upload`(.exe) → ②断言 400 + "Unsupported" |
| 4 | `test_upload_without_filename` | 空文件名 → 422(Pydantic 校验拒绝) | ①POST `/upload`(filename="") → ②断言 422 |
| 5 | `test_upload_invalid_store` | 非法的 store 值 → 400 | ①POST `/upload`(store="invalid") → ②断言 400 + "Invalid store" |
| 6 | `test_upload_no_auth` | 未认证 → 401 | ①POST `/upload`(无 token) → ②断言 401 |

---

### 二、`TestDocumentList` — 文档列表查询(3)

| # | 用例 | 验证内容 | 步骤 |
|:--:|:---|---|:--:|
| 7 | `test_list_documents` | 上传后列表应包含 | ①上传文档 → ②GET `/documents` → ③断言 id 在列表中 |
| 8 | `test_list_documents_filter_status` | 按 status 过滤 | ①上传文档 → ②GET `?status=ready`(应包含) → ③GET `?status=pending`(应不包含) |
| 9 | `test_list_documents_filter_store` | 按 store 过滤 | ①上传文档 → ②GET `?store=vector` → ③断言 id 在结果中 |

---

### 三、`TestDocumentChunks` — 文档分块查询(2)

| # | 用例 | 验证内容 | 步骤 |
|:--:|:---|---|:--:|
| 10 | `test_get_chunks_after_upload` | 上传后分块在 Milvus 中可查 | ①上传 5 段文本 → ②GET `/{id}/chunks` → ③断言 chunks>0 + chunk_index 有序 |
| 11 | `test_get_chunks_not_found` | 不存在的文档 → 404 | ①GET `/documents/99999/chunks` → ②断言 404 |

---

### 四、`TestDocumentDelete` — 文档删除(2)

| # | 用例 | 验证内容 | 步骤 |
|:--:|:---|---|:--:|
| 12 | `test_delete_document` | 删除后列表不含 + 分块不可查 | ①上传 → ②DELETE → ③列表不含 id → ④分块 404 |
| 13 | `test_delete_not_found` | 删除不存在的 → 404 | ①DELETE `/documents/99999` → ②断言 404 |

---

### 五、`TestDocumentReprocess` — 文档重试(2)

| # | 用例 | 验证内容 | 步骤 |
|:--:|:---|---|:--:|
| 14 | `test_reprocess_ready_document` | 已就绪文档可 reprocess | ①上传 → ②POST `/{id}/reprocess` → ③断言 message=="reprocessed" |
| 15 | `test_reprocess_not_found` | 不存在的 → 404 | ①POST `/documents/99999/reprocess` → ②断言 404 |

---

### 六、`TestDocumentLifecycle` — 完整生命周期(1)

| # | 用例 | 验证内容 | 步骤 |
|:--:|:---|---|:--:|
| 16 | `test_full_lifecycle` | 上传 → 确认 → 分块 → 重试 → 删除 全流程 | ①上传(断言 ready) → ②列表确认 → ③分块查询 → ④重试 → ⑤删除 → ⑥列表确认已删 |

---

## Fixture 清单

| Fixture | 作用域 | 说明 |
|---|---|---|
| `mock_embed` | function(autouse) | Mock `LLMService.embed()` 返回 `[[0.0]*1024]` |
| `txt_file` | function | 创建临时 .txt 文件(中文内容),自动清理 |
| `md_file` | function | 创建临时 .md 文件,自动清理 |
| `milvus_db` | function(autouse) | 每个用例独立的 Milvus Lite 数据库(`tmp_path`) |
| `clean_upload_dir` | function(autouse) | 清理 uploads 目录 |

---

## 断言矩阵

| 检查点 | 预期 |
|---|---|
| 上传成功 | HTTP 200, `status`=`"ready"`, `id`>0, `title`/`doc_type`/`store` 正确 |
| 文件类型不支持 | HTTP 400, `detail` 含 `"Unsupported"` |
| 无认证 | HTTP 401 |
| 列表查询 | HTTP 200, `total`>=1, `items` 含目标文档 id |
| 分块查询 | HTTP 200, `chunks` 非空, `chunk_index` 升序 |
| 删除 | HTTP 200, 列表不含 id, 分块 404 |
| 重试 | HTTP 200, `message`=`"reprocessed"` |
| 不存在 | HTTP 404 |

---

## 运行命令

```bash
# 单独跑文档上传测试
cd backend
python3.11 -m pytest tests/test_document_upload.py -v

# 跑全部测试
python3.11 -m pytest tests/ -v
```
