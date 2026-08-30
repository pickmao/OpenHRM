<template>
  <div class="page-shell">
    <a-page-header title="中层领导班子分析研判" sub-title="按研判期间选择版本；进入记录后可逐条勘误，原始 Excel 永久留存" />
    <a-card size="small" class="toolbar"><a-space wrap><a-select v-model:value="filters.file" allow-clear placeholder="选择研判期间" style="width: 360px" :options="fileOptions" @change="loadRecords" /><a-input v-model:value="filters.name" allow-clear placeholder="班子名称" style="width: 200px" @pressEnter="search" /><a-button type="primary" @click="search">查询</a-button><a-button v-if="canManage" @click="uploadOpen = true">上传本期 Excel</a-button></a-space></a-card>
    <a-alert v-if="selectedFile" type="info" show-icon class="version-alert"><template #message>当前期间：{{ selectedFile.version_date }}，共 {{ selectedFile.total_records }} 条班子记录</template><template #description>{{ selectedFile.file_name }} <a v-if="selectedFile.source_file" :href="selectedFile.source_file" target="_blank">下载原始 Excel</a></template></a-alert>
    <a-table :columns="columns" :data-source="records" :loading="loading" row-key="id" :pagination="pagination" @change="onTableChange"><template #bodyCell="{ column, record }"><template v-if="column.key === 'value'">{{ record[column.dataIndex] ?? '-' }}</template><template v-else-if="column.key === 'action'"><a-button type="link" @click="openRecord(record)">{{ canManage ? '查看/修改' : '查看' }}</a-button></template></template></a-table>
    <a-modal v-model:open="uploadOpen" title="上传领导班子研判 Excel" :confirm-loading="uploading" @ok="submitUpload" @cancel="resetUpload"><a-form layout="vertical"><a-form-item label="研判期间" required><a-input v-model:value="upload.period" type="date" /></a-form-item><a-form-item label="Excel 文件" required><a-upload :max-count="1" accept=".xlsx" :before-upload="captureFile" @remove="clearFile"><a-button>选择标准 .xlsx 文件</a-button></a-upload><div class="hint">系统会尝试从文件名预填日期；只接受实际格式为标准 .xlsx 的文件。</div></a-form-item></a-form></a-modal>
    <a-drawer v-model:open="drawerOpen" :title="detail?.name || '班子研判记录'" width="900"><a-space v-if="detail" class="drawer-actions"><a-button v-if="canManage && !editing" type="primary" @click="startEdit">编辑记录</a-button><a-button v-if="editing" @click="editing = false">取消</a-button><a-button v-if="editing" type="primary" :loading="saving" @click="saveRecord">保存修改</a-button></a-space><a-collapse v-if="detail && !editing" class="history" ghost><a-collapse-panel key="history" :header="`修改记录（${history.length}）`"><a-empty v-if="!history.length" description="暂未修改过此记录" :image-style="{ height: '42px' }" /><a-list v-else size="small" :data-source="history"><template #renderItem="{ item }"><a-list-item><a-list-item-meta :description="`${item.editor_name || '未知用户'} · ${item.created_at}`"><template #title>修改字段：{{ item.changed_fields.join('、') }}</template></a-list-item-meta><a-tooltip title="查看变更前后内容"><a-button type="link" @click="showHistory(item)">详情</a-button></a-tooltip></a-list-item></template></a-list></a-collapse-panel></a-collapse><a-descriptions v-if="detail && !editing" bordered size="small" :column="2"><a-descriptions-item v-for="field in fields" :key="field.key" :label="field.label" :span="field.type === 'textarea' ? 2 : 1">{{ detail[field.key] ?? '-' }}</a-descriptions-item></a-descriptions><a-form v-else-if="editing" layout="vertical"><a-row :gutter="16"><a-col v-for="field in fields" :key="field.key" :span="field.type === 'textarea' ? 24 : 12"><a-form-item :label="field.label"><a-input-number v-if="field.type === 'number'" v-model:value="editForm[field.key]" style="width: 100%" /><a-textarea v-else-if="field.type === 'textarea'" v-model:value="editForm[field.key]" :rows="3" /><a-input v-else v-model:value="editForm[field.key]" /></a-form-item></a-col></a-row></a-form></a-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { leadershipAssessmentApi } from '@/api/assessments'
import { useUserStore } from '@/stores/user'
import { registerModelContextTools } from '@/utils/webmcp'

