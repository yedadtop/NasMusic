import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export const STREAM_BASE_URL = 'http://127.0.0.1:8000'

export default request
