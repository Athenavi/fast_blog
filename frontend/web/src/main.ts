import {createPinia} from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import {createApp} from 'vue'

import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import 'element-plus/dist/index.css'
import 'nprogress/nprogress.css'
import '@/styles/index.css'

import App from './App.vue'
import {setupDirectives} from './directives'
import router from './router'

const app = createApp(App)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

// 注册 Element Plus 全量图标（模板里可直接用 <el-icon><Search /></el-icon>）
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus, {locale: zhCn})
setupDirectives(app)

app.mount('#app')
