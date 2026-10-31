<template>
  <div class="branch-page">
    <a-page-header title="支部管理" sub-title="维护支部，并将部门纳入所属支部；可用模板覆盖归属关系" />

    <a-card class="action-card" :bordered="false">
      <a-space :size="16" wrap>
        <a-button type="primary" @click="handleAdd">
          <PlusOutlined />
          新建支部
        </a-button>
        <a-upload :before-upload="beforeUpload" accept=".xlsx,.xls" :show-upload-list="false">
          <a-button type="primary" :loading="uploading">
            <UploadOutlined />
            上传并覆盖归属
          </a-button>
        </a-upload>
        <a-button @click="downloadTemplate">
          <DownloadOutlined />
          下载模板
        </a-button>
        <a-button @click="openCatalog" :loading="catalogLoading">各支部参考清单</a-button>
        <a-button @click="loadData" :loading="loading">
          <ReloadOutlined />
          刷新
        </a-button>
      </a-space>
      <div v-if="uploading" class="upload-progress">
        <a-progress :percent="uploadProgress" status="active" />
        <p class="progress-text">{{ uploadStatus }}</p>
      </div>
    </a-card>

    <a-card :bordered="false">
      <a-form layout="inline" class="search-form">
        <a-form-item label="支部名称">
          <a-input
            v-model:value="searchForm.search"
            placeholder="请输入支部名称"
            allow-clear
            style="width: 200px"
            @pressEnter="handleSearch"
          />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="searchForm.is_active" placeholder="全部" allow-clear style="width: 120px">
            <a-select-option :value="true">启用</a-select-option>
            <a-select-option :value="false">停用</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="handleSearch">搜索</a-button>
            <a-button @click="handleReset">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 1100 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'departments'">
            <a-space wrap v-if="record.departments?.length">
              <a-tag v-for="dept in record.departments" :key="dept.id">
                {{ dept.name }}
                <a class="tag-remove" @click.prevent="handleRemoveDepartment(record, dept)">移出</a>
              </a-tag>
            </a-space>
            <span v-else class="muted">暂无下属部门</span>
          </template>
          <template v-else-if="column.key === 'is_active'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '启用' : '停用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openAssign(record)">纳入部门</a-button>
              <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
              <a-button type="link" size="small" @click="toggleActive(record)">
                {{ record.is_active ? '停用' : '启用' }}
              </a-button>
              <a-button type="link" size="small" danger @click="handleDelete(record)">删除</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑支部' : '新建支部'"
      :confirm-loading="submitLoading"
      @ok="handleModalOk"
      @cancel="modalVisible = false"
    >
      <a-form ref="formRef" :model="formData" :rules="formRules" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="支部名称" name="name">
          <a-input v-model:value="formData.name" placeholder="请输入支部名称" />
        </a-form-item>
        <a-form-item label="支部编码" name="code">
          <a-input v-model:value="formData.code" placeholder="可选" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="formData.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="formData.is_active" checked-children="启用" un-checked-children="停用" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="assignVisible"
      title="纳入部门"
      :confirm-loading="assignLoading"
      ok-text="确认纳入"
      @ok="submitAssign"
      @cancel="assignVisible = false"
    >
      <p v-if="currentBranch" class="assign-hint">
        将部门纳入「{{ currentBranch.name }}」。一个部门同一时间只属于一个支部，已归属其他支部的部门会改挂到本支部。
      </p>
      <a-select
        v-model:value="selectedDepartmentIds"
        mode="multiple"
        show-search
        :filter-option="filterDepartment"
        placeholder="选择要纳入的部门"
        style="width: 100%"
        :options="assignableOptions"
      />
    </a-modal>

    <a-modal v-model:open="importResultVisible" title="导入结果" :footer="null" width="640">
      <a-result :status="importResult.error_count > 0 ? 'warning' : 'success'" :title="importResult.message">
        <template #subTitle>
          <a-space :size="24" wrap>
            <a-statistic title="解析行数" :value="importResult.total" />
            <a-statistic title="按模板归属" :value="importResult.success_count" :value-style="{ color: '#52c41a' }" />
            <a-statistic title="新纳入" :value="importResult.assigned_count || 0" />
            <a-statistic v-if="importResult.mode === 'replace'" title="移出原支部" :value="importResult.unassigned_count || 0" :value-style="{ color: '#fa8c16' }" />
            <a-statistic title="失败" :value="importResult.error_count" :value-style="{ color: '#f5222d' }" />
          </a-space>
        </template>
        <template #extra>
          <div v-if="importResult.errors?.length">
            <a-divider>错误详情</a-divider>
            <a-list :data-source="importResult.errors" size="small">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>第 {{ item.row }} 行 · {{ item.branch_name || '-' }} / {{ item.department_name || '-' }}</template>
                    <template #description>{{ item.error }}</template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </div>
          <a-button type="primary" @click="importResultVisible = false">关闭</a-button>
        </template>
      </a-result>
    </a-modal>
    <a-modal v-model:open="catalogVisible" title="各支部参考清单（27 个单位）" width="900px"
      ok-text="应用组织归属" :confirm-loading="catalogApplying"
      :ok-button-props="{ disabled: !catalog.can_apply || catalogLoading }" @ok="applyCatalog">
      <a-alert type="info" show-icon style="margin-bottom: 16px"
        message="按照片整理部门归属；机关支部合并所辖科室，监区和医院分别设置支部。"
        description="人名暂待核对。政工联系人不自动认定为书记；纸质版为报送提示，不代表已提交。清单只补建缺少的组织和归属，重复应用不会重复创建。" />
      <a-alert v-if="catalog.errors.length" type="error" show-icon message="请先处理以下归属冲突，本次不会修改任何组织。" style="margin-bottom: 16px">
        <template #description><div v-for="error in catalog.errors" :key="error">{{ error }}</div></template>
      </a-alert>
      <a-table :data-source="catalog.rows" :pagination="false" row-key="order" size="small" :scroll="{ y: 450 }">
        <a-table-column title="支部" key="name" data-index="name" />
        <a-table-column title="支部处理" key="action" data-index="action" />
        <a-table-column title="所辖部门" key="departments">
          <template #default="{ record }">
            <div v-for="department in record.departments" :key="department.name">{{ department.name }}（{{ department.action }}）</div>
          </template>
        </a-table-column>
      </a-table>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  PlusOutlined,
  UploadOutlined,
  DownloadOutlined,
  ReloadOutlined
} from '@ant-design/icons-vue'
import {
  getBranchList,
  createBranch,
  updateBranch,
  deleteBranch,
  getAssignableDepartments,
  assignDepartmentsToBranch,
  removeDepartmentsFromBranch,
  downloadBranchTemplate,
  uploadBranchExcel,
  getBranchCatalog,
  applyBranchCatalog
} from '@/api/org'