const userStore = useUserStore(); const loading = ref(false); const files = ref([]); const records = ref([]); const detail = ref(null); const history = ref([]); const drawerOpen = ref(false); const editing = ref(false); const saving = ref(false); const uploadOpen = ref(false); const uploading = ref(false)
const filters = reactive({ file: undefined, name: '' }); const pagination = reactive({ current: 1, pageSize: 20, total: 0 }); const upload = reactive({ period: null, file: null }); const editForm = reactive({})
const canManage = computed(() => userStore.userInfo?.is_superuser || ['assessments:manage', 'leadership:record:manage', 'leadership:file:manage'].some(permission => userStore.hasPermission?.(permission)))
const fields = [['name', '班子名称'], ['leadership_count', '领导现有人数', 'number'], ['vacancy_count', '空缺人数', 'number'], ['team_leader_count', '团队负责人人数', 'number'], ['team_leader_vacancy_count', '团队负责人空缺数', 'number'], ['average_age', '平均年龄', 'number'], ['max_age', '最大年龄', 'number'], ['min_age', '最小年龄', 'number'], ['postgraduate_count', '研究生人数', 'number'], ['undergraduate_count', '本科人数', 'number'], ['college_below_count', '大专及以下人数', 'number'], ['over_5_years_count', '任现职超过五年', 'number'], ['three_to_5_years_count', '任现职三至五年', 'number'], ['under_3_years_count', '任现职未满三年', 'number'], ['long_term_office_count', '长期机关工作人数', 'number'], ['balanced_count', '经历相对均衡人数', 'number'], ['long_term_prison_count', '长期监区工作人数', 'number'], ['ability_assessment', '能力评价', 'textarea'], ['performance_2023', '干事评价（2023）', 'textarea'], ['performance_2024', '干事评价（2024）', 'textarea'], ['shortcomings', '存在不足', 'textarea'], ['secretary_score', '支部书记评价分', 'number'], ['democratic_score', '民主测评分', 'number'], ['total_score', '得分', 'number'], ['approval_rate', '认可率', 'number'], ['ranking', '排名', 'number'], ['adjustment_suggestion', '调整建议', 'textarea']].map(([key, label, type = 'text']) => ({ key, label, type }))
const columns = [{ title: '班子名称', dataIndex: 'name' }, { title: '领导人数', dataIndex: 'leadership_count', key: 'value', width: 110 }, { title: '空缺人数', dataIndex: 'vacancy_count', key: 'value', width: 110 }, { title: '平均年龄', dataIndex: 'average_age', key: 'value', width: 110 }, { title: '总分', dataIndex: 'total_score', key: 'value', width: 90 }, { title: '排名', dataIndex: 'ranking', key: 'value', width: 80 }, { title: '操作', key: 'action', width: 100 }]
const fileOptions = computed(() => files.value.map(item => ({ value: item.id, label: `${item.version_date} · ${item.file_name}` }))); const selectedFile = computed(() => files.value.find(item => item.id === filters.file))
const loadFiles = async () => { const data = await leadershipAssessmentApi.getFiles(); files.value = data.results || data }; const loadRecords = async () => { loading.value = true; try { const data = await leadershipAssessmentApi.getRecords({ ...filters, page: pagination.current, page_size: pagination.pageSize }); records.value = data.results || data; pagination.total = data.count || records.value.length } finally { loading.value = false } }; const search = async () => { pagination.current = 1; await loadRecords() }; const onTableChange = page => { pagination.current = page.current; pagination.pageSize = page.pageSize; loadRecords() }
const openRecord = async record => { [detail.value, history.value] = await Promise.all([leadershipAssessmentApi.getRecord(record.id), leadershipAssessmentApi.getRecordHistory(record.id)]); editing.value = false; drawerOpen.value = true }; const startEdit = () => { fields.forEach(field => { editForm[field.key] = detail.value[field.key] }); editing.value = true }; const saveRecord = async () => { saving.value = true; try { detail.value = await leadershipAssessmentApi.updateRecord(detail.value.id, Object.fromEntries(fields.map(field => [field.key, editForm[field.key]]))); history.value = await leadershipAssessmentApi.getRecordHistory(detail.value.id); editing.value = false; message.success('记录已修改并已留痕'); loadRecords() } finally { saving.value = false } }; const showHistory = item => message.info(`修改前：${JSON.stringify(item.before_values)}\n修改后：${JSON.stringify(item.after_values)}`, 8)
const captureFile = file => { upload.file = file; const match = file.name.match(/(\d{4})(\d{2})(\d{2})/); if (match && !upload.period) upload.period = `${match[1]}-${match[2]}-${match[3]}`; return false }
const clearFile = () => { upload.file = null }
const resetUpload = () => { upload.period = null; upload.file = null }
const submitUpload = async () => {
  if (!upload.period || !upload.file) {
    const error = '请选择研判期间和 Excel 文件'
    message.warning(error)
    throw new Error(error)
  }
  const form = new FormData()
  form.append('version_date', upload.period)
  form.append('file', upload.file)
  uploading.value = true
  try {
    const result = await leadershipAssessmentApi.uploadFile(form)
    const response = { fileId: result.file_id, fileName: result.file_name, totalRecords: result.total_records }
    message.success(result.message)
    await loadFiles()
    filters.file = result.file_id
    await search()
    uploadOpen.value = false
    resetUpload()
    return response
  } catch (error) {
    const detail = error?.response?.data?.error || '导入失败'
    message.error(detail)
    throw new Error(detail)
  } finally {
    uploading.value = false
  }
}

let unregisterWebMcpTools = () => {}

const registerUploadTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_leadership_assessment_records',
      title: '读取领导班子研判记录',
      description: '按可选文件版本和班子名称读取领导班子研判记录及文件版本，不修改数据。',
      inputSchema: { type: 'object', properties: { fileId: { type: 'integer', minimum: 1 }, name: { type: 'string' } }, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { filters.file = input.fileId; filters.name = input.name?.trim() || ''; await Promise.all([loadFiles(), search()]); return { total: pagination.total, files: files.value.map(({ id, version_date, file_name }) => ({ id, versionDate: version_date, fileName: file_name })), records: records.value.map(({ id, name, leadership_count, vacancy_count, average_age, total_score, ranking }) => ({ id, name, leadershipCount: leadership_count, vacancyCount: vacancy_count, averageAge: average_age, totalScore: total_score, ranking })) } }
    },
    {
      name: 'read_openhrm_leadership_assessment_record',
      title: '读取领导班子研判详情',
      description: '读取一条领导班子研判记录及其修改历史，不修改数据。',
      inputSchema: { type: 'object', properties: { recordId: { type: 'integer', minimum: 1 } }, required: ['recordId'], additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { const record = records.value.find(item => item.id === input.recordId); if (!record) throw new Error('未找到指定记录，请先读取研判记录列表'); await openRecord(record); return { record: detail.value, history: history.value } }
    },
    {
      name: 'stage_openhrm_leadership_assessment_record_update',
      title: '配置领导班子研判修改',
      description: '在当前记录详情页暂存可编辑研判字段，不会保存到系统。',
      inputSchema: { type: 'object', properties: { recordId: { type: 'integer', minimum: 1 }, values: { type: 'object', additionalProperties: true, description: '以字段名为键的修改值；字段必须来自记录详情的可编辑字段' } }, required: ['recordId', 'values'], additionalProperties: false },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { if (!canManage.value) throw new Error('当前用户没有修改领导班子研判记录的权限'); const record = records.value.find(item => item.id === input.recordId); if (!record) throw new Error('未找到指定记录，请先读取研判记录列表'); const allowed = new Set(fields.map(item => item.key)); const invalid = Object.keys(input.values).find(key => !allowed.has(key)); if (invalid) throw new Error(`不支持修改字段：${invalid}`); await openRecord(record); startEdit(); Object.assign(editForm, input.values); return { status: 'staged', recordId: detail.value.id, fields: Object.keys(input.values) } }
    },
    {
      name: 'complete_openhrm_leadership_assessment_record_update',
      title: '保存领导班子研判修改',
      description: '保存指定领导班子研判记录的修改，并写入修改历史；这是会修改研判数据的操作。',
      inputSchema: { type: 'object', properties: { recordId: { type: 'integer', minimum: 1 }, values: { type: 'object', additionalProperties: true } }, required: ['recordId', 'values'], additionalProperties: false },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) { if (!canManage.value) throw new Error('当前用户没有修改领导班子研判记录的权限'); const record = records.value.find(item => item.id === input.recordId); if (!record) throw new Error('未找到指定记录，请先读取研判记录列表'); const allowed = new Set(fields.map(item => item.key)); const invalid = Object.keys(input.values).find(key => !allowed.has(key)); if (invalid) throw new Error(`不支持修改字段：${invalid}`); await openRecord(record); startEdit(); Object.assign(editForm, input.values); await saveRecord(); return { status: 'saved', recordId: detail.value.id, fields: Object.keys(input.values) } }
    },
    {
      name: 'start_leadership_assessment_excel_upload',
      title: '开始上传领导班子研判 Excel',
      description: '打开领导班子研判 Excel 上传流程。在调用完成上传工具前，先通过页面文件选择器暂存一个标准 .xlsx 文件。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      execute() {
        if (!canManage.value) throw new Error('当前用户没有上传领导班子研判文件的权限')
        resetUpload()
        uploadOpen.value = true
        return { status: 'awaiting_file', acceptedFileType: '.xlsx' }
      },
    },
    {
      name: 'complete_leadership_assessment_excel_upload',
      title: '完成上传领导班子研判 Excel',
      description: '上传已通过页面文件选择器暂存的领导班子研判 Excel，并将其关联到指定研判期间。',
      inputSchema: {
        type: 'object',
        properties: { period: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' } },
        required: ['period'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) {
        if (!canManage.value) throw new Error('当前用户没有上传领导班子研判文件的权限')
        if (!input || typeof input.period !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(input.period)) {
          throw new Error('研判期间必须为 YYYY-MM-DD 格式')
        }
        if (!upload.file) throw new Error('请先通过页面文件选择器暂存标准 .xlsx 文件')
        upload.period = input.period
        return submitUpload()
      },
    },
  ])
}

onMounted(async () => { registerUploadTools(); await loadFiles(); await loadRecords() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>.page-shell { padding: 8px 0; }.toolbar, .version-alert, .history { margin-bottom: 16px; }.hint { margin-top: 6px; color: #8c8c8c; font-size: 12px; }.drawer-actions { margin-bottom: 16px; }</style>
