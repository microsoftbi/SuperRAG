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
        <div class="form-row">
          <label>{{ isEdit ? '新关系类型 *' : '关系类型 *' }}</label>
          <input
            v-model="form.type"
            type="text"
            placeholder="如 任职于 / 属于 / 隶属"
            list="kg-rel-types"
          />
          <datalist id="kg-rel-types">
            <option v-for="t in existingRelTypes" :key="t" :value="t" />
          </datalist>
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
import { ref, computed, onMounted } from 'vue'
import { createRelationship, updateRelationship } from '../../api/index.js'

const props = defineProps({
  // edge 在新建场景下是 null,在编辑场景下是 {source, target, type, sourceName, targetName}
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
const oldType = ref('')   // 编辑时记录原类型
const saving = ref(false)

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
  // 检查源/目标是否存在于图中
  const names = new Set(props.nodes.map(n => n.name))
  if (form.value.source && !names.has(form.value.source.trim())) {
    return `源实体 "${form.value.source}" 不在图谱中，保存时会自动创建`
  }
  if (form.value.target && !names.has(form.value.target.trim())) {
    return `目标实体 "${form.value.target}" 不在图谱中，保存时会自动创建`
  }
  return ''
})

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

onMounted(() => {
  if (props.edge) {
    form.value.source = props.edge.sourceName || ''
    form.value.target = props.edge.targetName || ''
    form.value.type = props.edge.type || ''
    oldType.value = props.edge.type || ''
  }
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.dialog {
  background: #fff; border-radius: 8px; width: 440px; max-width: 90vw;
  display: flex; flex-direction: column;
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
.dialog-body { padding: 16px; }
.form-row { margin-bottom: 14px; }
.form-row label {
  display: block; font-size: 12px; color: #555; margin-bottom: 5px; font-weight: 500;
}
.form-row input {
  width: 100%; padding: 8px; font-size: 13px;
  border: 1px solid #d0d4db; border-radius: 4px; outline: none; box-sizing: border-box;
}
.form-row input:disabled { background: #f5f5f5; color: #999; }
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
