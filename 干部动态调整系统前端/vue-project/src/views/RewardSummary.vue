<template>
  <div class="page-shell">
    <a-page-header title="个人及集体奖励汇总" sub-title="支持原始奖励表留存、个人/集体奖励统一检索和统计" />

    <a-row :gutter="[16, 16]" class="statistics">
      <a-col :xs="24" :sm="8"><a-card><a-statistic title="奖励记录总数" :value="statistics.total" /></a-card></a-col>
      <a-col :xs="24" :sm="8"><a-card><a-statistic title="个人奖励" :value="statistics.individual_count" /></a-card></a-col>
      <a-col :xs="24" :sm="8"><a-card><a-statistic title="集体奖励" :value="statistics.collective_count" /></a-card></a-col>
    </a-row>

    <a-card size="small" class="toolbar">
      <a-space wrap>
        <a-input v-model:value="filters.search" allow-clear placeholder="名称" style="width: 160px" @pressEnter="search" />
        <a-select v-model:value="filters.recipient_type" allow-clear placeholder="奖励类型" style="width: 130px" :options="recipientTypeOptions" @change="search" />
        <a-input v-model:value="filters.award_level" allow-clear placeholder="奖励级别" style="width: 140px" @pressEnter="search" />
        <a-input-number v-model:value="filters.year_start" :min="1900" :max="2200" placeholder="起始年度" style="width: 120px" />
        <a-input-number v-model:value="filters.year_end" :min="1900" :max="2200" placeholder="截止年度" style="width: 120px" />
        <a-select v-model:value="filters.import_file" allow-clear placeholder="来源文件" style="width: 260px" :options="fileOptions" @change="search" />
        <a-button type="primary" @click="search">查询</a-button>
        <a-button v-if="canManage" @click="openCreate">新增记录</a-button>
        <a-button v-if="canManage" type="primary" ghost @click="uploadOpen = true">导入奖励汇总表</a-button>
      </a-space>
    </a-card>

    <a-alert v-if="selectedFile" type="info" show-icon class="source-alert">
      <template #message>当前来源文件：{{ selectedFile.file_name }}，已保存 {{ selectedFile.total_records }} 条记录</template>
      <template #description><a v-if="selectedFile.source_file" :href="selectedFile.source_file" target="_blank">下载留存的原始 Excel</a></template>
    </a-alert>

    <a-table :columns="columns" :data-source="records" :loading="loading" row-key="id" :pagination="pagination" @change="onTableChange">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'recipient_type'"><a-tag :color="record.recipient_type === 'INDIVIDUAL' ? 'blue' : 'purple'">{{ record.recipient_type_display }}</a-tag></template>
        <template v-else-if="column.key === 'award_content'"><a-tooltip :title="record.award_content"><span class="content-cell">{{ record.award_content || '-' }}</span></a-tooltip></template>
        <template v-else-if="column.key === 'source'"><a v-if="record.source_file" :href="record.source_file" target="_blank">{{ record.import_file_name }}</a><span v-else>{{ record.source_sheet || '手工新增' }}</span></template>
        <template v-else-if="column.key === 'action'"><a-space><a-button type="link" @click="openEdit(record)">{{ canManage ? '编辑' : '查看' }}</a-button><a-button v-if="canManage" danger type="link" @click="removeRecord(record)">删除</a-button></a-space></template>
      </template>
    </a-table>

    <a-modal v-model:open="editorOpen" :title="editingId ? (canManage ? '编辑奖励记录' : '奖励记录详情') : '新增奖励记录'" :confirm-loading="saving" :ok-button-props="{ disabled: !canManage }" :ok-text="canManage ? '保存' : '关闭'" @ok="saveRecord">
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="奖励类型" required><a-select v-model:value="editForm.recipient_type" :disabled="!canManage" :options="recipientTypeOptions" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="editForm.recipient_type === 'COLLECTIVE' ? '集体名称' : '姓名'" required><a-input v-model:value="editForm.recipient_name" :disabled="!canManage" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="奖励级别"><a-input v-model:value="editForm.award_level" :disabled="!canManage" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="批准年度"><a-input-number v-model:value="editForm.approval_year" :disabled="!canManage" :min="1900" :max="2200" style="width: 100%" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="批准时间"><a-input v-model:value="editForm.approval_date" :disabled="!canManage" type="date" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="文号"><a-input v-model:value="editForm.document_number" :disabled="!canManage" /></a-form-item></a-col>
          <a-col :span="24"><a-form-item label="奖励情况"><a-textarea v-model:value="editForm.award_content" :disabled="!canManage" :rows="3" /></a-form-item></a-col>
          <a-col :span="24"><a-form-item label="备注"><a-textarea v-model:value="editForm.remark" :disabled="!canManage" :rows="2" /></a-form-item></a-col>
        </a-row>
      </a-form>
    </a-modal>

    <a-modal v-model:open="uploadOpen" title="导入奖励汇总 Excel" :confirm-loading="uploading" @ok="submitUpload" @cancel="resetUpload">
      <a-form layout="vertical"><a-form-item label="Excel 文件" required><a-upload :max-count="1" accept=".xls,.xlsx" :before-upload="captureFile" @remove="clearFile"><a-button>选择 .xls 或 .xlsx 文件</a-button></a-upload><div class="hint">系统自动识别“姓名/集体名称、级别、批准年度、奖励情况、批准时间、文号、备注”等表头，跳过非奖励页。</div></a-form-item></a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { rewardApi } from '@/api/rewards'
