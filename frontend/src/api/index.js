import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

// Auth interceptor — 自动附带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auth interceptor — 401 时跳转登录
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// Auth
export function login(data) {
  return api.post('/auth/login', data)
}

export function register(data) {
  return api.post('/auth/register', data)
}

export function getMe() {
  return api.get('/auth/me')
}

// Documents
export function uploadDocument(file, title, category, knowledgeBaseIds = [], store = 'vector') {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (category) form.append('category', category)
  form.append('store', store)
  form.append('knowledge_base_ids', JSON.stringify(knowledgeBaseIds))
  return api.post('/documents/upload', form)
}

export function listDocuments(params) {
  return api.get('/documents', { params })
}

export function reprocessDocument(id) {
  return api.post(`/documents/${id}/reprocess`)
}

export function listDocumentsWithKB(params) {
  return api.get('/documents', { params })
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

export function getDocumentChunks(id) {
  return api.get(`/documents/${id}/chunks`)
}

// Chat
export function sendChatMessage(sessionId, query, mode = 'rag') {
  return fetch('/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify({ session_id: sessionId, query, mode }),
  })
}

// Chat History
export function getChatHistory(sessionId, mode = 'rag') {
  return api.get('/chat/history', { params: { session_id: sessionId, mode } })
}

export function getChatSessions(mode = 'rag') {
  return api.get('/chat/sessions', { params: { mode } })
}

export function deleteChatSession(sessionId, mode = 'rag') {
  return api.delete(`/chat/sessions/${sessionId}`, { params: { mode } })
}

export function renameChatSession(sessionId, title) {
  return api.put(`/chat/sessions/${sessionId}`, { title })
}

export function getChatSessionTitle(sessionId) {
  return api.get(`/chat/sessions/${sessionId}/title`)
}

// Logs
export function listLogs(params) {
  return api.get('/logs', { params })
}

export function getLog(id) {
  return api.get(`/logs/${id}`)
}

export function clearLogs() {
  return api.delete('/logs')
}

// Feedback
export function submitFeedback(data) {
  return api.post('/feedback', data)
}

export function getFeedbackStats() {
  return api.get('/feedback/stats')
}

export function listFeedback(params) {
  return api.get('/feedback', { params })
}

// Runtime Config
export function getRuntimeConfig() {
  return api.get('/config')
}

export function updateRuntimeConfig(data) {
  return api.put('/config', data)
}

// Stats
export function getStatsOverview() {
  return api.get('/stats/overview')
}

export function getStatsTrends(days = 7) {
  return api.get('/stats/trends', { params: { days } })
}

// Alerts
export function getAlerts() {
  return api.get('/alerts')
}

// Knowledge Bases
export function listKnowledgeBases() {
  return api.get('/knowledge-bases')
}

export function createKnowledgeBase(data) {
  return api.post('/knowledge-bases', data)
}

export function updateKnowledgeBase(id, data) {
  return api.put(`/knowledge-bases/${id}`, data)
}

export function deleteKnowledgeBase(id) {
  return api.delete(`/knowledge-bases/${id}`)
}

// Users
export function listUsers() {
  return api.get('/users')
}

export function getUserKnowledgeBases(userId) {
  return api.get(`/users/${userId}/knowledge-bases`)
}

export function setUserKnowledgeBases(userId, data) {
  return api.put(`/users/${userId}/knowledge-bases`, data)
}

// ── Knowledge Graph（全局图谱）──

export function getGraph() {
  return api.get('/knowledge-graph/graph')
}

export function getEntityTypes() {
  return api.get('/knowledge-graph/entity-types')
}

export function executeCypher(cypher) {
  return api.post('/knowledge-graph/cypher', { cypher })
}

export function searchEntities(query) {
  return api.get('/knowledge-graph/entities/search', { params: { q: query } })
}

export function getEntityDetail(entityId) {
  return api.get(`/knowledge-graph/entities/${entityId}`)
}

export function rebuildGraph() {
  return api.post('/knowledge-graph/extract', null, { timeout: 600000 })
}

export function createEntity(data) {
  return api.post('/knowledge-graph/entities', data)
}

export function createRelationship(data) {
  return api.post('/knowledge-graph/relationships', data)
}

export function deleteRelationship(data) {
  return api.delete('/knowledge-graph/relationships', { data })
}

export function updateRelationship(data) {
  return api.put('/knowledge-graph/relationships', data)
}

export function updateEntity(entityId, data) {
  return api.put(`/knowledge-graph/entities/${entityId}`, data)
}

export function deleteEntity(entityId) {
  return api.delete(`/knowledge-graph/entities/${entityId}`)
}

export function getEntityRelCount(entityId) {
  return api.get(`/knowledge-graph/entities/${entityId}/relationship-count`)
}

export function batchDeleteEntities(ids) {
  return api.post('/knowledge-graph/entities/batch-delete', { ids })
}

export function batchDeleteRelationships(relationships) {
  return api.post('/knowledge-graph/relationships/batch-delete', { relationships })
}

// ── 类型管理 ──

export function getNodeTypes() {
  return api.get('/knowledge-graph/node-types')
}

export function createNodeType(data) {
  return api.post('/knowledge-graph/node-types', data)
}

export function updateNodeType(name, data) {
  return api.put(`/knowledge-graph/node-types/${name}`, data)
}

export function deleteNodeType(name) {
  return api.delete(`/knowledge-graph/node-types/${name}`)
}

export function getRelationTypes() {
  return api.get('/knowledge-graph/relation-types')
}

export function createRelationType(data) {
  return api.post('/knowledge-graph/relation-types', data)
}

export function updateRelationType(name, data) {
  return api.put(`/knowledge-graph/relation-types/${name}`, data)
}

export function deleteRelationType(name) {
  return api.delete(`/knowledge-graph/relation-types/${name}`)
}

// ── NL2SQL ──

export function getNl2SqlConfig() {
  return api.get('/nl2sql/config')
}

export function updateNl2SqlConfig(data) {
  return api.put('/nl2sql/config', data)
}

export function testNl2SqlConnection(data) {
  return api.post('/nl2sql/test', data)
}

export default api