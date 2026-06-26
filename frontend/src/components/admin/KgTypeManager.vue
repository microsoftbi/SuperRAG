<template>
  <div class="type-mgr">
    <div class="sub-tabs">
      <button
        v-for="t in subTabs"
        :key="t.key"
        :class="['sub-tab', { active: activeSubTab === t.key }]"
        @click="activeSubTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 节点类型管理 -->
    <div v-if="activeSubTab === 'node'" class="type-panel">
      <div class="panel-header">
        <span class="count">共 {{ nodeTypes.length }} 个节点类型</span>
        <button class="btn-primary btn-sm" @click="startAddNodeType">+ 新增节点类型</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th class="col-name">名称</th>
              <th class="col-color">颜色</th>
              <th class="col-label">显示标签</th>
              <th class="col-desc">描述</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="nt in nodeTypes" :key="nt.name" :class="{ editing: editingNodeType === nt.name }">
              <!-- 编辑态/查看态 -->
              <template v-if="editingNodeType === nt.name">
                <td class="col-name"><code>{{ nt.name }}</code></td>
                <td class="col-color">
                  <div class="color-picker-wrap">
                    <input type="color" v-model="editForm.nodeColor" class="color-input" />
                    <span class="color-hex">{{ editForm.nodeColor }}</span>
                  </div>
                </td>
                <td><input v-model="editForm.nodeLabel" class="edit-input" /></td>
                <td><input v-model="editForm.nodeDesc" class="edit-input" /></td>
                <td class="col-actions">
                  <button class="action save" @click="saveNodeType(nt.name)">保存</button>
                  <button class="action cancel" @click="cancelEditNodeType">取消</button>
                </td>
              </template>
              <template v-else>
                <td class="col-name"><code>{{ nt.name }}</code></td>
                <td class="col-color">
                  <span class="color-dot" :style="{ background: nt.color }"></span>
                  <span class="color-hex">{{ nt.color }}</span>
                </td>
                <td>{{ nt.label }}</td>
                <td class="col-desc">{{ nt.description || '-' }}</td>
                <td class="col-actions">
                  <button class="action edit" @click="startEditNodeType(nt)">✏️</button>
                  <button class="action delete" @click="confirmDeleteNodeType(nt)" :disabled="deleting === nt.name">
                    🗑️
                  </button>
                </td>
              </template>
            </tr>
            <!-- 新增行 -->
            <tr v-if="addingNodeType" class="editing">
              <td class="col-name">
                <input v-model="addForm.nodeName" placeholder="内部名称" class="edit-input" />
                <div v-if="addError" class="add-error">{{ addError }}</div>
              </td>
              <td class="col-color">
                <div class="color-picker-wrap">
                  <input type="color" v-model="addForm.nodeColor" class="color-input" />
                  <span class="color-hex">{{ addForm.nodeColor }}</span>
                </div>
              </td>
              <td><input v-model="addForm.nodeLabel" placeholder="显示标签" class="edit-input" /></td>
              <td><input v-model="addForm.nodeDesc" placeholder="描述" class="edit-input" /></td>
              <td class="col-actions">
                <button class="action save" @click="addNodeType" :disabled="saving">保存</button>
                <button class="action cancel" @click="cancelAddNodeType">取消</button>
              </td>
            </tr>
            <tr v-if="!nodeTypes.length && !addingNodeType">
              <td colspan="5" class="empty">暂无节点类型定义</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 关系类型管理 -->
    <div v-if="activeSubTab === 'rel'" class="type-panel">
      <div class="panel-header">
        <span class="count">共 {{ relTypes.length }} 个关系类型</span>
        <button class="btn-primary btn-sm" @click="startAddRelType">+ 新增关系类型</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th class="col-name">名称</th>
              <th class="col-color">颜色</th>
              <th class="col-label">显示标签</th>
              <th class="col-desc">描述</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rt in relTypes" :key="rt.name" :class="{ editing: editingRelType === rt.name }">
              <template v-if="editingRelType === rt.name">
                <td class="col-name"><code>{{ rt.name }}</code></td>
                <td class="col-color">
                  <div class="color-picker-wrap">
                    <input type="color" v-model="editForm.relColor" class="color-input" />
                    <span class="color-hex">{{ editForm.relColor }}</span>
                  </div>
                </td>
                <td><input v-model="editForm.relLabel" class="edit-input" /></td>
                <td><input v-model="editForm.relDesc" class="edit-input" /></td>
                <td class="col-actions">
                  <button class="action save" @click="saveRelType(rt.name)">保存</button>
                  <button class="action cancel" @click="cancelEditRelType">取消</button>
                </td>
              </template>
              <template v-else>
                <td class="col-name"><code>{{ rt.name }}</code></td>
                <td class="col-color">
                  <span class="color-dot" :style="{ background: rt.color }"></span>
                  <span class="color-hex">{{ rt.color }}</span>
                </td>
                <td>{{ rt.label }}</td>
                <td class="col-desc">{{ rt.description || '-' }}</td>
                <td class="col-actions">
                  <button class="action edit" @click="startEditRelType(rt)">✏️</button>
                  <button class="action delete" @click="confirmDeleteRelType(rt)" :disabled="deleting === rt.name">
                    🗑️
                  </button>
                </td>
              </template>
            </tr>
            <!-- 新增行 -->
            <tr v-if="addingRelType" class="editing">
              <td class="col-name">
                <input v-model="addForm.relName" placeholder="内部名称" class="edit-input" />
                <div v-if="addError" class="add-error">{{ addError }}</div>
              </td>
              <td class="col-color">
                <div class="color-picker-wrap">
                  <input type="color" v-model="addForm.relColor" class="color-input" />
                  <span class="color-hex">{{ addForm.relColor }}</span>
                </div>
              </td>
              <td><input v-model="addForm.relLabel" placeholder="显示标签" class="edit-input" /></td>
              <td><input v-model="addForm.relDesc" placeholder="描述" class="edit-input" /></td>
              <td class="col-actions">
                <button class="action save" @click="addRelType" :disabled="saving">保存</button>
                <button class="action cancel" @click="cancelAddRelType">取消</button>
              </td>
            </tr>
            <tr v-if="!relTypes.length && !addingRelType">
              <td colspan="5" class="empty">暂无关系类型定义</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  getNodeTypes, createNodeType, updateNodeType, deleteNodeType,
  getRelationTypes, createRelationType, updateRelationType, deleteRelationType,
} from '../../api/index.js'

