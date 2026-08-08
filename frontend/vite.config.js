import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',                     // Nginx 根路径部署
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,            // 生产环境不生成 sourcemap
    chunkSizeWarningLimit: 1000, // Element Plus 较大会触发警告
    rollupOptions: {
      output: {
        manualChunks: {
          // 拆分大库，优化首屏加载
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-element': ['element-plus', '@element-plus/icons-vue'],
          'vendor-echarts': ['echarts'],
        },
      },
    },
  },
})
