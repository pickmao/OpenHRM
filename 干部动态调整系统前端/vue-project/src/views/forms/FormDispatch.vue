<template>
  <div class="page-shell">
    <a-page-header title="表单下发" sub-title="上传 Excel，选择填报批次和人员，再统一下发；表格类型不限定为考核表" />
    <a-row :gutter="16">
      <a-col :xs="24" :lg="10">
        <a-card title="一、上传或选择表格" class="section-card">
          <a-form layout="vertical">
            <a-form-item label="已有表格模板">
              <a-select v-model:value="form.templateId" placeholder="选择已上传的 Excel" :loading="loadingTemplates" @change="syncTemplateName">
                <a-select-option v-for="item in templates" :key="item.id" :value="item.id">{{ item.name }}（{{ item.code }}）</a-select-option>
              </a-select>
              <div class="form-hint">只显示仍保留 Excel 源文件、可在线填写的模板。</div>
            </a-form-item>
            <a-divider>或上传新的 Excel 表格</a-divider>
            <a-form-item label="表格名称"><a-input v-model:value="upload.name" placeholder="例如：2026 年度个人自评表" /></a-form-item>
            <a-form-item label="模板编码"><a-input v-model:value="upload.code" placeholder="例如：SELF_REVIEW_2026" /></a-form-item>
            <a-form-item label="Excel 文件">
              <a-upload :before-upload="captureFile" :max-count="1" accept=".xlsx,.xls" @remove="clearFile">
                <a-button><UploadOutlined />选择 Excel 文件</a-button>
              </a-upload>
            </a-form-item>
            <a-button type="dashed" block :loading="uploading" @click="uploadTemplate">保存为可下发表格</a-button>
          </a-form>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="14">
        <a-card title="二、选择下发对象" class="section-card">
          <a-alert type="info" show-icon message="下发给谁，谁就在“我的待填报”中在线填写该 Excel；无需再设置评价对象。" />
          <a-form layout="vertical" class="dispatch-form">
            <a-form-item label="填报批次">
              <a-radio-group v-model:value="batchMode" @change="form.batchId = undefined">
                <a-radio value="new">新建批次</a-radio>
                <a-radio value="existing">选择已有批次并追加</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item v-if="batchMode === 'new'" label="新建批次名称"><a-input v-model:value="form.batchName" placeholder="例如：2026 年消防安全自查、干部信息更新" /></a-form-item>
            <a-form-item v-else label="选择填报批次">
              <a-select v-model:value="form.batchId" :loading="loadingBatches" placeholder="选择尚未关闭的填报批次" :options="batchOptions" />
              <div class="form-hint">追加后会沿用该批次的原截止时间；相同表格和填报人不会重复创建任务。</div>
            </a-form-item>
            <a-form-item v-if="batchMode === 'new'" label="截止时间"><a-date-picker v-model:value="form.deadlineAt" show-time style="width:100%" /></a-form-item>
            <a-alert v-else-if="selectedBatch" type="info" show-icon :message="`当前批次：${selectedBatch.name}`" :description="`原截止时间：${new Date(selectedBatch.deadline_at).toLocaleString()}`" class="batch-info" />
            <a-form-item label="下发范围">
              <a-radio-group v-model:value="recipientMode">
                <a-radio value="all">下发给所有启用用户</a-radio>
                <a-radio value="selected">选择具体人员</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item v-if="recipientMode === 'selected'" label="填报人员">
              <a-select v-model:value="form.userIds" mode="multiple" show-search option-filter-prop="label" :loading="loadingUsers" placeholder="选择需要填写表格的人员">
                <a-select-option v-for="user in users" :key="user.id" :value="user.id" :label="user.real_name || user.username">
                  {{ user.real_name || user.username }}（{{ user.username }}）
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-space>
              <a-button @click="preview">预览下发名单</a-button>
              <a-button type="primary" :loading="publishing" @click="publish">确认下发</a-button>
            </a-space>
          </a-form>
        </a-card>
      </a-col>
    </a-row>
    <a-modal v-model:open="previewOpen" title="下发预览" :footer="null" width="760px">
      <a-alert :message="`将创建 ${previewItems.length} 个填报任务`" type="success" show-icon class="preview-alert" />
      <a-table :data-source="previewItems" :columns="previewColumns" row-key="assignee_id" size="small" :pagination="{ pageSize: 8 }" />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import request from '@/utils/request'
import { formsApi } from '@/api/forms'
import { registerModelContextTools } from '@/utils/webmcp'

const templates = ref([])
const users = ref([])
const batches = ref([])
const loadingTemplates = ref(false)
const loadingUsers = ref(false)
const loadingBatches = ref(false)
const uploading = ref(false)
const publishing = ref(false)
const previewOpen = ref(false)
const previewItems = ref([])
const recipientMode = ref('selected')
const batchMode = ref('new')
const selectedFile = ref(null)
const form = reactive({ templateId: undefined, batchId: undefined, batchName: '', deadlineAt: null, userIds: [] })
const upload = reactive({ name: '', code: '' })

