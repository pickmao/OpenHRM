<template>
  <div class="editor-page">
    <div class="editor-toolbar">
      <a-space>
        <a-button @click="router.back()">返回任务列表</a-button>
        <strong>{{ task?.template_name || '在线填报' }}</strong>
      </a-space>
      <a-space>
        <a-tag :color="saveStatusColor">{{ saveStatusText }}</a-tag>
        <a-button type="primary" :loading="submitting" @click="submit">
          完成填写并提交
        </a-button>
      </a-space>
    </div>
    <a-spin :spinning="loading" tip="正在加载在线表格…" class="editor-spin"><div id="onlyoffice-editor" class="editor" /></a-spin>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { formsApi } from '@/api/forms'
import { registerModelContextTools } from '@/utils/webmcp'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const task = ref(null)
/** unknown | saved | unsaved | saving */
const saveStatus = ref('unknown')
let editor = null
let saveWaitTimer = null

const saveStatusText = computed(() => {
  const map = {
    unknown: '保存状态未知，编辑后请等待自动保存',
    saved: '已保存',
    unsaved: '有未保存修改，请稍候…',
    saving: '正在保存…'
  }
  return map[saveStatus.value] || map.unknown
})

const saveStatusColor = computed(() => {
  const map = { unknown: 'default', saved: 'success', unsaved: 'warning', saving: 'processing' }
  return map[saveStatus.value] || 'default'
})

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

const waitUntilSaved = (timeoutMs = 8000) => new Promise((resolve, reject) => {
  if (saveStatus.value === 'saved') {
    resolve()
    return
  }
  saveStatus.value = saveStatus.value === 'unsaved' ? 'saving' : saveStatus.value
  const started = Date.now()
  saveWaitTimer = setInterval(() => {
    if (saveStatus.value === 'saved') {
      clearInterval(saveWaitTimer)
      saveWaitTimer = null
      resolve()
    } else if (Date.now() - started >= timeoutMs) {
      clearInterval(saveWaitTimer)
      saveWaitTimer = null
      reject(new Error('等待文档保存超时，请确认表格已自动保存后再提交'))
    }
  }, 300)
})

const load = async () => {
  loading.value = true
  try {
    task.value = await formsApi.getTask(route.params.id)
    const config = await formsApi.getOnlyOfficeConfig(route.params.id)
    await loadScript(`${config.document_server_url}/web-apps/apps/api/documents/api.js`)
    loading.value = false
    await nextTick()
    const events = {
      ...(config.events || {}),
      onDocumentStateChange(event) {
        saveStatus.value = event?.data ? 'unsaved' : 'saved'
        config.events?.onDocumentStateChange?.(event)
      },
      onDocumentReady(event) {
        if (saveStatus.value === 'unknown') saveStatus.value = 'saved'
        config.events?.onDocumentReady?.(event)
      }
    }
    editor = new window.DocsAPI.DocEditor('onlyoffice-editor', { ...config, ...editorSize(), events })
  } catch (error) {
    message.error(requestErrorMessage(error) || '在线表格加载失败')
  } finally { loading.value = false }
}

const doSubmit = async () => {
  submitting.value = true
  try {
    if (saveStatus.value === 'unsaved' || saveStatus.value === 'saving') {
      message.loading({ content: '正在等待文档保存完成…', key: 'save-wait', duration: 0 })
      await waitUntilSaved()
      message.destroy('save-wait')
    }
    await formsApi.submitTask(route.params.id)
    message.success('填报已提交')
    router.push('/forms/tasks')
  } catch (error) {
    message.destroy('save-wait')
    message.error(error.message || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

const submit = () => {
  if (saveStatus.value === 'unsaved') {
    Modal.confirm({
      title: '文档尚未保存完成',
      content: '检测到表格仍有未保存修改。请等待自动保存完成后再提交；也可确认已手动保存后继续。',
      okText: '等待保存并提交',
      cancelText: '取消',
      onOk: () => doSubmit()
    })
    return
  }
  if (saveStatus.value === 'unknown') {
    Modal.confirm({
      title: '确认提交？',
      content: '当前无法确认文档最新版本是否已保存。请确认内容无误后再提交。',
      okText: '确认提交',
      cancelText: '取消',
      onOk: () => doSubmit()
    })
    return
  }
  doSubmit()
}

let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_onlyoffice_form_task', title: '读取当前在线填报任务', description: '读取当前 OnlyOffice 填报任务的基本信息，不修改或提交内容。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() {
        if (!task.value) await load()
        return {
          task: task.value && {
            id: task.value.id,
            templateName: task.value.template_name,
            batchName: task.value.batch_name,
            status: task.value.status,
            deadlineAt: task.value.deadline_at
          },
          saveStatus: saveStatus.value
        }
      }
    },
    {
      name: 'complete_openhrm_current_form_submission', title: '提交当前在线填报', description: '提交当前 OnlyOffice 填报任务；请确认已在编辑器中保存内容，此操作会将任务状态变为已提交。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute() {
        if (!task.value) await load()
        await doSubmit()
        return { status: 'submitted', taskId: String(route.params.id), saveStatus: saveStatus.value }
      }
    }
  ])
}
onMounted(() => { registerWebMcpTools(); load() })
onBeforeUnmount(() => {
  unregisterWebMcpTools()
  if (saveWaitTimer) clearInterval(saveWaitTimer)
  if (editor?.destroyEditor) editor.destroyEditor()
})
</script>

<style scoped>
.editor-page { height: calc(100vh - 150px); min-height: 680px; width: 100%; display: flex; flex-direction: column; overflow: hidden; padding: 0 24px; }
.editor-toolbar { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; padding: 10px 0 16px; }
.editor-spin { display: block; flex: 1 1 auto; min-height: 0; width: 100%; }
.editor-spin :deep(.ant-spin-container) { height: 100%; width: 100%; }
.editor { width: 100%; height: 100%; min-height: 0; border: 1px solid #f0f0f0; }
</style>
