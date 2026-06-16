<template>
  <div class="kb-manager">
    <div class="header">
      <h2>知识库管理</h2>
      <button @click="showCreate = true" class="btn-primary">+ 新建知识库</button>
    </div>

    <!-- Create/Edit Form -->
    <div v-if="showCreate" class="kb-form">
      <input v-model="formName" placeholder="知识库名称" />
      <input v-model="formDesc" placeholder="描述（可选）" />
      <button @click="save" :disabled="saving" class="btn-primary">
        {{ editing ? '保存' : '创建' }}
      </button>
      <button @click="cancelForm" class="btn-cancel">取消</button>
    </div>

    <table v-if="kbs.length">
      <thead>
        <tr>
          <th>名称</th><th>描述</th><th>文档数</th><th>创建时间</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="kb in kbs" :key="kb.id">
          <td>{{ kb.name }}</td>
          <td>{{ kb.description || '-' }}</td>
          <td>{{ kb.doc_count }}</td>
          <td>{{ new Date(kb.created_at).toLocaleDateString() }}</td>
          <td>
            <button @click="edit(kb)" class="btn-edit">编辑</button>
            <button @click="openDocManager(kb)" class="btn-manage">管理文档</button>
            <button @click="remove(kb.id)" class="btn-danger">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">暂无知识库</div>

    <!-- Document Manager Modal -->
    <div v-if="showDocManager" class="modal-overlay" @click.self="closeDocManager">
      <div class="modal">
        <div class="modal-header">
          <h3>管理文档 — {{ managingKb?.name }}</h3>
          <button @click="closeDocManager" class="close-btn">✕</button>
        </div>
        <div class="modal-body">
          <div class="doc-checkbox-list">
            <label v-for="doc in allDocs" :key="doc.id" class="doc-row">
              <input
                type="checkbox"
                :value="doc.id"
                v-model="selectedDocIds"
              />
              <span class="doc-title">{{ doc.title }}</span>
              <span class="doc-type">{{ doc.doc_type }}</span>
              <span :class="['status', doc.status]">
                {{ statusMap[doc.status] || doc.status }}
              </span>
            </label>
            <div v-if="allDocs.length === 0" class="empty-hint">暂无文档，请先在「文档管理」上传</div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="saveDocManager" :disabled="savingDocs" class="btn-primary">
            {{ savingDocs ? '保存中...' : '保存关联' }}
          </button>
          <button @click="closeDocManager" class="btn-cancel">取消</button>
          <span v-if="docMsg" :class="['msg', docMsgType]">{{ docMsg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  listKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase,
} from '../../api/index.js'
import api from '../../api/index.js'

const kbs = ref([])
const showCreate = ref(false)
const editing = ref(null)
const formName = ref('')
const formDesc = ref('')
const saving = ref(false)

// Document manager
const showDocManager = ref(false)
const managingKb = ref(null)
const allDocs = ref([])
const selectedDocIds = ref([])
const savingDocs = ref(false)
const docMsg = ref('')
const docMsgType = ref('')
const statusMap = { pending: '待处理', processing: '处理中', ready: '就绪', failed: '失败' }

async function load() {
  const res = await listKnowledgeBases()
  kbs.value = res.data
}

function edit(kb) {
  editing.value = kb.id
  formName.value = kb.name
  formDesc.value = kb.description || ''
  showCreate.value = true
}

function cancelForm() {
  showCreate.value = false
  editing.value = null
  formName.value = ''
  formDesc.value = ''
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await updateKnowledgeBase(editing.value, { name: formName.value, description: formDesc.value })
    } else {
      await createKnowledgeBase({ name: formName.value, description: formDesc.value })
    }
    cancelForm()
    await load()
  } catch (err) {
    alert(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function remove(id) {
  if (!confirm('确定删除此知识库？关联的文档不会删除。')) return
  await deleteKnowledgeBase(id)
  await load()
}

// Document manager
async function openDocManager(kb) {
  managingKb.value = kb
  selectedDocIds.value = []
  docMsg.value = ''

  // Load all docs
  const docRes = await api.get('/documents', { params: { limit: 200 } })
  allDocs.value = docRes.data.items

  // Load current KB doc IDs
  const kbDocRes = await api.get(`/knowledge-bases/${kb.id}/documents`)
  selectedDocIds.value = kbDocRes.data

  showDocManager.value = true
}

function closeDocManager() {
  showDocManager.value = false
  managingKb.value = null
  allDocs.value = []
  selectedDocIds.value = []
  docMsg.value = ''
}

async function saveDocManager() {
  savingDocs.value = true
  docMsg.value = ''
  try {
    await api.put(`/knowledge-bases/${managingKb.value.id}/documents`, {
      document_ids: selectedDocIds.value,
    })
    docMsg.value = '保存成功'
    docMsgType.value = 'success'
    // Update doc count
    const kbRes = await listKnowledgeBases()
    kbs.value = kbRes.data
  } catch (err) {
    docMsg.value = err.response?.data?.detail || '保存失败'
    docMsgType.value = 'error'
  } finally {
    savingDocs.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.header h2 { font-size: 16px; }
.kb-form { display: flex; gap: 8px; padding: 12px; background: #f9f9f9; border-radius: 6px; margin-bottom: 12px; flex-wrap: wrap; }
.kb-form input { padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; flex: 1; min-width: 120px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
th { background: #f5f5f5; font-weight: 600; }
.empty { text-align: center; color: #999; padding: 40px; }
.btn-primary { padding: 8px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { background: #ccc; }
.btn-cancel { padding: 8px 16px; background: #fff; border: 1px solid #d0d0d0; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-edit { padding: 4px 10px; background: #fff; border: 1px solid #d0d0d0; border-radius: 3px; cursor: pointer; font-size: 12px; margin-right: 4px; }
.btn-manage { padding: 4px 10px; background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; border-radius: 3px; cursor: pointer; font-size: 12px; margin-right: 4px; }
.btn-danger { padding: 4px 10px; background: #ef5350; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 12px; }
.msg { font-size: 13px; }
.msg.success { color: #2e7d32; }
.msg.error { color: #c62828; }

/* Modal */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: #fff; border-radius: 10px; width: 600px; max-height: 80vh;
  display: flex; flex-direction: column; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid #e0e0e0;
}
.modal-header h3 { font-size: 16px; margin: 0; }
.close-btn { background: none; border: none; font-size: 18px; cursor: pointer; color: #888; }
.modal-body {
  padding: 16px 20px; overflow-y: auto; flex: 1; max-height: 50vh;
}
.modal-footer {
  padding: 12px 20px; border-top: 1px solid #e0e0e0; display: flex; gap: 8px; align-items: center;
}
.doc-checkbox-list { display: flex; flex-direction: column; gap: 6px; }
.doc-row {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border: 1px solid #eee; border-radius: 4px; cursor: pointer; font-size: 14px;
}
.doc-row:hover { background: #f9f9f9; }
.doc-title { flex: 1; }
.doc-type { font-size: 12px; color: #888; }
.status { padding: 1px 6px; border-radius: 3px; font-size: 11px; }
.status.ready { background: #e8f5e9; color: #2e7d32; }
.status.failed { background: #ffebee; color: #c62828; }
.status.processing { background: #fff3e0; color: #ef6c00; }
.status.pending { background: #f5f5f5; color: #666; }
.empty-hint { text-align: center; color: #999; padding: 24px; font-size: 14px; }
</style>