const previewColumns = [
  { title: '表格', dataIndex: 'template_name' },
  { title: '填报人', dataIndex: 'assignee_name' },
  { title: '所属单位', dataIndex: 'org_unit' }
]
const batchOptions = computed(() => batches.value.filter(item => item.status !== 'CLOSED').map(item => ({
  value: item.id,
  label: `${item.name}（截止：${new Date(item.deadline_at).toLocaleString()}）`
})))
const selectedBatch = computed(() => batches.value.find(item => item.id === form.batchId))

const loadTemplates = async () => {
  loadingTemplates.value = true
  try {
    const result = await formsApi.getTemplates({ active: true })
    // 数据库中的旧模板可保留作历史记录；源文件随故障磁盘丢失时，不能再用于 OnlyOffice 填报。
    templates.value = (Array.isArray(result) ? result : result?.results || []).filter(item => item.source_file)
  } finally { loadingTemplates.value = false }
}
const loadUsers = async () => {
  loadingUsers.value = true
  try { const result = await request.get('/admin/users/'); users.value = Array.isArray(result) ? result : result?.results || [] } catch (_) { users.value = [] } finally { loadingUsers.value = false }
}
const loadBatches = async () => {
  loadingBatches.value = true
  try { const result = await formsApi.getDispatches(); batches.value = Array.isArray(result) ? result : result?.results || [] } finally { loadingBatches.value = false }
}
const syncTemplateName = () => {
  const item = templates.value.find(value => value.id === form.templateId)
  if (item && !form.batchName) form.batchName = `${item.name}下发`
}
const captureFile = (file) => { selectedFile.value = file; return false }
const clearFile = () => { selectedFile.value = null }
const uploadTemplate = async () => {
  if (!upload.name || !upload.code || !selectedFile.value) return message.warning('请填写表格名称、模板编码并选择 Excel 文件')
  const data = new FormData()
  data.append('name', upload.name)
  data.append('code', upload.code)
  data.append('source_file', selectedFile.value)
  data.append('source_file_name', selectedFile.value.name)
  uploading.value = true
  try {
    const template = await formsApi.createTemplate(data)
    message.success('Excel 表格已保存，可以下发')
    await loadTemplates()
    form.templateId = template.id
  } finally { uploading.value = false }
}
const payload = () => {
  if (!form.templateId) throw new Error('请先选择表格')
  if (batchMode.value === 'new' && (!form.batchName || !form.deadlineAt)) throw new Error('请填写新建批次名称和截止时间')
  if (batchMode.value === 'existing' && !form.batchId) throw new Error('请选择要追加的填报批次')
  if (recipientMode.value === 'selected' && !form.userIds.length) throw new Error('请至少选择一名填报人员')
  const result = {
    rules: [{
      template_id: form.templateId,
      receiver_type: 'USER',
      receiver_expr_json: recipientMode.value === 'all' ? { all_users: true } : { user_ids: form.userIds }
    }]
  }
  if (batchMode.value === 'new') {
    result.batch_name = form.batchName
    result.deadline_at = new Date(form.deadlineAt).toISOString()
  } else result.batch_id = form.batchId
  return result
}
const preview = async () => {
  try {
    const result = await formsApi.previewDispatch(payload())
    previewItems.value = result.tasks || []
    previewOpen.value = true
  } catch (error) { message.error(error.message || '无法预览下发名单') }
}
const publish = async () => {
  try {
    publishing.value = true
    const result = await formsApi.publishDispatch(payload())
    message.success(`下发成功，已创建 ${result.summary.created_tasks} 个任务`)
    form.userIds = []
    await loadBatches()
  } catch (error) { message.error(error.response?.data?.detail || error.message || '下发失败') } finally { publishing.value = false }
}

