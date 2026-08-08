import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data === undefined || data === null) {
      return { code: 500, message: '服务端返回数据为空', data: null }
    }
    if (typeof data !== 'object') {
      return { code: 500, message: '服务端返回格式错误', data: null }
    }
    if (data.code === undefined) {
      return { code: 200, data }
    }
    return data
  },
  (error) => {
    console.error('API请求失败:', error)
    const message = error.response?.data?.message || error.message || '网络请求失败'
    return Promise.reject({ code: error.response?.status || 500, message })
  }
)

export default request
