<template>
  <div class="editor-page">
    <div class="editor-toolbar">
      <a-space>
        <a-button @click="router.back()">返回任务列表</a-button>
        <strong>{{ task?.template_name || '在线填报' }}</strong>
      </a-space>
      <a-space>
        <span class="hint">表格会自动保存</span>
        <a-button type="primary" :loading="submitting" @click="submit">完成填写并提交</a-button>
      </a-space>
    </div>
    <a-spin :spinning="loading" tip="正在加载在线表格…" class="editor-spin"><div id="onlyoffice-editor" class="editor" /></a-spin>
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
const submitting = ref(false)
const task = ref(null)
let editor = null

const requestErrorMessage = error => {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') return Object.values(detail).flat().join('；')
  return error.message
}
const editorSize = () => ({ width: '100%', height: `${Math.max(window.innerHeight - 190, 680)}px` })

const loadScript = src => new Promise((resolve, reject) => {
  if (window.DocsAPI) return resolve()
  const script = document.createElement('script')
  script.src = src
  script.onload = resolve
  script.onerror = () => reject(new Error('OnlyOffice 编辑器加载失败，请检查文档服务是否启动'))
  document.head.appendChild(script)
})
const load = async () => {
  loading.value = true
  try {
    task.value = await formsApi.getTask(route.params.id)
    const config = await formsApi.getOnlyOfficeConfig(route.params.id)
    await loadScript(`${config.document_server_url}/web-apps/apps/api/documents/api.js`)
    // 先让加载层退出，保证 OnlyOffice 首次读取到的是最终的全尺寸容器。
    loading.value = false
    await nextTick()
    editor = new window.DocsAPI.DocEditor('onlyoffice-editor', { ...config, ...editorSize() })
  } catch (error) {
    message.error(requestErrorMessage(error) || '在线表格加载失败')
  } finally { loading.value = false }
}
const submit = async () => {
  submitting.value = true
  try {
    await formsApi.submitTask(route.params.id)
    message.success('填报已提交')
    router.push('/forms/tasks')
  } catch (_) { message.error('提交失败，请稍后重试') } finally { submitting.value = false }
}
onMounted(load)
onBeforeUnmount(() => { if (editor?.destroyEditor) editor.destroyEditor() })
</script>

<style scoped>
.editor-page { height: calc(100vh - 150px); min-height: 680px; width: 100%; display: flex; flex-direction: column; overflow: hidden; }
.editor-toolbar { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 10px 0 16px; }
.hint { color: #8c8c8c; font-size: 13px; }
.editor-spin { display: block; flex: 1 1 auto; min-height: 0; width: 100%; }
.editor-spin :deep(.ant-spin-container) { height: 100%; width: 100%; }
.editor { width: 100%; height: 100%; min-height: 0; border: 1px solid #f0f0f0; }
</style>