import { useUserStore } from '@/stores/user'
import { registerModelContextTools } from '@/utils/webmcp'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const uploadOpen = ref(false)
const editorOpen = ref(false)
const editingId = ref(null)
const records = ref([])
const files = ref([])
const statistics = ref({ total: 0, individual_count: 0, collective_count: 0 })
const uploadFile = ref(null)
const filters = reactive({ search: '', recipient_type: undefined, award_level: '', year_start: undefined, year_end: undefined, import_file: undefined })
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const emptyForm = () => ({ recipient_type: 'INDIVIDUAL', recipient_name: '', award_level: '', approval_year: undefined, award_content: '', approval_date: '', document_number: '', remark: '' })
const editForm = reactive(emptyForm())

const recipientTypeOptions = [{ value: 'INDIVIDUAL', label: '个人奖励' }, { value: 'COLLECTIVE', label: '集体奖励' }]
const fileOptions = computed(() => files.value.map(file => ({ value: file.id, label: `${file.file_name}（${file.total_records}条）` })))
const selectedFile = computed(() => files.value.find(file => file.id === filters.import_file))
const canManage = computed(() => userStore.userInfo?.is_superuser || ['rewards:manage', 'rewards:record:manage', 'rewards:file:manage'].some(permission => userStore.hasPermission?.(permission)))
const columns = [
  { title: '名称', dataIndex: 'recipient_name', width: 130 },
  { title: '当前部门', dataIndex: 'current_department', width: 140 },
  { title: '类型', key: 'recipient_type', width: 100 },
  { title: '级别', dataIndex: 'award_level', width: 130 },
  { title: '批准年度', dataIndex: 'approval_year', width: 100 },
  { title: '奖励情况', key: 'award_content', ellipsis: true },
  { title: '批准时间', dataIndex: 'approval_date', width: 120 },
  { title: '文号', dataIndex: 'document_number', width: 180, ellipsis: true },
  { title: '来源', key: 'source', width: 160, ellipsis: true },
  { title: '操作', key: 'action', width: 140 },
]