const loading = ref(false)
const catalogVisible = ref(false)
const catalogLoading = ref(false)
const catalogApplying = ref(false)
const catalog = ref({ rows: [], errors: [], can_apply: false })
const openCatalog = async () => {
  catalogLoading.value = true
  catalog.value = { rows: [], errors: [], can_apply: false }
  try {
    catalog.value = await getBranchCatalog()
    catalogVisible.value = true
  } catch (error) {
    message.error(error.response?.data?.error || '读取各支部清单失败')
  } finally {
    catalogLoading.value = false
  }
}
const applyCatalog = async () => {
  catalogApplying.value = true
  try {
    const result = await applyBranchCatalog()
    message.success(`已新增 ${result.created_branches} 个支部、${result.created_departments} 个部门，设置 ${result.assigned} 项归属`)
    catalogVisible.value = false
    await loadData()
  } catch (error) {
    message.error(error.response?.data?.error || '应用清单失败')
    await openCatalog()
  } finally {
    catalogApplying.value = false
  }
}
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const dataSource = ref([])
const modalVisible = ref(false)
const assignVisible = ref(false)
const importResultVisible = ref(false)
const submitLoading = ref(false)
const assignLoading = ref(false)
const isEdit = ref(false)
const currentRecord = ref(null)
const currentBranch = ref(null)
const formRef = ref()
const selectedDepartmentIds = ref([])
const assignableDepartments = ref([])

