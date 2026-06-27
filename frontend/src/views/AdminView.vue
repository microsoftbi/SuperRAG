<template>
  <div class="admin-page">
    <header class="admin-header">
      <h1>管理后台 <span class="version">v{{ appVersion }}</span></h1>
      <div class="nav">
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换到浅色模式' : '切换到深色模式'">{{ isDark ? '🌙' : '☀️' }}</button>
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
        <div class="doc-tabs">
          <button
            :class="['doc-tab', { active: docFilter === 'vector' }]"
            @click="docFilter = 'vector'; loadDocuments()"
          >向量存储</button>
          <button
            :class="['doc-tab', { active: docFilter === 'graph' }]"
            @click="docFilter = 'graph'; loadDocuments()"
          >图谱存储</button>
          <button
            class="btn-bm25"
            :disabled="bm25Rebuilding"
            @click="handleRebuildBm25"
          >{{ bm25Rebuilding ? '重构中...' : '🔄 BM25 重构' }}</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>标题</th><th>类型</th><th>存储目标</th><th>知识库</th><th>状态</th><th>上传时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in documents" :key="doc.id">
              <td>{{ doc.title }}</td>
              <td>{{ doc.doc_type }}</td>
              <td><span :class="['store-badge', doc.store]">{{ storeLabel(doc.store) }}</span></td>
              <td>
                <div class="kb-badges">
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
              <td class="actions">
                <button v-if="docFilter === 'vector' || doc.store === 'both'" @click="viewChunks(doc)" class="chunk-btn">查看分块</button>
                <button v-if="doc.status === 'failed'" @click="retry(doc.id)" class="retry-btn">重试</button>
                <button @click="remove(doc.id)" class="delete-btn">删除</button>
              </td>
            </tr>
            <tr v-if="documents.length === 0">
              <td colspan="7" class="empty">暂无文档</td>
            </tr>
          </tbody>
        </table>
      </div>
      <LogViewer v-if="activeTab === 'logs'" />
      <SettingsPanel v-if="activeTab === 'settings'" />
      <FeedbackPanel v-if="activeTab === 'feedback'" />
      <KnowledgeBaseManager v-if="activeTab === 'knowledge-bases'" />
      <KnowledgeGraphViewer v-if="activeTab === 'knowledge-graph'" />
      <UserManager v-if="activeTab === 'users'" />
      <Nl2SqlPanel v-if="activeTab === 'nl2sql'" />
    </div>

    <DocumentChunkViewer
      v-if="chunkViewerDoc"
      :document-id="chunkViewerDoc.id"
      :doc-title="chunkViewerDoc.title"
      @close="chunkViewerDoc = null"
    />
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
import KnowledgeGraphViewer from '../components/admin/KnowledgeGraphViewer.vue'
import DocumentChunkViewer from '../components/admin/DocumentChunkViewer.vue'
import Nl2SqlPanel from '../components/admin/Nl2SqlPanel.vue'
import { listDocuments, deleteDocument, reprocessDocument, listKnowledgeBases, rebuildBm25 } from '../api/index.js'
import { getRuntimeConfig } from '../api/index.js'
import { useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme.js'

const router = useRouter()
const { isDark, toggle: toggleTheme } = useTheme()
const appVersion = ref('')

async function loadVersion() {
  try {
    const res = await getRuntimeConfig()
    appVersion.value = res.data?.app_version || ''
  } catch { /* ignore */ }
}

onMounted(loadVersion)

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

const activeTab = ref('dashboard')
const docFilter = ref('vector')
const tabs = [
  { key: 'dashboard', label: '仪表盘' },
  { key: 'docs', label: '文档管理' },
  { key: 'knowledge-bases', label: '知识库' },
  { key: 'knowledge-graph', label: '知识图谱' },
  { key: 'users', label: '用户管理' },
  { key: 'logs', label: '问答日志' },
  { key: 'feedback', label: '用户反馈' },
  { key: 'settings', label: '参数配置' },
{ key: 'nl2sql', label: 'NL2SQL' },
]

const documents = ref([])
const kbMap = ref({})
const chunkViewerDoc = ref(null)
const bm25Rebuilding = ref(false)
const statusMap = { pending: '待处理', processing: '处理中', ready: '就绪', failed: '失败' }

const storeLabels = { vector: '向量', graph: '图谱', both: '全部' }
function storeLabel(s) { return storeLabels[s] || s }

function getKbName(id) {
  return kbMap.value[id] || `ID:${id}`
}

async function loadDocuments() {
  const [docRes, kbRes] = await Promise.all([
    listDocuments({ limit: 100, store: docFilter.value }),
    listKnowledgeBases(),
  ])
  documents.value = docRes.data.items
  for (const kb of kbRes.data) {
    kbMap.value[kb.id] = kb.name
  }
}

function viewChunks(doc) {
  chunkViewerDoc.value = doc
}

async function remove(id) {
  if (!confirm('确定删除此文档？')) return
  await deleteDocument(id)
  await loadDocuments()
}

async function retry(id) {
  try {
    await reprocessDocument(id)
    await loadDocuments()
  } catch (e) {
    alert('重试失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleRebuildBm25() {
  bm25Rebuilding.value = true
  try {
    const res = await rebuildBm25()
    alert('BM25 索引重构完成：' + (res.data?.message || 'ok'))
  } catch (e) {
    alert('BM25 重构失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    bm25Rebuilding.value = false
  }
}

onMounted(loadDocuments)
</script>

<style scoped>
.admin-page { max-width: 1100px; margin: 0 auto; padding: 20px; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.admin-header h1 { font-size: 22px; color: var(--text-primary); }
.version { font-size: 12px; color: var(--text-tertiary); font-weight: 400; margin-left: 6px; }
.admin-header a { color: var(--color-primary); text-decoration: none; font-size: 14px; }
.nav { display: flex; align-items: center; gap: 12px; }
.theme-toggle {
  background: none; border: none; cursor: pointer;
  font-size: 18px; padding: 4px; line-height: 1;
  border-radius: 4px; transition: background 0.2s;
}
.theme-toggle:hover { background: var(--bg-hover); }
.logout-btn {
  padding: 4px 12px; border: 1px solid var(--border-input); border-radius: 4px;
  background: var(--bg-card); cursor: pointer; font-size: 12px; color: var(--text-secondary);
}
.logout-btn:hover { background: var(--bg-hover); }
.tabs { display: flex; gap: 4px; border-bottom: 2px solid var(--border-default); margin-bottom: 20px; }
.tab {
  padding: 8px 20px; border: none; background: none; cursor: pointer;
  font-size: 14px; color: var(--text-secondary); border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 600; }
.admin-content { display: flex; flex-direction: column; gap: 24px; }
.doc-list h2 { font-size: 16px; margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border-default); }
th { background: var(--table-header-bg); font-weight: 600; }
.status { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.status.ready { background: var(--color-success-light); color: var(--color-success); }
.status.failed { background: var(--color-danger-light); color: var(--color-danger); }
.status.processing { background: var(--color-warning-light); color: var(--color-warning); }
.status.pending { background: var(--bg-hover); color: var(--text-secondary); }
.actions { white-space: nowrap; }
.delete-btn { padding: 4px 10px; background: var(--color-danger); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-left: 4px; }
.retry-btn { padding: 4px 10px; background: var(--color-warning); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-left: 4px; }
.retry-btn:hover { opacity: 0.85; }
.chunk-btn { padding: 4px 10px; background: var(--color-primary); color: var(--text-inverse); border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.chunk-btn:hover { background: var(--color-primary-hover); }
.empty { text-align: center; color: var(--text-tertiary); padding: 24px; }
.kb-badges { display: flex; gap: 3px; flex-wrap: wrap; }
.badge { padding: 1px 6px; background: var(--color-primary-light); color: var(--color-primary); border-radius: 3px; font-size: 11px; }
.no-kb { color: var(--text-muted); }

.doc-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border-default);
  align-items: center;
}
.doc-tab {
  padding: 6px 18px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.doc-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}
.btn-bm25 {
  margin-left: auto;
  padding: 4px 12px;
  border: 1px solid var(--border-input);
  border-radius: 4px;
  background: var(--bg-card);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
}
.btn-bm25:hover:not(:disabled) { background: var(--bg-hover); }
.btn-bm25:disabled { opacity: 0.5; cursor: not-allowed; }
.store-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
}
.store-badge.vector { background: var(--color-success-light); color: var(--color-success); }
.store-badge.graph  { background: var(--color-warning-light); color: var(--color-warning); }
.store-badge.both   { background: var(--color-primary-light); color: var(--color-primary); }
</style>