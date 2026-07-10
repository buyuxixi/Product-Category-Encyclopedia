import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const devProxyTarget = process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': devProxyTarget,
      '/health': devProxyTarget,
    },
  },
})
