<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <div class="dialog-header">
        <span>{{ isEdit ? '编辑节点' : '新建节点' }}</span>
        <button class="close" @click="$emit('close')">✕</button>
      </div>
      <div class="dialog-body">
        <div class="form-row">
          <label>名称 *</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="实体名称"
            ref="nameInputRef"
            @blur="checkNameConflict"
          />
          <div v-if="nameWarning" class="warning">⚠️ {{ nameWarning }}</div>
        </div>
        <div class="form-row" ref="typeRowRef">
          <label>类型</label>
          <div class="type-select-wrapper">
            <input
              v-model="form.type"
              type="text"
              placeholder="选择或输入类型..."
              @focus="showDropdown = true"
              @input="onTypeInput"
              @keydown.escape="showDropdown = false"
              @keydown.enter="showDropdown = false"
            />
            <div v-if="showDropdown" class="type-dropdown">
              <div
                v-for="t in filteredTypes"
                :key="t.name"
                class="type-option"
                @mousedown.prevent="selectType(t.name)"
              >
                <span class="type-dot" :style="{ background: t.color }"></span>
                <span class="type-label">{{ t.label || t.name }}</span>
                <span class="type-name">({{ t.name }})</span>
              </div>
              <div v-if="form.type && !allTypeNames.includes(form.type)" class="type-option custom">
                ✏️ 自定义 "{{ form.type }}"（需先在类型管理中注册）
              </div>
              <div v-if="filteredTypes.length === 0 && (!form.type || allTypeNames.includes(form.type))" class="type-option empty">
                {{ loadingTypes ? '加载中...' : '暂无类型，请先在「类型管理」中创建' }}
              </div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label>属性 (JSON 格式，可选)</label>
          <textarea
            v-model="form.propsText"
            rows="6"
            placeholder='{"description": "…", "alias": "…"}'
            :class="{ invalid: propsError }"
          />
          <div v-if="propsError" class="warning">⚠️ {{ propsError }}</div>
        </div>
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
import { createEntity, updateEntity, getNodeTypes } from '../../api/index.js'

const props = defineProps({
  node: { type: Object, default: null },     // null = 新建
  existingNames: { type: Set, required: true },
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.node)

const form = ref({
  name: '',
  type: '',
  propsText: '{}',
})

const nameWarning = ref('')
const propsError = ref('')
const saving = ref(false)
const nameInputRef = ref(null)
const typeRowRef = ref(null)
const showDropdown = ref(false)
const allTypes = ref([])
const loadingTypes = ref(false)

const getCSSVar = (name, fallback) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

const allTypeNames = computed(() => allTypes.value.map(t => t.name))

const filteredTypes = computed(() => {
  const q = form.value.type.trim().toLowerCase()
  if (!q) return allTypes.value
  return allTypes.value.filter(t =>
    t.name.toLowerCase().includes(q) ||
    (t.label && t.label.toLowerCase().includes(q))
  )
})

const canSave = computed(() => {
  if (!form.value.name.trim()) return false
  if (propsError.value) return false
  return true
})

async function loadTypes() {
  loadingTypes.value = true
  try {
    const res = await getNodeTypes()
    // API returns array of {name, label, color, description}
    allTypes.value = (res.data || []).map(t => ({
      name: t.name,
      label: t.label || t.name,
      color: t.color || '#607d8b',
    }))
  } catch {
    allTypes.value = []
  } finally {
    loadingTypes.value = false
  }
}

function selectType(t) {
  form.value.type = t
  showDropdown.value = false
}

function onTypeInput() {
  showDropdown.value = true
}

function onDocumentClick(e) {
  if (typeRowRef.value && !typeRowRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

function parseProps() {
  const txt = form.value.propsText.trim()
  if (!txt) return {}
  try {
    const obj = JSON.parse(txt)
    if (typeof obj !== 'object' || Array.isArray(obj)) {
      throw new Error('必须是 JSON 对象')
    }
    return obj
  } catch (e) {
    throw new Error('JSON 格式错误: ' + e.message)
  }
}

function checkPropsLive() {
  try {
    parseProps()
    propsError.value = ''
  } catch (e) {
    propsError.value = e.message
  }
}

function checkNameConflict() {
  const n = form.value.name.trim()
  if (!n) { nameWarning.value = ''; return }
  if (isEdit.value && n === props.node.name) {
    nameWarning.value = ''; return
  }
  if (props.existingNames.has(n)) {
    nameWarning.value = isEdit.value
      ? `已有同名节点 "${n}"。保存会被服务器拒绝（请改名或先合并）。`
      : `已存在同名节点 "${n}"。新建会合并到该节点。`
  } else {
    nameWarning.value = ''
  }
}

async function save() {
  let propsObj
  try {
    propsObj = parseProps()
  } catch (e) {
    propsError.value = e.message
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await updateEntity(props.node.id, {
        name: form.value.name.trim(),
        type: form.value.type.trim() ,
        properties: propsObj,
      })
    } else {
      await createEntity({
        name: form.value.name.trim(),
        type: form.value.type.trim() ,
        properties: propsObj,
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
  if (props.node) {
    form.value.name = props.node.name || ''
    form.value.type = props.node.type 
    let propsObj = {}
    try {
      propsObj = props.node.properties
        ? (typeof props.node.properties === 'string'
            ? JSON.parse(props.node.properties)
            : props.node.properties)
        : {}
    } catch { propsObj = {} }
    form.value.propsText = JSON.stringify(propsObj, null, 2)
  }
  await loadTypes()
  nextTick(() => nameInputRef.value?.focus())
  document.addEventListener('click', onDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
})

import { watch } from 'vue'
watch(() => form.value.propsText, checkPropsLive)
watch(() => form.value.name, checkNameConflict)
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: var(--overlay);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.dialog {
  background: var(--bg-card); border-radius: 8px; width: 480px; max-width: 90vw;
  display: flex; flex-direction: column; max-height: 85vh;
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
.dialog-body { padding: 16px; overflow-y: auto; flex: 1; }
.form-row { margin-bottom: 14px; }
.form-row label {
  display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 5px; font-weight: 500;
}
.form-row input,
.form-row textarea {
  width: 100%; padding: 8px; font-size: 13px;
  border: 1px solid var(--border-input); border-radius: 4px; outline: none;
  font-family: inherit; box-sizing: border-box;
  background: var(--bg-card); color: var(--text-primary);
}
.form-row textarea {
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 12px; resize: vertical;
}
.form-row textarea.invalid { border-color: var(--color-danger); }
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