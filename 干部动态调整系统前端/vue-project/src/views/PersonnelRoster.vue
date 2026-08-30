<template>
  <div class="personnel-roster-container">
    <!-- 页面标题 -->
    <a-page-header
      title="花名册管理"
      sub-title="上传和管理干部花名册数据"
    />

    <!-- 操作区域 -->
    <a-card class="action-card" :bordered="false">
      <a-space :size="16">
        <!-- 上传按钮 -->
        <a-upload
          :before-upload="beforeUpload"
          accept=".xlsx,.xls"
          :show-upload-list="false"
        >
          <a-button type="primary" :loading="uploading">
            <UploadOutlined />
            上传 Excel 文件
          </a-button>
        </a-upload>

        <!-- 模板下载 -->
        <a-button @click="downloadTemplate">
          <DownloadOutlined />
          下载模板
        </a-button>

        <!-- 刷新 -->
        <a-button @click="loadStatistics" :loading="loading">
          <ReloadOutlined />
          刷新
        </a-button>

        <!-- 批量删除 -->
        <a-button
          v-if="selectedRowKeys.length > 0"
          danger
          @click="handleBatchDelete"
        >
          <DeleteOutlined />
          删除选中 ({{ selectedRowKeys.length }})
        </a-button>
      </a-space>

      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-progress">
        <a-progress :percent="uploadProgress" status="active" />
        <p class="progress-text">{{ uploadStatus }}</p>
      </div>
    </a-card>

    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stats-row">
      <a-col :xs="24" :sm="12" :md="6">
        <a-card>
          <a-statistic
            title="总人数"
            :value="statistics.total"
            :value-style="{ color: '#1890ff' }"
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card>
          <a-statistic
            title="部门数"
            :value="statistics.departments"
            :value-style="{ color: '#52c41a' }"
          >
            <template #prefix>
              <ApartmentOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card>
          <a-statistic
            title="男性"
            :value="statistics.male_count"
            :value-style="{ color: '#13c2c2' }"
          >
            <template #prefix>
              <ManOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card>
          <a-statistic
            title="女性"
            :value="statistics.female_count"
            :value-style="{ color: '#eb2f96' }"
          >
            <template #prefix>
              <WomanOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 数据表格 -->
    <a-card title="花名册数据" class="table-card">
      <!-- 搜索和筛选 -->
      <div class="table-filters">
        <a-space :size="8" wrap>
          <a-input-search
            v-model:value="searchText"
            placeholder="搜索姓名、部门、警号、身份证号"
            style="width: 300px"
            @search="handleSearch"
          />
          <a-select
            v-model:value="filterGender"
            placeholder="筛选性别"
            style="width: 120px"
            allow-clear
            @change="handleSearch"
          >
            <a-select-option value="M">男</a-select-option>
            <a-select-option value="F">女</a-select-option>
          </a-select>
          <a-select
            v-model:value="filterPoliticalStatus"
            placeholder="筛选政治面貌"
            style="width: 150px"
            allow-clear
            @change="handleSearch"
          >
            <a-select-option value="中共党员">中共党员</a-select-option>
            <a-select-option value="共青团员">共青团员</a-select-option>
            <a-select-option value="群众">群众</a-select-option>
          </a-select>
        </a-space>
      </div>

      <!-- 表格 -->
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :row-selection="rowSelection"
        :pagination="pagination"
        :scroll="{ x: 2000 }"
        @change="handleTableChange"
        row-key="id"
      >
        <!-- 自定义列渲染 -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'gender'">
            <a-tag :color="record.gender === 'M' ? 'blue' : record.gender === 'F' ? 'pink' : 'default'">
              {{ formatGender(record.gender) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="viewDetail(record)">
                查看详情
              </a-button>
              <a-popconfirm
                title="确定要删除这条记录吗？"
                @confirm="deleteRecord(record.id)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:open="detailVisible"
      title="花名册详情"
      width="800"
      placement="right"
    >
      <a-descriptions :column="2" bordered v-if="currentRecord">
        <a-descriptions-item label="姓名">{{ currentRecord.name }}</a-descriptions-item>
        <a-descriptions-item label="部门">{{ currentRecord.department }}</a-descriptions-item>
        <a-descriptions-item label="性别">
          <a-tag :color="currentRecord.gender === 'M' ? 'blue' : 'pink'">
            {{ formatGender(currentRecord.gender) }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="年龄">{{ currentRecord.age }}</a-descriptions-item>
        <a-descriptions-item label="警号">{{ currentRecord.police_number }}</a-descriptions-item>
        <a-descriptions-item label="身份证号">{{ currentRecord.id_card }}</a-descriptions-item>
        <a-descriptions-item label="政治面貌">{{ currentRecord.political_status }}</a-descriptions-item>
        <a-descriptions-item label="职务">{{ currentRecord.position }}</a-descriptions-item>
        <a-descriptions-item label="警员职级">{{ currentRecord.police_rank }}</a-descriptions-item>
        <a-descriptions-item label="警衔">{{ currentRecord.police_title }}</a-descriptions-item>
        <a-descriptions-item label="最高学历" :span="2">
          {{ currentRecord.highest_education }} - {{ currentRecord.highest_school }}
        </a-descriptions-item>
        <a-descriptions-item label="出生年月">{{ currentRecord.birth_date }}</a-descriptions-item>
        <a-descriptions-item label="参加工作时间">{{ currentRecord.join_work_date }}</a-descriptions-item>
        <a-descriptions-item label="电话" :span="2">{{ currentRecord.phone }}</a-descriptions-item>
        <a-descriptions-item label="备注" :span="2">{{ currentRecord.remark || '-' }}</a-descriptions-item>
      </a-descriptions>
    </a-drawer>

    <!-- 导入结果模态框 -->
    <a-modal
      v-model:open="importResultVisible"
      title="导入结果"
      :footer="null"
      width="600"
    >
      <a-result
        :status="importResult.error_count > 0 ? 'warning' : 'success'"
        :title="importResult.message"
      >
        <template #subTitle>
          <a-space :size="32">
            <a-statistic title="总行数" :value="importResult.total" />
            <a-statistic title="成功" :value="importResult.success_count" :value-style="{ color: '#52c41a' }" />
            <a-statistic title="失败" :value="importResult.error_count" :value-style="{ color: '#f5222d' }" />
          </a-space>
        </template>
        <template #extra>
          <div v-if="importResult.errors && importResult.errors.length > 0">
            <a-divider>错误详情（前10条）</a-divider>
            <a-list
              :data-source="importResult.errors"
              size="small"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>第 {{ item.row }} 行 - {{ item.name }}</template>
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
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  UploadOutlined,
  DownloadOutlined,
  ReloadOutlined,
  DeleteOutlined,
  UserOutlined,
  ApartmentOutlined,
  ManOutlined,
  WomanOutlined
} from '@ant-design/icons-vue'
import request from '@/utils/request'
import { registerModelContextTools } from '@/utils/webmcp'

// 响应式数据
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const loading = ref(false)
const dataSource = ref([])
const searchText = ref('')
const filterGender = ref(undefined)
const filterPoliticalStatus = ref(undefined)
const selectedRowKeys = ref([])
const detailVisible = ref(false)
const currentRecord = ref(null)
const importResultVisible = ref(false)

// 统计数据
const statistics = reactive({
  total: 0,
  departments: 0,
  male_count: 0,
  female_count: 0
})

// 导入结果
const importResult = reactive({
  message: '',
  total: 0,
  success_count: 0,
  error_count: 0,
  errors: []
})

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条记录`
})

// 表格列配置
const columns = [
  { title: '序号', dataIndex: 'serial_number', width: 80, fixed: 'left' },
  { title: '姓名', dataIndex: 'name', width: 100, fixed: 'left' },
  { title: '部门', dataIndex: 'department', width: 150 },
  { title: '性别', key: 'gender', width: 80 },
  { title: '年龄', dataIndex: 'age', width: 80 },
  { title: '警号', dataIndex: 'police_number', width: 120 },
  { title: '身份证号', dataIndex: 'id_card', width: 180 },
  { title: '政治面貌', dataIndex: 'political_status', width: 120 },
  { title: '职务', dataIndex: 'position', width: 150 },
  { title: '警员职级', dataIndex: 'police_rank', width: 120 },
  { title: '警衔', dataIndex: 'police_title', width: 120 },
  { title: '最高学历', dataIndex: 'highest_education', width: 120 },
  { title: '参加工作时间', dataIndex: 'join_work_date', width: 120 },
  { title: '电话', dataIndex: 'phone', width: 130 },
  { title: '创建时间', dataIndex: 'created_at', width: 160 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' }
]

// 行选择配置
const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys) => {
    selectedRowKeys.value = keys
  }
}))

// 格式化性别
const formatGender = (gender) => {
  const map = {
    'M': '男',
    'F': '女',
    'U': '未知'
  }
  return map[gender] || '未知'
}

// 上传前校验
const beforeUpload = (file) => {
  const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
  if (!isExcel) {
    message.error('只能上传 Excel 文件！')
    return false
  }
  const isLt20M = file.size / 1024 / 1024 < 20
  if (!isLt20M) {
    message.error('文件大小不能超过 20MB！')
    return false
  }

  handleUpload(file)
  return false
}

// 处理上传
const handleUpload = async (file) => {
  const formData = new FormData()
  formData.append('file', file)

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = '正在上传文件...'

  try {
    uploadProgress.value = 30
    uploadStatus.value = '正在解析文件...'

    const response = await request.post('/roster/upload-excel/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress.value = percentCompleted
      }
    })

    uploadProgress.value = 100
    uploadStatus.value = '导入完成！'

    // 显示导入结果
    Object.assign(importResult, response)
    importResultVisible.value = true

    // 刷新数据
    await Promise.all([
      loadStatistics(),
      loadData()
    ])

    message.success('文件上传成功！')
  } catch (error) {
    console.error('上传失败:', error)
    message.error(error.response?.data?.error || '文件上传失败，请检查文件格式是否正确')
  } finally {
    uploading.value = false
    setTimeout(() => {
      uploadProgress.value = 0
      uploadStatus.value = ''
    }, 2000)
  }
}

// 下载模板
const downloadTemplate = () => {
  message.info('模板功能开发中，请联系管理员获取模板文件')
}

// 加载统计数据
const loadStatistics = async () => {
  try {
    const response = await request.get('/roster/statistics/')

    statistics.total = response.total || 0
    statistics.departments = response.departments || 0

    // 统计性别
    const genderStats = response.gender_stats || []
    const maleStat = genderStats.find(item => item.gender === 'M')
    const femaleStat = genderStats.find(item => item.gender === 'F')

    statistics.male_count = maleStat?.count || 0
    statistics.female_count = femaleStat?.count || 0
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.pageSize
    }

    if (searchText.value) {
      params.search = searchText.value
    }
    if (filterGender.value) {
      params.gender = filterGender.value
    }
    if (filterPoliticalStatus.value) {
      params.political_status = filterPoliticalStatus.value
    }

    const response = await request.get('/roster/', { params })

    dataSource.value = response.results || response
    pagination.total = response.count || response.length
  } catch (error) {
    console.error('加载数据失败:', error)
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadData()
}

// 表格变化
const handleTableChange = (pag) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadData()
}

// 查看详情
const viewDetail = (record) => {
  currentRecord.value = record
  detailVisible.value = true
}

// 删除记录
const deleteRecord = async (id) => {
  try {
    await request.delete(`/roster/${id}/`)
    message.success('删除成功')
    loadData()
    loadStatistics()
  } catch (error) {
    console.error('删除失败:', error)
    message.error('删除失败')
  }
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要删除的记录')
    return
  }

  try {
    for (const id of selectedRowKeys.value) {
      await request.delete(`/roster/${id}/`)
    }
    message.success(`成功删除 ${selectedRowKeys.value.length} 条记录`)
    selectedRowKeys.value = []
    loadData()
    loadStatistics()
  } catch (error) {
    console.error('批量删除失败:', error)
    message.error('批量删除失败')
  }
}

const rosterFilterSchema = { type: 'object', properties: { search: { type: 'string', description: '姓名、部门、警号或身份证号关键词' }, gender: { type: 'string', enum: ['M', 'F'] }, politicalStatus: { type: 'string', enum: ['中共党员', '共青团员', '群众'] }, page: { type: 'integer', minimum: 1 }, pageSize: { type: 'integer', minimum: 1, maximum: 100 } }, additionalProperties: false }
const applyRosterFilters = async input => { searchText.value = input.search?.trim() || ''; filterGender.value = input.gender; filterPoliticalStatus.value = input.politicalStatus; pagination.current = input.page || 1; pagination.pageSize = input.pageSize || pagination.pageSize; await loadData(); await nextTick() }
const findRosterRecord = id => { const record = dataSource.value.find(item => item.id === id); if (!record) throw new Error('未找到指定花名册记录，请先读取花名册列表'); return record }
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_roster_statistics', title: '读取花名册统计', description: '读取花名册总人数、部门数和性别统计，不读取个人明细，也不修改数据。', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await loadStatistics(); return { total: statistics.total, departments: statistics.departments, maleCount: statistics.male_count, femaleCount: statistics.female_count } }
    },
    {
      name: 'list_openhrm_roster_records', title: '读取花名册', description: '按可选关键词、性别、政治面貌和分页读取花名册记录，不修改数据。', inputSchema: rosterFilterSchema, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { await applyRosterFilters(input); return { total: pagination.total, page: pagination.current, pageSize: pagination.pageSize, records: dataSource.value.map(({ id, serial_number, name, department, gender, age, police_number, political_status, position }) => ({ id, serialNumber: serial_number, name, department, gender, age, policeNumber: police_number, politicalStatus: political_status, position })) } }
    },
    {
      name: 'read_openhrm_roster_record', title: '读取花名册详情', description: '在当前页面打开并返回一条花名册记录详情，不修改数据。', inputSchema: { type: 'object', properties: { recordId: { type: 'integer', minimum: 1 } }, required: ['recordId'], additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) { const record = findRosterRecord(input.recordId); viewDetail(record); await nextTick(); return { record: currentRecord.value } }
    },
    {
      name: 'stage_openhrm_roster_record_selection', title: '选择花名册记录', description: '在当前页面勾选要批量处理的花名册记录，仅暂存选择，不会删除数据。', inputSchema: { type: 'object', properties: { recordIds: { type: 'array', items: { type: 'integer', minimum: 1 }, uniqueItems: true } }, required: ['recordIds'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { input.recordIds.forEach(findRosterRecord); selectedRowKeys.value = [...input.recordIds]; await nextTick(); return { status: 'staged', recordIds: selectedRowKeys.value } }
    },
    {
      name: 'complete_openhrm_roster_record_deletion', title: '删除花名册记录', description: '永久删除指定的一条花名册记录；这是不可逆的人员数据删除操作。', inputSchema: { type: 'object', properties: { recordId: { type: 'integer', minimum: 1 } }, required: ['recordId'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { const record = findRosterRecord(input.recordId); await request.delete(`/roster/${record.id}/`); await Promise.all([loadData(), loadStatistics()]); message.success('删除成功'); return { status: 'deleted', recordId: record.id, name: record.name } }
    },
    {
      name: 'complete_openhrm_roster_batch_deletion', title: '批量删除花名册记录', description: '永久删除所列花名册记录；这是不可逆的人员数据删除操作。', inputSchema: { type: 'object', properties: { recordIds: { type: 'array', items: { type: 'integer', minimum: 1 }, minItems: 1, uniqueItems: true } }, required: ['recordIds'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { const records = input.recordIds.map(findRosterRecord); await Promise.all(records.map(record => request.delete(`/roster/${record.id}/`))); selectedRowKeys.value = []; await Promise.all([loadData(), loadStatistics()]); message.success(`成功删除 ${records.length} 条记录`); return { status: 'deleted', count: records.length, recordIds: input.recordIds } }
    }
  ])
}

// 页面加载
onMounted(() => {
  registerWebMcpTools()
  loadStatistics()
  loadData()
})
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.personnel-roster-container {
  padding: 24px;
  background: #f0f2f5;
  min-height: calc(100vh - 64px - 70px);
}

.action-card {
  margin-bottom: 16px;
}

.upload-progress {
  margin-top: 16px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 4px;
}

.progress-text {
  margin: 8px 0 0 0;
  color: #666;
  font-size: 14px;
}

.stats-row {
  margin-bottom: 16px;
}

.table-card {
  margin-bottom: 16px;
}

.table-filters {
  margin-bottom: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .personnel-roster-container {
    padding: 16px;
  }

  .table-filters :deep(.ant-space) {
    width: 100%;
  }

  .table-filters :deep(.ant-input-search),
  .table-filters :deep(.ant-select) {
    width: 100% !important;
  }
}
</style>
