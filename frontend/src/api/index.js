import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

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

export function sendChatMessage(sessionId, query, history) {
  return api.post('/chat', { session_id: sessionId, query, history }, {
    responseType: 'stream',
    adapter: 'fetch',
  })
}

export default api
