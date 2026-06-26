<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <div class="dialog-header">
        <span>{{ isEdit ? '修改关系类型' : '新建关系' }}</span>
        <button class="close" @click="$emit('close')">✕</button>
      </div>
      <div class="dialog-body">
        <div class="form-row">
          <label>源实体 *</label>
          <input
            v-model="form.source"
            type="text"
            placeholder="输入名称..."
            list="kg-node-options"
            :disabled="isEdit"
          />
        </div>
        <div class="form-row">
          <label>目标实体 *</label>
          <input
            v-model="form.target"
            type="text"
            placeholder="输入名称..."
            list="kg-node-options"
            :disabled="isEdit"
          />
        </div>
        <datalist id="kg-node-options">
          <option v-for="n in nodes" :key="n.id" :value="n.name" />
        </datalist>
        <div class="form-row" ref="typeRowRef">
          <label>{{ isEdit ? '新关系类型 *' : '关系类型 *' }}</label>
          <div class="type-select-wrapper">
            <input
              v-model="form.type"
              type="text"
              placeholder="选择或输入关系类型..."
              @focus="showDropdown = true"
              @input="showDropdown = true"
              @keydown.escape="showDropdown = false"
              @keydown.enter="showDropdown = false"
            />
            <div v-if="showDropdown" class="type-dropdown">
              <div
                v-for="t in filteredRelTypes"
                :key="t.name"
                class="type-option"
                @mousedown.prevent="selectType(t.name)"
              >
                <span class="type-dot" :style="{ background: t.color }"></span>
                <span class="type-label">{{ t.label || t.name }}</span>
                <span class="type-name">({{ t.name }})</span>
              </div>
              <div v-if="form.type && !allRelTypeNames.includes(form.type)" class="type-option custom">
                ✏️ 自定义 "{{ form.type }}"（需先在类型管理中注册）
              </div>
              <div v-if="filteredRelTypes.length === 0 && (!form.type || allRelTypeNames.includes(form.type))" class="type-option empty">
                {{ loadingTypes ? '加载中...' : '暂无关系类型，请先在「类型管理」中创建' }}
              </div>
            </div>
          </div>
        </div>
        <div v-if="warningMsg" class="warning">⚠️ {{ warningMsg }}</div>
      </div>
      <div class="dialog-footer">
        <button class="btn-secondary" @click="$emit('close')">取消</button>
        <button class="btn-primary" :disabled="!canSave || saving" @click="save">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { createRelationship, updateRelationship, getRelationTypes } from '../../api/index.js'

