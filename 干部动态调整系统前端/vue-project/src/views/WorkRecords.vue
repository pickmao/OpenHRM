<template>
  <div class="work-records">
    <a-page-header title="知事识人纪实" sub-title="记录本人完成的急难险重任务和突出任务" />
    <a-card>
      <a-space wrap class="toolbar">
        <a-button type="primary" @click="openEditor()">新增纪实</a-button>
        <a-input-search v-model:value="search" placeholder="搜索任务或完成成效" allow-clear @search="reload" />
        <a-select v-model:value="category" placeholder="任务类型" allow-clear style="width: 180px" :options="categories" @change="reload" />
        <a-button @click="loadRecords">刷新</a-button>
      </a-space>
      <a-table :columns="columns" :data-source="records" row-key="id" :loading="loading" :pagination="pagination" :scroll="{ x: 800 }" @change="changePage">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'"><a-space><a-button type="link" @click="viewRecord = record">查看</a-button><a-button type="link" @click="openEditor(record)">编辑</a-button></a-space></template>
        </template>
      </a-table>
    </a-card>
    <a-modal v-model:open="editorOpen" :title="editingId ? '编辑纪实' : '新增纪实'" :confirm-loading="saving" width="700px" ok-text="保存" cancel-text="取消" @ok="save">
      <a-form ref="formRef" :model="form" layout="vertical">
        <a-form-item label="任务名称" name="title" :rules="[{ required: true, whitespace: true, message: '请输入任务名称' }]"><a-input v-model:value="form.title" :maxlength="200" /></a-form-item>
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="任务类型" name="category" :rules="[{ required: true, message: '请选择任务类型' }]"><a-select v-model:value="form.category" :options="categories" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="完成日期" name="completed_on" :rules="[{ required: true, message: '请选择完成日期' }]"><a-date-picker v-model:value="form.completed_on" value-format="YYYY-MM-DD" style="width: 100%" :disabled-date="date => date.startOf('day').valueOf() > new Date().setHours(0, 0, 0, 0)" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="承担角色"><a-input v-model:value="form.role" placeholder="例如：主导者、协助者、执行者" :maxlength="100" /></a-form-item>
        <a-form-item label="具体任务及作用发挥" name="details" :rules="[{ required: true, whitespace: true, message: '请填写具体任务及作用发挥' }]"><a-textarea v-model:value="form.details" :rows="5" /></a-form-item>
        <a-form-item label="完成成效"><a-textarea v-model:value="form.outcome" :rows="3" /></a-form-item>
      </a-form>
    </a-modal>
    <a-drawer :open="!!viewRecord" title="纪实详情" width="640" @close="viewRecord = null">
      <a-descriptions v-if="viewRecord" bordered :column="1">
        <a-descriptions-item label="任务名称">{{ viewRecord.title }}</a-descriptions-item>
        <a-descriptions-item label="任务类型">{{ viewRecord.category_display }}</a-descriptions-item>
        <a-descriptions-item label="完成日期">{{ viewRecord.completed_on }}</a-descriptions-item>
        <a-descriptions-item label="承担角色">{{ viewRecord.role || '—' }}</a-descriptions-item>
        <a-descriptions-item label="具体任务及作用发挥"><div class="record-text">{{ viewRecord.details }}</div></a-descriptions-item>
        <a-descriptions-item label="完成成效"><div class="record-text">{{ viewRecord.outcome || '—' }}</div></a-descriptions-item>
      </a-descriptions>
    </a-drawer>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/utils/request'

const categories = [{ value: 'CHALLENGING', label: '急难险重任务' }, { value: 'OUTSTANDING', label: '突出任务' }]
const columns = [{ title: '任务名称', dataIndex: 'title' }, { title: '任务类型', dataIndex: 'category_display', width: 150 }, { title: '完成日期', dataIndex: 'completed_on', width: 130 }, { title: '承担角色', dataIndex: 'role', width: 160 }, { title: '操作', key: 'action', width: 140 }]
const records = ref([]), loading = ref(false), saving = ref(false), editorOpen = ref(false)
const search = ref(''), category = ref(undefined), editingId = ref(null), viewRecord = ref(null), formRef = ref(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0, showSizeChanger: false })
const blank = () => ({ title: '', category: 'CHALLENGING', completed_on: null, role: '', details: '', outcome: '' })
const form = reactive(blank())
const loadRecords = async () => {
  loading.value = true
  try {
    const result = await request.get('/inspections/records/', { params: { page: pagination.current, search: search.value, category: category.value } })
    records.value = result.results || []; pagination.total = result.count || 0
  } catch (_) { message.error('纪实记录加载失败，请重试') } finally { loading.value = false }
}
const reload = () => { pagination.current = 1; loadRecords() }
const changePage = page => { pagination.current = page.current; loadRecords() }
const openEditor = async record => {
  editingId.value = record?.id || null
  Object.assign(form, blank(), record ? Object.fromEntries(Object.keys(blank()).map(key => [key, record[key]])) : {})
  editorOpen.value = true
  await nextTick(); formRef.value?.clearValidate()
}
const save = async () => {
  try { await formRef.value.validate() } catch (_) { return }
  saving.value = true
  try {
    if (editingId.value) await request.patch(`/inspections/records/${editingId.value}/`, { ...form })
    else await request.post('/inspections/records/', { ...form })
    editorOpen.value = false; message.success('纪实已保存'); pagination.current = 1; await loadRecords()
  } catch (error) {
    const data = error.response?.data
    message.error(data ? Object.values(data).flat().join('；') : '保存失败，请重试')
  } finally { saving.value = false }
}
onMounted(loadRecords)
</script>

<style scoped>
.work-records { padding: 8px 0; }
.toolbar { margin-bottom: 20px; }
.record-text { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
