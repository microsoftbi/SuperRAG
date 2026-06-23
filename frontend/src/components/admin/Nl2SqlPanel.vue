<template>
  <div class="nl2sql-panel">
    <h2>NL2SQL 数据库配置</h2>

    <!-- 连接配置 -->
    <section class="section">
      <h3>连接配置</h3>
      <div class="form-grid">
        <div class="field">
          <label>连接名</label>
          <input v-model="conn.conn_name" placeholder="如：生产数据库" />
        </div>
        <div class="field">
          <label>IP 地址</label>
          <input v-model="conn.host" placeholder="192.168.1.100" />
        </div>
        <div class="field">
          <label>端口号</label>
          <input type="number" v-model.number="conn.port" />
        </div>
        <div class="field">
          <label>用户名</label>
          <input v-model="conn.username" placeholder="sa" />
        </div>
        <div class="field">
          <label>密码</label>
          <input type="password" v-model="conn.password" />
        </div>
        <div class="field">
          <label>数据库名</label>
          <input v-model="conn.database" placeholder="mydb" />
        </div>
      </div>
      <div class="actions">
        <button @click="testConn" :disabled="testing" class="test-btn">
          {{ testing ? '测试中...' : '测试连接' }}
        </button>
        <button @click="saveConn" :disabled="saving" class="save-btn">
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
        <span v-if="testMsg" :class="['msg', testOk ? 'success' : 'error']">{{ testMsg }}</span>
      </div>
    </section>

    <!-- 提示词增强 -->
    <section class="section">
      <h3>问数提示词增强</h3>
      <div class="prompt-tabs">
        <button :class="['prompt-tab', { active: promptTab === 'schema' }]" @click="promptTab = 'schema'">字段结构</button>
        <button :class="['prompt-tab', { active: promptTab === 'terms' }]" @click="promptTab = 'terms'">专业术语</button>
        <button :class="['prompt-tab', { active: promptTab === 'qa_pairs' }]" @click="promptTab = 'qa_pairs'">Q&amp;A 示例</button>
      </div>

      <div v-if="promptTab === 'schema'" class="field">
        <label>数据库字段结构信息</label>
        <p class="hint">描述数据表的字段、类型、主外键关系等，用于帮助 LLM 理解数据模型</p>
        <textarea v-model="prompts.schema" rows="10" placeholder="例如：&#10;表 sale_order：&#10;  id (int, PK) — 订单ID&#10;  customer_id (int, FK→customer.id) — 客户ID&#10;  amount (decimal) — 金额&#10;  created_at (datetime) — 创建时间&#10;..."></textarea>
      </div>
      <div v-if="promptTab === 'terms'" class="field">
        <label>专业术语信息</label>
        <p class="hint">定义业务术语与数据库字段的映射关系</p>
        <textarea v-model="prompts.terms" rows="10" placeholder="例如：&#10;出货量 = order_lines 表中 status='shipped' 的数量之和&#10;退货率 = 退货订单数 / 总订单数&#10;GMV = 成交订单金额总和&#10;..."></textarea>
      </div>
      <div v-if="promptTab === 'qa_pairs'" class="field">
        <label>常用问答对应的 SQL</label>
        <p class="hint">提供问法→SQL 的示例，供 LLM 参考生成同类查询</p>
        <textarea v-model="prompts.qa_pairs" rows="10" placeholder="例如：&#10;Q: 上个月销售额最高的客户是谁&#10;A: SELECT c.name, SUM(o.amount) AS total&#10;   FROM sale_order o JOIN customer c ON o.customer_id = c.id&#10;   WHERE o.created_at >= date_trunc('month', now()) - interval '1 month'&#10;   GROUP BY c.name ORDER BY total DESC LIMIT 1;&#10;&#10;Q: ...&#10;A: ..."></textarea>
      </div>
      <button @click="savePrompts" :disabled="saving" class="save-btn">
        {{ saving ? '保存中...' : '保存提示词' }}
      </button>
      <span v-if="saveMsg" :class="['msg', saveOk ? 'success' : 'error']">{{ saveMsg }}</span>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getNl2SqlConfig, updateNl2SqlConfig, testNl2SqlConnection } from '../../api/index.js'

const conn = ref({ conn_name: '', host: '', port: 1433, username: '', password: '', database: '' })
const prompts = ref({ schema: '', terms: '', qa_pairs: '' })
const promptTab = ref('schema')

const testing = ref(false)
const saving = ref(false)
const testMsg = ref('')
const testOk = ref(false)
const saveMsg = ref('')
const saveOk = ref(false)

async function load() {
  try {
    const res = await getNl2SqlConfig()
    if (res.data?.connection) conn.value = { ...res.data.connection }
    if (res.data?.prompts) prompts.value = { ...res.data.prompts }
  } catch { /* ignore */ }
}

async function testConn() {
  testing.value = true
  testMsg.value = ''
  try {
    const res = await testNl2SqlConnection(conn.value)
    testOk.value = res.data.success
    testMsg.value = res.data.success ? '连接成功 ✅' : `连接失败: ${res.data.message}`
  } catch (e) {
    testOk.value = false
    testMsg.value = '测试请求失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    testing.value = false
  }
}

async function saveConn() {
  saving.value = true
  saveMsg.value = ''
  try {
    await updateNl2SqlConfig({ connection: conn.value, prompts: prompts.value })
    saveOk.value = true
    saveMsg.value = '配置已保存 ✅'
  } catch {
    saveOk.value = false
    saveMsg.value = '保存失败'
  } finally {
    saving.value = false
  }
}

async function savePrompts() {
  saving.value = true
  saveMsg.value = ''
  try {
    await updateNl2SqlConfig({ connection: conn.value, prompts: prompts.value })
    saveOk.value = true
    saveMsg.value = '提示词已保存 ✅'
  } catch {
    saveOk.value = false
    saveMsg.value = '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.nl2sql-panel { max-width: 800px; }
.nl2sql-panel h2 { font-size: 16px; margin-bottom: 16px; }
.section {
  padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 20px;
}
.section h3 { font-size: 14px; margin: 0 0 12px; color: #444; }
.form-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 13px; color: #555; font-weight: 500; }
.field input, .field textarea {
  padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 14px;
}
.field textarea { font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace; font-size: 13px; resize: vertical; }
.hint { font-size: 12px; color: #999; margin: 0 0 2px; }
.actions { margin-top: 12px; display: flex; gap: 8px; align-items: center; }
.test-btn, .save-btn {
  padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
}
.test-btn { background: #fff; border: 1px solid #1976d2; color: #1976d2; }
.test-btn:hover:not(:disabled) { background: #e3f2fd; }
.save-btn { background: #1976d2; color: #fff; }
.save-btn:hover:not(:disabled) { background: #1565c0; }
.test-btn:disabled, .save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.msg { font-size: 13px; }
.msg.success { color: #2e7d32; }
.msg.error { color: #c62828; }
.prompt-tabs {
  display: flex; gap: 2px; border-bottom: 1px solid #e0e0e0; margin-bottom: 12px;
}
.prompt-tab {
  padding: 6px 18px; border: none; background: none; cursor: pointer;
  font-size: 13px; color: #666; border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.prompt-tab.active { color: #1976d2; border-bottom-color: #1976d2; font-weight: 600; }
.prompt-tab:hover:not(.active) { color: #333; }
</style>