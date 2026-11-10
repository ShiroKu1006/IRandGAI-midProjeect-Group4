import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 開發時把 /api 轉給 Flask（預設 http://127.0.0.1:5000），前端不需處理 CORS。
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
