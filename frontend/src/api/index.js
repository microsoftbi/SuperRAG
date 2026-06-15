import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// Documents
export function uploadDocument(file, title, category) {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (category) form.append('category', category)
  return api.post('/documents/upload', form)
}

export function listDocuments(params) {
  return api.get('/documents', { params })
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

// Chat
export function sendChatMessage(sessionId, query, history) {
  return api.post('/chat', { session_id: sessionId, query, history }, {
    responseType: 'stream',
    adapter: 'fetch',
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

export default api
