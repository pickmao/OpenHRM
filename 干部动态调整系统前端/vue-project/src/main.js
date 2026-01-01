import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
// Ant Design Vue
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import zhCN from 'ant-design-vue/es/locale/zh_CN'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})
app.use(Antd)

app.mount('#app')
