import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401 && !err.config._retry) {
      err.config._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/api/auth/token/refresh/`, { refresh })
          localStorage.setItem('access_token', data.access)
          err.config.headers.Authorization = `Bearer ${data.access}`
          return api(err.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

export const auth = {
  login: (u, p) => api.post('/api/auth/token/', { username: u, password: p }),
  me: () => api.get('/api/accounts/me/'),
}

export const emissions = {
  stats: () => api.get('/api/emissions/records/stats/'),
  records: (params) => api.get('/api/emissions/records/', { params }),
  review: (id, action, notes) => api.post(`/api/emissions/records/${id}/review/`, { action, notes }),
  bulkApprove: (ids) => api.post('/api/emissions/records/bulk_approve/', { ids }),
  batches: (params) => api.get('/api/emissions/batches/', { params }),
}

export const ingestion = {
  upload: (file, sourceType, notes) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('source_type', sourceType)
    if (notes) fd.append('notes', notes)
    return api.post('/api/ingestion/upload/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default api
