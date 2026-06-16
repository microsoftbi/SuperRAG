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
            <button @click="remove(kb.id)" class="btn-danger">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">暂无知识库</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from '../../api/index.js'

const kbs = ref([])
const showCreate = ref(false)
const editing = ref(null)
const formName = ref('')
const formDesc = ref('')
const saving = ref(false)

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
.btn-danger { padding: 4px 10px; background: #ef5350; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 12px; }
</style>