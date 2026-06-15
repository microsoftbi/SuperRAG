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
