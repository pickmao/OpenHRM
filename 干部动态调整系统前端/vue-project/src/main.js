import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'ant-design-vue/dist/reset.css'

import App from './App.vue'
import router from './router'
import { registerApplicationWebMcpTools } from './utils/app-webmcp'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')

const unregisterApplicationWebMcpTools = registerApplicationWebMcpTools(router)

if (import.meta.hot) {
  import.meta.hot.dispose(unregisterApplicationWebMcpTools)
}