const subTabs = [
  { key: 'node', label: '📦 节点类型' },
  { key: 'rel', label: '🔗 关系类型' },
]
const activeSubTab = ref('node')

// 数据
const nodeTypes = ref([])
const relTypes = ref([])
const saving = ref(false)
const deleting = ref('')
const addError = ref('')

// 编辑态
const editingNodeType = ref('')
const editingRelType = ref('')
const editForm = ref({
  nodeColor: '#607d8b', nodeLabel: '', nodeDesc: '',
  relColor: '#5e35b1', relLabel: '', relDesc: '',
})

// 新增态
const addingNodeType = ref(false)
const addingRelType = ref(false)
const addForm = ref({
  nodeName: '', nodeColor: '#607d8b', nodeLabel: '', nodeDesc: '',
  relName: '', relColor: '#5e35b1', relLabel: '', relDesc: '',
})

async function loadData() {
  try {
    const [nodeRes, relRes] = await Promise.all([getNodeTypes(), getRelationTypes()])
    nodeTypes.value = nodeRes.data || []
    relTypes.value = relRes.data || []
  } catch (e) {
    console.warn('Failed to load type data:', e)
  }
}

// ── 节点类型 CRUD ──

function startAddNodeType() {
  addingNodeType.value = true
  addError.value = ''
  addForm.value = { nodeName: '', nodeColor: '#607d8b', nodeLabel: '', nodeDesc: '' }
}

function cancelAddNodeType() {
  addingNodeType.value = false
  addError.value = ''
}

