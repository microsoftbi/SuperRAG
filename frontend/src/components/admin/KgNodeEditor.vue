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
        <div class="form-row">
          <label>类型</label>
          <input
            v-model="form.type"
            type="text"
            placeholder="如 person / org / product / concept / location 或自定义"
            list="kg-type-suggestions"
          />
          <datalist id="kg-type-suggestions">
            <option v-for="t in typeSuggestions" :key="t" :value="t" />
          </datalist>
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
import { ref, computed, onMounted, nextTick } from 'vue'
import { createEntity, updateEntity } from '../../api/index.js'

const props = defineProps({
  node: { type: Object, default: null },     // null = 新建
  existingNames: { type: Set, required: true },
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.node)

const form = ref({
  name: '',
  type: 'concept',
  propsText: '{}',
})

const nameWarning = ref('')
const propsError = ref('')
const saving = ref(false)
const nameInputRef = ref(null)

const typeSuggestions = ['person', 'org', 'product', 'concept', 'location']

const canSave = computed(() => {
  if (!form.value.name.trim()) return false
  if (propsError.value) return false
  return true
})

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
  // 编辑：自己的名字不算冲突
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
  // 重新校验
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
        type: form.value.type.trim() || 'concept',
        properties: propsObj,
      })
    } else {
      await createEntity({
        name: form.value.name.trim(),
        type: form.value.type.trim() || 'concept',
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

onMounted(() => {
  if (props.node) {
    form.value.name = props.node.name || ''
    form.value.type = props.node.type || 'concept'
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
  nextTick(() => nameInputRef.value?.focus())
})

import { watch } from 'vue'
watch(() => form.value.propsText, checkPropsLive)
watch(() => form.value.name, checkNameConflict)
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.dialog {
  background: #fff; border-radius: 8px; width: 480px; max-width: 90vw;
  display: flex; flex-direction: column; max-height: 85vh;
}
.dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid #eef0f3;
  font-size: 14px; font-weight: 600;
}
.close {
  background: none; border: none; cursor: pointer;
  font-size: 16px; color: #999; padding: 0 4px;
}
.dialog-body { padding: 16px; overflow-y: auto; flex: 1; }
.form-row { margin-bottom: 14px; }
.form-row label {
  display: block; font-size: 12px; color: #555; margin-bottom: 5px; font-weight: 500;
}
.form-row input,
.form-row textarea {
  width: 100%; padding: 8px; font-size: 13px;
  border: 1px solid #d0d4db; border-radius: 4px; outline: none;
  font-family: inherit; box-sizing: border-box;
}
.form-row textarea {
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 12px; resize: vertical;
}
.form-row textarea.invalid { border-color: #c62828; }
.warning {
  margin-top: 4px; font-size: 11px; color: #ef6c00;
  background: #fff3e0; padding: 4px 8px; border-radius: 3px;
}
.dialog-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 16px; border-top: 1px solid #eef0f3; background: #fafbfc;
}
.btn-primary, .btn-secondary {
  padding: 6px 16px; font-size: 13px; border-radius: 4px;
  cursor: pointer; border: 1px solid;
}
.btn-primary { background: #1976d2; color: #fff; border-color: #1976d2; }
.btn-primary:disabled { background: #ccc; border-color: #ccc; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #555; border-color: #d0d4db; }
.btn-secondary:hover { background: #f0f0f0; }
</style>