const props = defineProps({
  edge: { type: Object, default: null },
  nodes: { type: Array, default: () => [] },
  existingRelTypes: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.edge)

const form = ref({
  source: '',
  target: '',
  type: '',
})
const oldType = ref('')
const saving = ref(false)
const showDropdown = ref(false)
const loadingTypes = ref(false)
const allRelTypes = ref([])
const typeRowRef = ref(null)

const allRelTypeNames = computed(() => allRelTypes.value.map(t => t.name))

const filteredRelTypes = computed(() => {
  const q = form.value.type.trim().toLowerCase()
  if (!q) return allRelTypes.value
  return allRelTypes.value.filter(t =>
    t.name.toLowerCase().includes(q) ||
    (t.label && t.label.toLowerCase().includes(q))
  )
})

const canSave = computed(() => {
  if (!form.value.source.trim() || !form.value.target.trim() || !form.value.type.trim()) {
    return false
  }
  if (form.value.source.trim() === form.value.target.trim()) return false
  if (isEdit.value && form.value.type.trim() === oldType.value) return false
  return true
})

const warningMsg = computed(() => {
  if (form.value.source && form.value.target && form.value.source === form.value.target) {
    return '源和目标不能相同'
  }
  const names = new Set(props.nodes.map(n => n.name))
  if (form.value.source && !names.has(form.value.source.trim())) {
    return `源实体 "${form.value.source}" 不在图谱中，保存时会自动创建`
  }
  if (form.value.target && !names.has(form.value.target.trim())) {
    return `目标实体 "${form.value.target}" 不在图谱中，保存时会自动创建`
  }
  return ''
})

function selectType(name) {
  form.value.type = name
  showDropdown.value = false
}

function onDocumentClick(e) {
  if (typeRowRef.value && !typeRowRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

async function loadRelTypes() {
  loadingTypes.value = true
  try {
    const res = await getRelationTypes()
    allRelTypes.value = (res.data || []).map(t => ({
      name: t.name,
      label: t.label || t.name,
      color: t.color || '#5e35b1',
    }))
  } catch {
    allRelTypes.value = []
  } finally {
    loadingTypes.value = false
  }
}

async function save() {
  saving.value = true
  try {
    if (isEdit.value) {
      await updateRelationship({
        source: form.value.source.trim(),
        target: form.value.target.trim(),
        old_type: oldType.value,
        new_type: form.value.type.trim(),
      })
    } else {
      await createRelationship({
        source: form.value.source.trim(),
        target: form.value.target.trim(),
        type: form.value.type.trim(),
      })
    }
    emit('saved')
  } catch (e) {
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (props.edge) {
    form.value.source = props.edge.sourceName || ''
    form.value.target = props.edge.targetName || ''
    form.value.type = props.edge.type || ''
    oldType.value = props.edge.type || ''
  }
  await loadRelTypes()
  document.addEventListener('click', onDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: var(--overlay);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.dialog {
  background: var(--bg-card); border-radius: 8px; width: 440px; max-width: 90vw;
  display: flex; flex-direction: column;
}
.dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--border-light);
  font-size: 14px; font-weight: 600;
}
.close {
  background: none; border: none; cursor: pointer;
  font-size: 16px; color: var(--text-tertiary); padding: 0 4px;
}
.dialog-body { padding: 16px; }
.form-row { margin-bottom: 14px; }
.form-row label {
  display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 5px; font-weight: 500;
}
.form-row input {
  width: 100%; padding: 8px; font-size: 13px;
  border: 1px solid var(--border-input); border-radius: 4px; outline: none; box-sizing: border-box;
  background: var(--bg-card); color: var(--text-primary);
}
.form-row input:disabled { background: var(--bg-page); color: var(--text-tertiary); }
.warning {
  margin-top: 4px; font-size: 11px; color: var(--color-warning);
  background: var(--color-warning-light); padding: 4px 8px; border-radius: 3px;
}
.dialog-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px; border-top: 1px solid var(--border-light); background: var(--bg-surface);
}
.btn-primary, .btn-secondary {
  padding: 6px 16px; font-size: 13px; border-radius: 4px;
  cursor: pointer; border: 1px solid;
}
.btn-primary { background: var(--color-primary); color: var(--text-inverse); border-color: var(--color-primary); }
.btn-primary:disabled { background: var(--text-muted); border-color: var(--text-muted); cursor: not-allowed; }
.btn-secondary { background: var(--bg-card); color: var(--text-secondary); border-color: var(--border-input); }
.btn-secondary:hover { background: var(--bg-hover); }

/* ── Type dropdown ── */
.type-select-wrapper { position: relative; }
.type-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 10;
  background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 4px; max-height: 200px; overflow-y: auto;
  box-shadow: var(--shadow-sm); margin-top: 2px;
}
.type-option {
  padding: 7px 10px; font-size: 13px; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  color: var(--text-primary); transition: background 0.1s;
}
.type-option:hover { background: var(--bg-active); }
.type-option.empty { color: var(--text-tertiary); cursor: default; }
.type-option.custom { color: var(--color-primary); font-style: italic; }
.type-label { font-weight: 500; }
.type-name { font-size: 11px; color: var(--text-tertiary); }
.type-dot {
  display: inline-block; width: 10px; height: 10px;
  border-radius: 50%; flex-shrink: 0;
}
</style>