async function addNodeType() {
  const name = addForm.value.nodeName.trim()
  if (!name) { addError.value = '名称不能为空'; return }
  if (!addForm.value.nodeLabel.trim()) { addError.value = '显示标签不能为空'; return }
  saving.value = true
  addError.value = ''
  try {
    await createNodeType({
      name,
      label: addForm.value.nodeLabel.trim(),
      color: addForm.value.nodeColor,
      description: addForm.value.nodeDesc.trim(),
    })
    addingNodeType.value = false
    await loadData()
  } catch (e) {
    addError.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

function startEditNodeType(nt) {
  editingNodeType.value = nt.name
  editForm.value.nodeColor = nt.color || '#607d8b'
  editForm.value.nodeLabel = nt.label || ''
  editForm.value.nodeDesc = nt.description || ''
}

function cancelEditNodeType() {
  editingNodeType.value = ''
}

async function saveNodeType(name) {
  saving.value = true
  try {
    await updateNodeType(name, {
      label: editForm.value.nodeLabel.trim(),
      color: editForm.value.nodeColor,
      description: editForm.value.nodeDesc.trim(),
    })
    editingNodeType.value = ''
    await loadData()
  } catch (e) {
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function confirmDeleteNodeType(nt) {
  if (!confirm(`确定删除节点类型 "${nt.name} (${nt.label})"？\n如果该类型已被 Neo4j 中的节点使用，删除将被拒绝。`)) return
  deleting.value = nt.name
  try {
    await deleteNodeType(nt.name)
    await loadData()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    deleting.value = ''
  }
}

// ── 关系类型 CRUD ──

function startAddRelType() {
  addingRelType.value = true
  addError.value = ''
  addForm.value = { relName: '', relColor: '#5e35b1', relLabel: '', relDesc: '' }
}

function cancelAddRelType() {
  addingRelType.value = false
  addError.value = ''
}

async function addRelType() {
  const name = addForm.value.relName.trim()
  if (!name) { addError.value = '名称不能为空'; return }
  if (!addForm.value.relLabel.trim()) { addError.value = '显示标签不能为空'; return }
  saving.value = true
  addError.value = ''
  try {
    await createRelationType({
      name,
      label: addForm.value.relLabel.trim(),
      color: addForm.value.relColor,
      description: addForm.value.relDesc.trim(),
    })
    addingRelType.value = false
    await loadData()
  } catch (e) {
    addError.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

function startEditRelType(rt) {
  editingRelType.value = rt.name
  editForm.value.relColor = rt.color || '#5e35b1'
  editForm.value.relLabel = rt.label || ''
  editForm.value.relDesc = rt.description || ''
}

function cancelEditRelType() {
  editingRelType.value = ''
}

async function saveRelType(name) {
  saving.value = true
  try {
    await updateRelationType(name, {
      label: editForm.value.relLabel.trim(),
      color: editForm.value.relColor,
      description: editForm.value.relDesc.trim(),
    })
    editingRelType.value = ''
    await loadData()
  } catch (e) {
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function confirmDeleteRelType(rt) {
  if (!confirm(`确定删除关系类型 "${rt.name} (${rt.label})"？\n如果该类型已被 Neo4j 中的关系使用，删除将被拒绝。`)) return
  deleting.value = rt.name
  try {
    await deleteRelationType(rt.name)
    await loadData()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    deleting.value = ''
  }
}

onMounted(loadData)
</script>

<style scoped>
.type-mgr { display: flex; flex-direction: column; gap: 12px; }
.sub-tabs {
  display: flex; gap: 0; border-bottom: 1px solid var(--border-default);
}
.sub-tab {
  background: none; border: none; padding: 7px 14px;
  font-size: 13px; cursor: pointer; color: var(--text-secondary);
  border-bottom: 2px solid transparent;
}
.sub-tab.active {
  color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 600;
}
.sub-tab:hover:not(.active) { color: var(--text-primary); }

.type-panel { display: flex; flex-direction: column; gap: 8px; }
.panel-header {
  display: flex; align-items: center; gap: 12px;
}
.count { font-size: 12px; color: var(--text-tertiary); }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-primary {
  background: var(--color-primary); color: var(--text-inverse);
  border: none; border-radius: 4px; cursor: pointer; margin-left: auto;
}
.btn-primary:hover { background: var(--color-primary-hover); }

.table-scroll {
  max-height: 600px; overflow: auto;
  border: 1px solid var(--border-default); border-radius: 8px;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { position: sticky; top: 0; z-index: 1; background: var(--table-header-bg); }
th {
  font-weight: 600; color: var(--text-primary); padding: 8px 10px;
  border-bottom: 2px solid var(--table-header-border); text-align: left; font-size: 12px;
}
td {
  padding: 8px 10px; border-bottom: 1px solid var(--border-light);
  color: var(--text-primary); vertical-align: middle;
}
tbody tr:nth-child(even) td { background: var(--table-row-alt); }
tbody tr:hover td { background: var(--table-row-hover); }
tr.editing td { background: var(--color-primary-light); }
.col-name { width: 140px; }
.col-name code { font-size: 12px; }
.col-color { width: 140px; }
.col-desc { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-actions { width: 100px; text-align: right; white-space: nowrap; }
.empty { text-align: center; color: var(--text-tertiary); padding: 40px; }

.color-dot {
  display: inline-block; width: 14px; height: 14px;
  border-radius: 50%; vertical-align: middle;
  border: 1px solid var(--border-light);
}
.color-hex { font-size: 11px; color: var(--text-tertiary); margin-left: 4px; }
.color-picker-wrap { display: flex; align-items: center; gap: 6px; }
.color-input {
  width: 30px; height: 26px; border: 1px solid var(--border-input);
  border-radius: 4px; padding: 1px; cursor: pointer;
  background: none;
}

.edit-input {
  width: 100%; padding: 4px 6px; font-size: 12px;
  border: 1px solid var(--color-primary-border); border-radius: 3px; outline: none;
  background: var(--bg-card); color: var(--text-primary);
  box-sizing: border-box;
}

.action {
  border: none; border-radius: 3px; cursor: pointer; font-size: 12px;
  padding: 3px 8px; margin-left: 4px;
}
.action.save { background: var(--color-success); color: var(--text-inverse); }
.action.save:hover { opacity: 0.9; }
.action.cancel { background: var(--bg-hover); color: var(--text-secondary); }
.action.edit { background: none; border: 1px solid var(--color-primary); color: var(--color-primary); }
.action.edit:hover { background: var(--bg-active); }
.action.delete { background: none; border: 1px solid var(--color-danger); color: var(--color-danger); }
.action.delete:hover { background: var(--color-danger-light); }
.action.delete:disabled { opacity: 0.5; cursor: not-allowed; }

.add-error { color: var(--color-danger); font-size: 11px; margin-top: 2px; }
</style>