<template>
  <div class="user-manager">
    <div class="header">
      <h2>用户管理</h2>
      <button @click="showCreate = true" class="btn-primary">+ 新建用户</button>
    </div>

    <table v-if="users.length">
      <thead>
        <tr>
          <th>用户名</th><th>邮箱</th><th>角色</th><th>知识库权限</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.username }}</td>
          <td>{{ u.email }}</td>
          <td><span :class="['role', u.role]">{{ u.role === 'admin' ? '管理员' : '普通用户' }}</span></td>
          <td>
            <div v-if="u.role !== 'admin'" class="kb-badges">
              <span v-for="kb in getUserKbNames(u.id)" :key="kb" class="badge">{{ kb }}</span>
              <button @click="openKbModal(u)" class="btn-edit-sm">分配</button>
            </div>
            <span v-if="u.role === 'admin'" class="all-access">全部</span>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">暂无用户</div>

    <!-- Create User Modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建用户</h3>
          <button @click="showCreate = false" class="close-btn">✕</button>
        </div>
        <div class="modal-body">
          <div class="create-form">
            <div class="field">
              <label>用户名</label>
              <input v-model="formUsername" placeholder="用户名" />
            </div>
            <div class="field">
              <label>邮箱</label>
              <input v-model="formEmail" placeholder="邮箱" />
            </div>
            <div class="field">
              <label>密码</label>
              <input v-model="formPassword" type="password" placeholder="密码（至少6位）" />
            </div>
            <div class="field">
              <label>角色</label>
              <select v-model="formRole">
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </div>
          </div>
          <p v-if="createError" class="error">{{ createError }}</p>
          <p v-if="createSuccess" class="success">{{ createSuccess }}</p>
        </div>
        <div class="modal-footer">
          <button @click="createUser" :disabled="creating" class="btn-primary">
            {{ creating ? '创建中...' : '创建' }}
          </button>
          <button @click="showCreate = false" class="btn-cancel">取消</button>
        </div>
      </div>
    </div>
  <!-- KB Permission Modal -->
    <div v-if="showKbModal" class="modal-overlay" @click.self="closeKbModal">
      <div class="modal">
        <div class="modal-header">
          <h3>知识库权限 — {{ editingUser?.username }}</h3>
          <button @click="closeKbModal" class="close-btn">✕</button>
        </div>
        <div class="modal-body">
          <div class="doc-checkbox-list">
            <label v-for="kb in allKbs" :key="kb.id" class="doc-row">
              <input
                type="checkbox"
                :value="kb.id"
                v-model="editingKbIds"
              />
              <span class="doc-title">{{ kb.name }}</span>
              <span class="doc-type">{{ kb.description || '-' }}</span>
            </label>
            <div v-if="allKbs.length === 0" class="empty-hint">暂无知识库</div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="saveKbPerms" :disabled="savingPerms" class="btn-primary">
            {{ savingPerms ? '保存中...' : '保存权限' }}
          </button>
          <button @click="closeKbModal" class="btn-cancel">取消</button>
          <span v-if="permMsg" :class="['msg', permMsgType]">{{ permMsg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listUsers, listKnowledgeBases, getUserKnowledgeBases, setUserKnowledgeBases } from '../../api/index.js'
import api from '../../api/index.js'

const users = ref([])
const allKbs = ref([])
const userKbMap = ref({})
const editingKbIds = ref([])
const savingPerms = ref(false)

// KB permission modal
const showKbModal = ref(false)
const editingUser = ref(null)
const permMsg = ref('')
const permMsgType = ref('')

// Create user
const showCreate = ref(false)
const formUsername = ref('')
const formEmail = ref('')
const formPassword = ref('')
const formRole = ref('user')
const creating = ref(false)
const createError = ref('')
const createSuccess = ref('')

async function load() {
  const [userRes, kbRes] = await Promise.all([listUsers(), listKnowledgeBases()])
  users.value = userRes.data
  allKbs.value = kbRes.data
  for (const u of users.value) {
    if (u.role === 'user') {
      try {
        const res = await getUserKnowledgeBases(u.id)
        userKbMap.value[u.id] = res.data
      } catch { /* ignore */ }
    }
  }
}

function getUserKbNames(userId) {
  const ids = userKbMap.value[userId] || []
  return allKbs.value.filter(kb => ids.includes(kb.id)).map(kb => kb.name)
}

async function openKbModal(user) {
  editingUser.value = user
  editingKbIds.value = [...(userKbMap.value[user.id] || [])]
  permMsg.value = ''
  showKbModal.value = true
}

async function saveKbPerms() {
  savingPerms.value = true
  permMsg.value = ''
  try {
    await setUserKnowledgeBases(editingUser.value.id, { knowledge_base_ids: editingKbIds.value })
    userKbMap.value[editingUser.value.id] = [...editingKbIds.value]
    permMsg.value = '保存成功'
    permMsgType.value = 'success'
  } catch (err) {
    permMsg.value = err.response?.data?.detail || '保存失败'
    permMsgType.value = 'error'
  } finally {
    savingPerms.value = false
  }
}

function closeKbModal() {
  showKbModal.value = false
  editingUser.value = null
  editingKbIds.value = []
  permMsg.value = ''
}

async function createUser() {
  if (!formUsername.value || !formEmail.value || !formPassword.value) {
    createError.value = '请填写所有字段'
    return
  }
  creating.value = true
  createError.value = ''
  createSuccess.value = ''

  try {
    const res = await api.post('/auth/register', {
      username: formUsername.value,
      email: formEmail.value,
      password: formPassword.value,
    })

    // If created as user but should be admin, update role
    if (formRole.value === 'admin') {
      await api.put(`/users/${res.data.id}/role`, { role: 'admin' })
    }

    createSuccess.value = `用户 ${formUsername.value} 创建成功`
    formUsername.value = ''
    formEmail.value = ''
    formPassword.value = ''
    formRole.value = 'user'
    setTimeout(() => { showCreate.value = false }, 1000)
    await load()
  } catch (err) {
    createError.value = err.response?.data?.detail || '创建失败'
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.user-manager { }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.header h2 { font-size: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border-default); }
th { background: var(--bg-page); font-weight: 600; }
.empty { text-align: center; color: var(--text-tertiary); padding: 40px; }
.role { padding: 2px 8px; border-radius: 3px; font-size: 12px; }
.role.admin { background: var(--bg-active); color: var(--color-primary); }
.role.user { background: var(--bg-page); color: var(--text-secondary); }
.all-access { font-size: 12px; color: var(--text-tertiary); }
.kb-badges { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.badge { padding: 2px 6px; background: var(--color-success-light); color: var(--color-success); border-radius: 3px; font-size: 11px; }
.btn-edit-sm { padding: 2px 8px; background: var(--bg-card); border: 1px solid var(--border-input); border-radius: 3px; cursor: pointer; font-size: 11px; }
.btn-primary { padding: 8px 16px; background: var(--color-primary); color: var(--text-inverse); border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { background: #ccc; }
.btn-cancel { padding: 8px 16px; background: var(--bg-card); border: 1px solid var(--border-input); border-radius: 4px; cursor: pointer; font-size: 13px; }
.error { color: var(--color-danger); font-size: 13px; margin-top: 8px; }
.success { color: var(--color-success); font-size: 13px; margin-top: 8px; }

/* Modal */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: var(--overlay); display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: var(--bg-card); border-radius: 10px; width: 500px; max-height: 80vh;
  display: flex; flex-direction: column; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid var(--border-default);
}
.modal-header h3 { font-size: 16px; margin: 0; }
.close-btn { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-tertiary); }
.modal-body {
  padding: 16px 20px; overflow-y: auto; flex: 1; max-height: 50vh;
}
.modal-footer {
  padding: 12px 20px; border-top: 1px solid var(--border-default); display: flex; gap: 8px; align-items: center;
}
.doc-checkbox-list { display: flex; flex-direction: column; gap: 6px; }
.doc-row {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border: 1px solid #eee; border-radius: 4px; cursor: pointer; font-size: 14px;
}
.doc-row:hover { background: #f9f9f9; }
.doc-title { flex: 1; }
.doc-type { font-size: 12px; color: var(--text-tertiary); }
.empty-hint { text-align: center; color: var(--text-tertiary); padding: 24px; font-size: 14px; }
.msg { font-size: 13px; }
.msg.success { color: var(--color-success); }
.msg.error { color: var(--color-danger); }
.create-form { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.field input, .field select {
  padding: 8px; border: 1px solid var(--border-input); border-radius: 4px; font-size: 14px;
}
</style>