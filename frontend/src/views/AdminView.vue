<template>
  <div class="admin-page">
    <header class="admin-header">
      <h1>管理后台</h1>
      <div class="nav">
        <router-link to="/">返回对话</router-link>
        <button @click="logout" class="logout-btn">退出</button>
      </div>
    </header>
    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>
    <div class="admin-content">
      <DashboardView v-if="activeTab === 'dashboard'" />
      <DocumentUploader v-if="activeTab === 'docs'" @uploaded="loadDocuments" />
      <div v-if="activeTab === 'docs'" class="doc-list">
        <h2>文档列表</h2>
        <table>
          <thead>
            <tr>
              <th>标题</th><th>类型</th><th>知识库</th><th>状态</th><th>上传时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in documents" :key="doc.id">
              <td>{{ doc.title }}</td>
              <td>{{ doc.doc_type }}</td>
              <td>
                <div v-if="editingDocId === doc.id" class="kb-edit-inline">
                  <label v-for="kb in allKbs" :key="kb.id" class="kb-opt">
                    <input type="checkbox" :value="kb.id" v-model="editingKbIds" />
                    {{ kb.name }}
                  </label>
                  <div class="kb-edit-actions">
                    <button @click="saveKbEdit(doc.id)" class="btn-xs-primary">保存</button>
                    <button @click="editingDocId = null" class="btn-xs">取消</button>
                  </div>
                </div>
                <div v-else class="kb-badges">
                  <span v-for="kid in (doc.knowledge_base_ids || [])" :key="kid" class="badge">
                    {{ getKbName(kid) }}
                  </span>
                  <span v-if="!(doc.knowledge_base_ids || []).length" class="no-kb">-</span>
                </div>
              </td>
              <td>
                <span :class="['status', doc.status]">
                  {{ statusMap[doc.status] || doc.status }}
                </span>
              </td>
              <td>{{ new Date(doc.created_at).toLocaleString() }}</td>
              <td>
                <button @click="startKbEdit(doc)" class="edit-btn">编辑知识库</button>
                <button @click="remove(doc.id)" class="delete-btn">删除</button>
              </td>
            </tr>
            <tr v-if="documents.length === 0">
              <td colspan="6" class="empty">暂无文档</td>
            </tr>
          </tbody>
        </table>
      </div>
      <LogViewer v-if="activeTab === 'logs'" />
      <SettingsPanel v-if="activeTab === 'settings'" />
      <FeedbackPanel v-if="activeTab === 'feedback'" />
      <KnowledgeBaseManager v-if="activeTab === 'knowledge-bases'" />
      <UserManager v-if="activeTab === 'users'" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DashboardView from '../components/admin/DashboardView.vue'
import DocumentUploader from '../components/admin/DocumentUploader.vue'
import LogViewer from '../components/admin/LogViewer.vue'
import SettingsPanel from '../components/admin/SettingsPanel.vue'
import FeedbackPanel from '../components/admin/FeedbackPanel.vue'
import KnowledgeBaseManager from '../components/admin/KnowledgeBaseManager.vue'
import UserManager from '../components/admin/UserManager.vue'
import { listDocuments, deleteDocument, listKnowledgeBases } from '../api/index.js'
import { useRouter } from 'vue-router'
import api from '../api/index.js'

const router = useRouter()

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

const activeTab = ref('dashboard')
const tabs = [
  { key: 'dashboard', label: '仪表盘' },
  { key: 'docs', label: '文档管理' },
  { key: 'knowledge-bases', label: '知识库' },
  { key: 'users', label: '用户管理' },
  { key: 'logs', label: '问答日志' },
  { key: 'feedback', label: '用户反馈' },
  { key: 'settings', label: '参数配置' },
]

const documents = ref([])
const kbMap = ref({})
const statusMap = { pending: '待处理', processing: '处理中', ready: '就绪', failed: '失败' }

const allKbs = ref([])
const editingDocId = ref(null)
const editingKbIds = ref([])

function getKbName(id) {
  return kbMap.value[id] || `ID:${id}`
}

function startKbEdit(doc) {
  editingDocId.value = doc.id
  editingKbIds.value = [...(doc.knowledge_base_ids || [])]
}

async function saveKbEdit(docId) {
  try {
    await api.put(`/documents/${docId}/knowledge-bases`, { knowledge_base_ids: editingKbIds.value })
    editingDocId.value = null
    await loadDocuments()
  } catch (err) {
    alert(err.response?.data?.detail || '保存失败')
  }
}

async function loadDocuments() {
  const [docRes, kbRes] = await Promise.all([
    listDocuments({ limit: 100 }),
    listKnowledgeBases(),
  ])
  documents.value = docRes.data.items
  allKbs.value = kbRes.data
  for (const kb of kbRes.data) {
    kbMap.value[kb.id] = kb.name
  }
}

async function remove(id) {
  if (!confirm('确定删除此文档？')) return
  await deleteDocument(id)
  await loadDocuments()
}

onMounted(loadDocuments)
</script>

<style scoped>
.admin-page { max-width: 1100px; margin: 0 auto; padding: 20px; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.admin-header h1 { font-size: 22px; }
.admin-header a { color: #1976d2; text-decoration: none; font-size: 14px; }
.nav { display: flex; align-items: center; gap: 12px; }
.logout-btn {
  padding: 4px 12px; border: 1px solid #d0d0d0; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 12px; color: #666;
}
.logout-btn:hover { background: #f5f5f5; }
.tabs { display: flex; gap: 4px; border-bottom: 2px solid #e0e0e0; margin-bottom: 20px; }
.tab {
  padding: 8px 20px; border: none; background: none; cursor: pointer;
  font-size: 14px; color: #666; border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.tab.active { color: #1976d2; border-bottom-color: #1976d2; font-weight: 600; }
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
.delete-btn { padding: 4px 12px; background: #ef5350; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-left: 4px; }
.edit-btn { padding: 4px 10px; background: #fff; border: 1px solid #d0d0d0; border-radius: 4px; cursor: pointer; font-size: 12px; }
.edit-btn:hover { background: #f5f5f5; }
.empty { text-align: center; color: #999; padding: 24px; }
.kb-badges { display: flex; gap: 3px; flex-wrap: wrap; }
.badge { padding: 1px 6px; background: #e3f2fd; color: #1565c0; border-radius: 3px; font-size: 11px; }
.no-kb { color: #ccc; }
.kb-edit-inline { display: flex; flex-direction: column; gap: 4px; }
.kb-opt { font-size: 12px; display: flex; align-items: center; gap: 3px; }
.kb-edit-actions { display: flex; gap: 4px; margin-top: 4px; }
.btn-xs-primary { padding: 3px 8px; background: #1976d2; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 11px; }
.btn-xs { padding: 3px 8px; background: #fff; border: 1px solid #d0d0d0; border-radius: 3px; cursor: pointer; font-size: 11px; }
</style>