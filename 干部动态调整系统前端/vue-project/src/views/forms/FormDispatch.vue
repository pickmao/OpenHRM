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
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import request from '@/utils/request'
import { formsApi } from '@/api/forms'

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
    templates.value = (Array.isArray(result) ? result : []).filter(item => item.source_file)
  } finally { loadingTemplates.value = false }
}
const loadUsers = async () => {
  loadingUsers.value = true
  try { users.value = await request.get('/admin/users/') } catch (_) { users.value = [] } finally { loadingUsers.value = false }
}
const loadBatches = async () => {
  loadingBatches.value = true
  try { batches.value = await formsApi.getDispatches() } finally { loadingBatches.value = false }
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

onMounted(() => { loadTemplates(); loadUsers(); loadBatches() })
</script>

<style scoped>
.page-shell { padding: 8px 0; }
.section-card { min-height: 520px; }
.dispatch-form { margin-top: 20px; }
.preview-alert { margin-bottom: 16px; }
.form-hint { margin-top: 6px; color: #8c8c8c; font-size: 12px; }
.batch-info { margin-bottom: 16px; }
</style>
