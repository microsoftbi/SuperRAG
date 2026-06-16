<template>
  <div class="user-manager">
    <h2>用户管理</h2>
    <table v-if="users.length">
      <thead>
        <tr>
          <th>用户名</th><th>邮箱</th><th>角色</th><th>知识库权限</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.username }}</td>
          <td>{{ u.email }}</td>
          <td><span :class="['role', u.role]">{{ u.role === 'admin' ? '管理员' : '普通用户' }}</span></td>
          <td>
            <div v-if="editingUserId === u.id" class="kb-select">
              <label v-for="kb in allKbs" :key="kb.id" class="kb-option">
                <input type="checkbox" :value="kb.id" v-model="editingKbIds" />
                {{ kb.name }}
              </label>
              <button @click="saveKbPerms(u.id)" :disabled="savingPerms" class="btn-primary">保存</button>
              <button @click="editingUserId = null" class="btn-cancel">取消</button>
            </div>
            <button v-else-if="u.role !== 'admin'" @click="startEdit(u)" class="btn-edit">分配知识库</button>
            <span v-else class="all-access">全部</span>
          </td>
          <td>
            <span v-if="u.role === 'user'" class="kb-badges">
              <span v-for="kb in getUserKbNames(u.id)" :key="kb" class="badge">{{ kb }}</span>
            </span>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">暂无用户</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listUsers, listKnowledgeBases, getUserKnowledgeBases, setUserKnowledgeBases } from '../../api/index.js'

const users = ref([])
const allKbs = ref([])
const userKbMap = ref({})
const editingUserId = ref(null)
const editingKbIds = ref([])
const savingPerms = ref(false)

async function load() {
  const [userRes, kbRes] = await Promise.all([listUsers(), listKnowledgeBases()])
  users.value = userRes.data
  allKbs.value = kbRes.data
  for (const u of users.value) {
    if (u.role === 'user') {
      const res = await getUserKnowledgeBases(u.id)
      userKbMap.value[u.id] = res.data
    }
  }
}

function getUserKbNames(userId) {
  const ids = userKbMap.value[userId] || []
  return allKbs.value.filter(kb => ids.includes(kb.id)).map(kb => kb.name)
}

async function startEdit(user) {
  editingUserId.value = user.id
  editingKbIds.value = [...(userKbMap.value[user.id] || [])]
}

async function saveKbPerms(userId) {
  savingPerms.value = true
  try {
    await setUserKnowledgeBases(userId, { knowledge_base_ids: editingKbIds.value })
    userKbMap.value[userId] = [...editingKbIds.value]
    editingUserId.value = null
  } catch (err) {
    alert(err.response?.data?.detail || '保存失败')
  } finally {
    savingPerms.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.user-manager { }
.user-manager h2 { font-size: 16px; margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
th { background: #f5f5f5; font-weight: 600; }
.empty { text-align: center; color: #999; padding: 40px; }
.role { padding: 2px 8px; border-radius: 3px; font-size: 12px; }
.role.admin { background: #e3f2fd; color: #1565c0; }
.role.user { background: #f5f5f5; color: #666; }
.kb-select { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.kb-option { font-size: 13px; display: flex; align-items: center; gap: 3px; }
.kb-option input { margin: 0; }
.all-access { font-size: 12px; color: #888; }
.btn-edit { padding: 4px 10px; background: #fff; border: 1px solid #d0d0d0; border-radius: 3px; cursor: pointer; font-size: 12px; }
.btn-primary { padding: 4px 10px; background: #1976d2; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 12px; }
.btn-primary:disabled { background: #ccc; }
.btn-cancel { padding: 4px 10px; background: #fff; border: 1px solid #d0d0d0; border-radius: 3px; cursor: pointer; font-size: 12px; }
.kb-badges { display: flex; gap: 4px; flex-wrap: wrap; }
.badge { padding: 2px 6px; background: #e8f5e9; color: #2e7d32; border-radius: 3px; font-size: 11px; }
</style>