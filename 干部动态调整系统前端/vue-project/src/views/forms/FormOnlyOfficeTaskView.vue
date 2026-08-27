<template>
  <div class="editor-page">
    <div class="editor-toolbar"><a-button @click="router.back()">返回</a-button><strong>{{ task?.template_name || '填报结果' }}</strong></div>
    <a-spin :spinning="loading" tip="正在加载表格…" class="editor-spin"><div id="onlyoffice-viewer" class="editor" /></a-spin>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { formsApi } from '@/api/forms'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const task = ref(null)
let editor = null
const editorSize = () => ({ width: '100%', height: `${Math.max(window.innerHeight - 190, 680)}px` })
const loadScript = src => new Promise((resolve, reject) => {
  if (window.DocsAPI) return resolve()
  const script = document.createElement('script'); script.src = src; script.onload = resolve; script.onerror = reject; document.head.appendChild(script)
})
onMounted(async () => {
  try {
    task.value = await formsApi.getTask(route.params.id)
    const config = await formsApi.getOnlyOfficeViewConfig(route.params.id)
    await loadScript(`${config.document_server_url}/web-apps/apps/api/documents/api.js`)
    loading.value = false
    await nextTick()
    editor = new window.DocsAPI.DocEditor('onlyoffice-viewer', { ...config, ...editorSize() })
  } catch (_) { message.error('无法加载填报结果') } finally { loading.value = false }
})
onBeforeUnmount(() => { if (editor?.destroyEditor) editor.destroyEditor() })
</script>

<style scoped>
.editor-page { height: calc(100vh - 150px); min-height: 680px; width: 100%; display: flex; flex-direction: column; overflow: hidden; }
.editor-toolbar { flex: 0 0 auto; display: flex; gap: 16px; align-items: center; padding: 10px 0 16px; }
.editor-spin { display: block; flex: 1 1 auto; min-height: 0; width: 100%; }
.editor-spin :deep(.ant-spin-container) { height: 100%; width: 100%; }
.editor { width: 100%; height: 100%; min-height: 0; border: 1px solid #f0f0f0; }
</style>
