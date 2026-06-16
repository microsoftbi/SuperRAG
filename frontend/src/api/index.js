import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
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
export function uploadDocument(file, title, category, knowledgeBaseIds = []) {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (category) form.append('category', category)
  form.append('knowledge_base_ids', JSON.stringify(knowledgeBaseIds))
  return api.post('/documents/upload', form)
}

export function listDocuments(params) {
  return api.get('/documents', { params })
}

export function listDocumentsWithKB(params) {
  return api.get('/documents', { params })
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

// Chat
export function sendChatMessage(sessionId, query, history) {
  return fetch('/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify({ session_id: sessionId, query, history }),
  })
}

// Logs
export function listLogs(params) {
  return api.get('/logs', { params })
}

export function getLog(id) {
  return api.get(`/logs/${id}`)
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

export default api