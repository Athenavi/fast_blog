import {fileURLToPath, URL} from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import {ElementPlusResolver} from 'unplugin-vue-components/resolvers'
import Components from 'unplugin-vue-components/vite'
import {defineConfig, loadEnv} from 'vite'

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.VITE_PROXY_TARGET || 'http://localhost:9421'

  return {
    plugins: [
      vue(),
      tailwindcss(),
      AutoImport({
        imports: ['vue', 'vue-router', 'pinia'],
        resolvers: [ElementPlusResolver()],
        dts: 'src/auto-imports.d.ts',
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: 'src/components.d.ts',
      }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: Number(env.VITE_PORT || 5173),
      host: true,
      proxy: {
        // 开发期把 /api 代理到后端（生产由 nginx 反代）
        '/api': {
          target: backend,
          changeOrigin: true,
        },
        '/media': {
          target: backend,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router', 'pinia'],
            element: ['element-plus', '@element-plus/icons-vue'],
          },
        },
      },
    },
  }
})
