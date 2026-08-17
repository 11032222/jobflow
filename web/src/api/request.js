import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('jobflow_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    const msg =
      typeof detail === 'string'
        ? detail
        : detail?.[0]?.msg || err.message || '请求失败'
    if (status === 401) {
      localStorage.removeItem('jobflow_token')
      localStorage.removeItem('jobflow_user')
      if (!location.hash.includes('/login')) {
        location.hash = '#/login'
      }
    } else if (status === 400 || status === 403 || status === 404 || status === 500) {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  },
)

export default request