const searchForm = reactive({
  search: '',
  is_active: undefined
})

const formData = reactive({
  name: '',
  code: '',
  sort_order: 0,
  is_active: true
})

const formRules = {
  name: [{ required: true, message: '请输入支部名称', trigger: 'blur' }]
}

const columns = [
  { title: '支部名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '下属部门数', dataIndex: 'department_count', key: 'department_count', width: 110 },
  { title: '下属部门', key: 'departments' },
  { title: '状态', key: 'is_active', width: 90 },
  { title: '操作', key: 'action', width: 280, fixed: 'right' }
]

const importResult = reactive({
  message: '',
  mode: 'replace',
  total: 0,
  success_count: 0,
  assigned_count: 0,
  unassigned_count: 0,
  error_count: 0,
  errors: []
})

const assignableOptions = ref([])

const loadData = async () => {
  loading.value = true
  try {
    const params = { ...searchForm }
    Object.keys(params).forEach(key => {
      if (params[key] === undefined || params[key] === '') delete params[key]
    })
    const response = await getBranchList(params)
    dataSource.value = Array.isArray(response) ? response : (response.results || [])
  } catch (error) {
    message.error(error.response?.data?.error || '加载支部列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => loadData()
const handleReset = () => {
  searchForm.search = ''
  searchForm.is_active = undefined
  loadData()
}

const resetForm = () => {
  formData.name = ''
  formData.code = ''
  formData.sort_order = 0
  formData.is_active = true
  formRef.value?.clearValidate()
}

const handleAdd = () => {
  isEdit.value = false
  currentRecord.value = null
  resetForm()
  modalVisible.value = true
}

const handleEdit = (record) => {
  isEdit.value = true
  currentRecord.value = record
  formData.name = record.name
  formData.code = record.code || ''
  formData.sort_order = record.sort_order || 0
  formData.is_active = record.is_active !== false
  modalVisible.value = true
}

const handleModalOk = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    const payload = {
      name: formData.name,
      code: formData.code || null,
      sort_order: formData.sort_order,
      is_active: formData.is_active
    }
    if (isEdit.value) {
      await updateBranch(currentRecord.value.id, payload)
      message.success('支部已更新')
    } else {
      await createBranch(payload)
      message.success('支部已创建')
    }
    modalVisible.value = false
    await loadData()
  } catch (error) {
    if (!error.errorFields) {
      message.error(error.response?.data?.error || error.response?.data?.name?.[0] || '保存失败')
    }
  } finally {
    submitLoading.value = false
  }
}

const toggleActive = (record) => {
  const next = !record.is_active
  Modal.confirm({
    title: next ? '启用支部' : '停用支部',
    content: `确定要${next ? '启用' : '停用'}「${record.name}」吗？${next ? '' : '停用后填报进度仍可按历史归属查找。'}`,
    onOk: async () => {
      await updateBranch(record.id, { is_active: next })
      message.success(next ? '已启用' : '已停用')
      await loadData()
    }
  })
}

const handleDelete = (record) => {
  Modal.confirm({
    title: '删除支部',
    content: `确定删除「${record.name}」吗？有下属部门时无法删除，请先移出或改为停用。`,
    okType: 'danger',
    onOk: async () => {
      try {
        await deleteBranch(record.id)
        message.success('已删除')
        await loadData()
      } catch (error) {
        message.error(error.response?.data?.error || '删除失败')
      }
    }
  })
}

const openAssign = async (record) => {
  currentBranch.value = record
  selectedDepartmentIds.value = (record.departments || []).map(item => item.id)
  const list = await getAssignableDepartments()
  assignableDepartments.value = Array.isArray(list) ? list : []
  assignableOptions.value = assignableDepartments.value.map(item => ({
    value: item.id,
    label: item.branch_name && item.branch_id !== record.id
      ? `${item.name}（当前：${item.branch_name}）`
      : item.name
  }))
  assignVisible.value = true
}

const filterDepartment = (input, option) => (option.label || '').toLowerCase().includes((input || '').toLowerCase())

const submitAssign = async () => {
  if (!currentBranch.value) return
  const currentIds = new Set((currentBranch.value.departments || []).map(item => item.id))
  const nextIds = selectedDepartmentIds.value || []
  const toAdd = nextIds.filter(id => !currentIds.has(id))
  const toRemove = [...currentIds].filter(id => !nextIds.includes(id))
  assignLoading.value = true
  try {
    if (toAdd.length) {
      await assignDepartmentsToBranch(currentBranch.value.id, toAdd)
    }
    if (toRemove.length) {
      await removeDepartmentsFromBranch(currentBranch.value.id, toRemove)
    }
    message.success('支部部门归属已更新')
    assignVisible.value = false
    await loadData()
  } catch (error) {
    message.error(error.response?.data?.error || '更新归属失败')
  } finally {
    assignLoading.value = false
  }
}

const handleRemoveDepartment = (branch, dept) => {
  Modal.confirm({
    title: '移出支部',
    content: `将「${dept.name}」从「${branch.name}」移出？移出后该部门暂不属于任何支部。`,
    onOk: async () => {
      await removeDepartmentsFromBranch(branch.id, [dept.id])
      message.success('已移出')
      await loadData()
    }
  })
}

const beforeUpload = (file) => {
  const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
  if (!isExcel) {
    message.error('只能上传 Excel 文件')
    return false
  }
  Modal.confirm({
    title: '覆盖导入支部-部门关系？',
    content: `将按「${file.name}」重建部门归属哪个支部。模板中的部门会改挂到对应支部；当前已挂在支部下但不在模板中的部门会移出支部。不会删除组织机构。找不到的支部或部门将整表报错。是否继续？`,
    okText: '确认覆盖导入',
    okType: 'danger',
    cancelText: '取消',
    onOk: () => handleUpload(file)
  })
  return false
}

const handleUpload = async (file) => {
  const formDataPayload = new FormData()
  formDataPayload.append('file', file)
  formDataPayload.append('replace', 'true')
  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = '正在上传文件...'
  try {
    uploadStatus.value = '正在解析并覆盖归属...'
    const response = await uploadBranchExcel(formDataPayload, (event) => {
      if (event.total) {
        uploadProgress.value = Math.round((event.loaded * 100) / event.total)
      }
    })
    uploadProgress.value = 100
    uploadStatus.value = '覆盖导入完成'
    Object.assign(importResult, {
      message: '',
      mode: 'replace',
      total: 0,
      success_count: 0,
      assigned_count: 0,
      unassigned_count: 0,
      error_count: 0,
      errors: [],
      ...response
    })
    importResultVisible.value = true
    message.success(response.message || '支部归属已覆盖更新')
    await loadData()
  } catch (error) {
    const data = error.response?.data
    if (data?.errors?.length) {
      Object.assign(importResult, {
        message: data.error || '覆盖导入失败',
        mode: 'replace',
        total: 0,
        success_count: 0,
        assigned_count: 0,
        unassigned_count: 0,
        error_count: data.error_count || data.errors.length,
        errors: data.errors
      })
      importResultVisible.value = true
    }
    message.error(data?.error || '文件上传失败，请检查模板格式')
  } finally {
    uploading.value = false
    setTimeout(() => {
      uploadProgress.value = 0
      uploadStatus.value = ''
    }, 2000)
  }
}

const downloadTemplate = async () => {
  try {
    const response = await downloadBranchTemplate()
    const blob = response instanceof Blob
      ? response
      : new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '支部部门关系导入模板.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    message.success('已开始下载模板')
  } catch (error) {
    message.error('模板下载失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.branch-page {
  padding: 0 0 24px;
}
.action-card {
  margin-bottom: 16px;
}
.search-form {
  margin-bottom: 16px;
}
.muted {
  color: #999;
}
.assign-hint {
  margin-bottom: 12px;
  color: #666;
}
.upload-progress {
  margin-top: 12px;
  max-width: 480px;
}
.progress-text {
  margin-top: 4px;
  color: #666;
}
.tag-remove {
  margin-left: 6px;
  font-size: 12px;
}
</style>