const dispatchSchema = { type: 'object', properties: { templateId: { type: 'integer', minimum: 1 }, batchMode: { type: 'string', enum: ['new', 'existing'] }, batchName: { type: 'string' }, batchId: { type: 'integer', minimum: 1 }, deadlineAt: { type: 'string', description: '新批次截止时间，ISO 日期或本地日期时间字符串' }, recipientMode: { type: 'string', enum: ['selected', 'all'] }, userIds: { type: 'array', items: { type: 'integer', minimum: 1 }, uniqueItems: true } }, required: ['templateId', 'batchMode', 'recipientMode'], additionalProperties: false }
const stageDispatch = async input => {
  const template = templates.value.find(item => item.id === input.templateId); if (!template) throw new Error('未找到指定的可用模板，请先读取下发选项')
  if (input.batchMode === 'new' && (!input.batchName?.trim() || !input.deadlineAt)) throw new Error('新建批次必须提供批次名称和截止时间')
  if (input.batchMode === 'existing' && !batches.value.some(item => item.id === input.batchId && item.status !== 'CLOSED')) throw new Error('未找到可追加的填报批次')
  if (input.recipientMode === 'selected') { if (!input.userIds?.length) throw new Error('请选择至少一名填报人员'); const known = new Set(users.value.map(item => item.id)); const unknown = input.userIds.find(id => !known.has(id)); if (unknown) throw new Error(`未知用户 ID：${unknown}`) }
  Object.assign(form, { templateId: input.templateId, batchId: input.batchId, batchName: input.batchName?.trim() || '', deadlineAt: input.deadlineAt || null, userIds: input.userIds ? [...input.userIds] : [] }); batchMode.value = input.batchMode; recipientMode.value = input.recipientMode; await nextTick()
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_form_dispatch_options', title: '读取表单下发选项', description: '读取可用 Excel 模板、可选人员及未关闭批次，不会下发表单。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await Promise.all([loadTemplates(), loadUsers(), loadBatches()]); return { templates: templates.value.map(({ id, name, code }) => ({ id, name, code })), users: users.value.map(({ id, username, real_name }) => ({ id, username, realName: real_name })), batches: batchOptions.value } }
    },
    {
      name: 'stage_openhrm_form_dispatch', title: '配置表单下发', description: '在当前页面填写下发批次、接收人员和截止时间，仅暂存，不会创建任务。', inputSchema: dispatchSchema, annotations: { readOnlyHint: false },
      async execute(input) { await stageDispatch(input); return { status: 'staged', templateId: form.templateId, batchMode: batchMode.value, recipientMode: recipientMode.value, recipientCount: recipientMode.value === 'all' ? users.value.length : form.userIds.length } }
    },
    {
      name: 'preview_openhrm_form_dispatch', title: '预览表单下发', description: '预览所配置的表单下发任务，不会创建批次或任务。', inputSchema: dispatchSchema, annotations: { readOnlyHint: true },
      async execute(input) { await stageDispatch(input); const result = await formsApi.previewDispatch(payload()); previewItems.value = result.tasks || []; previewOpen.value = true; return { taskCount: previewItems.value.length, tasks: previewItems.value.map(({ template_name, assignee_name, org_unit }) => ({ templateName: template_name, assigneeName: assignee_name, orgUnit: org_unit })) } }
    },
    {
      name: 'complete_openhrm_form_dispatch', title: '下发表单任务', description: '创建表单下发批次和接收人任务，或向现有批次追加任务；这是会写入系统并通知接收范围的操作。', inputSchema: dispatchSchema, annotations: { readOnlyHint: false },
      async execute(input) { await stageDispatch(input); publishing.value = true; try { const result = await formsApi.publishDispatch(payload()); await loadBatches(); form.userIds = []; message.success(`下发成功，已创建 ${result.summary.created_tasks} 个任务`); return { status: 'published', batchId: result.batch?.id, createdTasks: result.summary.created_tasks } } finally { publishing.value = false } }
    },
    {
      name: 'stage_openhrm_excel_template_upload', title: '配置 Excel 表单模板', description: '填写 Excel 模板名称和编码；文件需先通过当前页面文件选择器暂存，此操作不会上传文件。', inputSchema: { type: 'object', properties: { name: { type: 'string', minLength: 1 }, code: { type: 'string', minLength: 1 } }, required: ['name', 'code'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { upload.name = input.name.trim(); upload.code = input.code.trim(); await nextTick(); return { status: selectedFile.value ? 'file_staged' : 'awaiting_file', acceptedFileTypes: ['.xlsx', '.xls'] } }
    },
    {
      name: 'complete_openhrm_excel_template_upload', title: '上传 Excel 表单模板', description: '将页面中已选择的 Excel 文件上传为新表单模板；这是会上传文件并创建模板的操作。', inputSchema: { type: 'object', properties: { name: { type: 'string', minLength: 1 }, code: { type: 'string', minLength: 1 } }, required: ['name', 'code'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { upload.name = input.name.trim(); upload.code = input.code.trim(); if (!selectedFile.value) throw new Error('请先通过页面文件选择器暂存 .xlsx 或 .xls 文件'); await uploadTemplate(); return { status: 'uploaded', templateId: form.templateId, name: upload.name, code: upload.code } }
    }
  ])
}
onMounted(() => { registerWebMcpTools(); loadTemplates(); loadUsers(); loadBatches() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.section-card { min-height: 520px; }
.dispatch-form { margin-top: 20px; }
.preview-alert { margin-bottom: 16px; }
.form-hint { margin-top: 6px; color: #8c8c8c; font-size: 12px; }
.batch-info { margin-bottom: 16px; }
</style>