const loadFiles = async () => { const data = await rewardApi.getFiles(); files.value = data.results || data }
const loadRecords = async () => {
  loading.value = true
  try {
    const data = await rewardApi.getRecords({ ...filters, page: pagination.current, page_size: pagination.pageSize })
    records.value = data.results || data
    pagination.total = data.count ?? records.value.length
  } finally { loading.value = false }
}
const loadStatistics = async () => { statistics.value = await rewardApi.getStatistics(filters) }
const search = async () => { pagination.current = 1; await Promise.all([loadRecords(), loadStatistics()]) }
const onTableChange = page => { pagination.current = page.current; pagination.pageSize = page.pageSize; loadRecords() }
const resetEditor = () => { Object.assign(editForm, emptyForm()); editingId.value = null }
const openCreate = () => { resetEditor(); editorOpen.value = true }
const openEdit = async record => { const detail = await rewardApi.getRecord(record.id); Object.assign(editForm, emptyForm(), detail); editingId.value = detail.id; editorOpen.value = true }
const saveRecord = async () => {
  if (!canManage.value) { editorOpen.value = false; return }
  if (!editForm.recipient_name.trim()) { message.warning('请填写名称'); return }
  saving.value = true
  try {
    if (editingId.value) await rewardApi.updateRecord(editingId.value, editForm)
    else await rewardApi.createRecord(editForm)
    message.success(editingId.value ? '奖励记录已更新' : '奖励记录已保存')
    editorOpen.value = false
    await search()
  } catch (error) { message.error(error?.response?.data?.detail || '保存失败') } finally { saving.value = false }
}
const removeRecord = record => Modal.confirm({ title: '确认删除', content: `确定删除“${record.recipient_name}”的这条奖励记录吗？`, okType: 'danger', onOk: async () => { await rewardApi.deleteRecord(record.id); message.success('已删除'); await search() } })
const captureFile = file => { uploadFile.value = file; return false }
const clearFile = () => { uploadFile.value = null }
const resetUpload = () => { uploadFile.value = null }
const submitUpload = async () => {
  if (!uploadFile.value) { message.warning('请选择奖励汇总 Excel 文件'); return }
  const form = new FormData(); form.append('file', uploadFile.value); uploading.value = true
  try {
    const result = await rewardApi.uploadFile(form)
    message.success(result.message)
    await loadFiles(); filters.import_file = result.file_id; uploadOpen.value = false; resetUpload(); await search()
  } catch (error) { message.error(error?.response?.data?.error || '导入失败') } finally { uploading.value = false }
}

const recordDraftSchema = {
  type: 'object',
  properties: {
    recordId: { type: 'string', minLength: 1, description: '编辑时指定的奖励记录 UUID；新建时省略。' },
    recipientType: { type: 'string', enum: ['INDIVIDUAL', 'COLLECTIVE'] },
    recipientName: { type: 'string', minLength: 1, maxLength: 200 },
    awardLevel: { type: 'string', maxLength: 100 },
    approvalYear: { type: ['integer', 'null'], minimum: 1900, maximum: 2200 },
    approvalDate: { type: ['string', 'null'], description: '可选 ISO 日期。' },
    documentNumber: { type: 'string', maxLength: 200 },
    awardContent: { type: 'string' },
    remark: { type: 'string' },
  },
  required: ['recipientType', 'recipientName'],
  additionalProperties: false,
}
const recordFiltersSchema = { type: 'object', properties: { search: { type: 'string' }, recipientType: { type: 'string', enum: ['INDIVIDUAL', 'COLLECTIVE'] }, awardLevel: { type: 'string' }, yearStart: { type: 'integer', minimum: 1900, maximum: 2200 }, yearEnd: { type: 'integer', minimum: 1900, maximum: 2200 }, importFileId: { type: 'string', minLength: 1, description: '来源文件 UUID。' }, page: { type: 'integer', minimum: 1 }, pageSize: { type: 'integer', minimum: 1, maximum: 100 } }, additionalProperties: false }
const toRecordPayload = input => ({ recipient_type: input.recipientType, recipient_name: input.recipientName.trim(), award_level: input.awardLevel?.trim() || '', approval_year: input.approvalYear ?? null, approval_date: input.approvalDate || null, document_number: input.documentNumber?.trim() || '', award_content: input.awardContent || '', remark: input.remark || '' })
const findRecord = recordId => {
  const record = records.value.find(item => item.id === recordId)
  if (!record) throw new Error('未找到指定奖励记录，请先读取奖励记录列表')
  return record
}
const applyRecordDraft = async input => {
  if (input.recordId) findRecord(input.recordId)
  Object.assign(editForm, emptyForm(), toRecordPayload(input))
  editingId.value = input.recordId || null
  editorOpen.value = true
  await nextTick()
}
const applyRecordFilters = async input => {
  Object.assign(filters, { search: input.search?.trim() || '', recipient_type: input.recipientType, award_level: input.awardLevel?.trim() || '', year_start: input.yearStart, year_end: input.yearEnd, import_file: input.importFileId, })
  pagination.current = input.page ?? 1
  pagination.pageSize = input.pageSize ?? 20
  await Promise.all([loadFiles(), loadRecords(), loadStatistics()])
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_reward_summary', title: '读取奖励汇总',
      description: '按可选筛选条件读取奖励汇总、来源文件与统计数据，不修改记录。', inputSchema: recordFiltersSchema, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { await applyRecordFilters(input); return { statistics: statistics.value, files: files.value.map(({ id, file_name, total_records }) => ({ id, fileName: file_name, totalRecords: total_records })), total: pagination.total, records: records.value.map(({ id, recipient_type, recipient_name, award_level, approval_year, approval_date, document_number, award_content, remark, import_file }) => ({ id, recipientType: recipient_type, recipientName: recipient_name, awardLevel: award_level, approvalYear: approval_year, approvalDate: approval_date, documentNumber: document_number, awardContent: award_content, remark, importFileId: import_file })) } }
    },
    {
      name: 'read_openhrm_reward_record', title: '读取奖励记录详情',
      description: '读取一条已加载的奖励记录详情，不修改数据。', inputSchema: { type: 'object', properties: { recordId: { type: 'string', minLength: 1, description: '奖励记录 UUID。' } }, required: ['recordId'], additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { findRecord(input.recordId); const detail = await rewardApi.getRecord(input.recordId); return { record: detail } }
    },
    {
      name: 'stage_openhrm_reward_record', title: '配置奖励记录',
      description: '在当前页面配置新建或编辑的奖励记录，不会保存。', inputSchema: recordDraftSchema, annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { await applyRecordDraft(input); return { status: 'staged', recordId: editingId.value, recipientName: editForm.recipient_name } }
    },
    {
      name: 'complete_openhrm_reward_record', title: '保存奖励记录',
      description: '新建或更新一条奖励记录；会写入本机奖励数据。', inputSchema: recordDraftSchema, annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { if (!canManage.value) throw new Error('当前用户没有管理奖励记录的权限'); await applyRecordDraft(input); saving.value = true; try { const saved = editingId.value ? await rewardApi.updateRecord(editingId.value, toRecordPayload(input)) : await rewardApi.createRecord(toRecordPayload(input)); editorOpen.value = false; await search(); return { status: editingId.value ? 'updated' : 'created', recordId: saved.id ?? editingId.value, recipientName: saved.recipient_name ?? editForm.recipient_name } } finally { saving.value = false } }
    },
    {
      name: 'complete_openhrm_reward_record_deletion', title: '删除奖励记录',
      description: '永久删除一条奖励记录；这是不可逆的本机数据删除操作。', inputSchema: { type: 'object', properties: { recordId: { type: 'string', minLength: 1, description: '奖励记录 UUID。' } }, required: ['recordId'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { if (!canManage.value) throw new Error('当前用户没有管理奖励记录的权限'); const record = findRecord(input.recordId); await rewardApi.deleteRecord(record.id); await search(); return { status: 'deleted', recordId: record.id, recipientName: record.recipient_name } }
    },
    {
      name: 'stage_openhrm_reward_excel_upload', title: '配置奖励 Excel 导入',
      description: '打开奖励 Excel 导入界面；文件需先通过页面文件选择器暂存，不会上传。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute() { uploadOpen.value = true; await nextTick(); return { status: uploadFile.value ? 'file_staged' : 'awaiting_file', acceptedFileTypes: ['.xlsx', '.xls'] } }
    },
    {
      name: 'complete_openhrm_reward_excel_upload', title: '导入奖励 Excel',
      description: '上传当前页面已选择的奖励 Excel，并导入其中的奖励记录。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute() { if (!canManage.value) throw new Error('当前用户没有导入奖励数据的权限'); if (!uploadFile.value) throw new Error('请先通过页面文件选择器暂存 .xlsx 或 .xls 文件'); const data = new FormData(); data.append('file', uploadFile.value); uploading.value = true; try { const result = await rewardApi.uploadFile(data); await Promise.all([loadFiles(), search()]); uploadOpen.value = false; resetUpload(); return { status: 'uploaded', fileId: result.file_id, message: result.message } } finally { uploading.value = false } }
    },
  ])
}

onMounted(async () => { registerWebMcpTools(); await Promise.all([loadFiles(), loadRecords(), loadStatistics()]) })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.statistics, .toolbar, .source-alert { margin-bottom: 16px; }
.content-cell { display: inline-block; max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }
.hint { margin-top: 6px; color: #8c8c8c; font-size: 12px; }
</style>
