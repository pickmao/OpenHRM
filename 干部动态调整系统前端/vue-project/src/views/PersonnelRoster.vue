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
            上传并覆盖花名册
          </a-button>
        </a-upload>

        <!-- 模板下载 -->
        <a-button @click="downloadTemplate">
          <DownloadOutlined />
          下载模板
        </a-button>

        <!-- 刷新 -->
        <a-button @click="refreshAll" :loading="loading || statsLoading">
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
      <div class="upload-hint">上传新表会清空并覆盖当前全部花名册记录，请先确认文件无误。</div>

      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-progress">
        <a-progress :percent="uploadProgress" status="active" />
        <p class="progress-text">{{ uploadStatus }}</p>
      </div>
    </a-card>

    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stats-row">
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="总人数"
            :value="statsError ? '—' : statistics.total"
            :value-style="{ color: statsError ? '#999' : '#1890ff' }"
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="部门数"
            :value="statsError ? '—' : statistics.departments"
            :value-style="{ color: statsError ? '#999' : '#52c41a' }"
          >
            <template #prefix>
              <ApartmentOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="男性"
            :value="statsError ? '—' : statistics.male_count"
            :value-style="{ color: statsError ? '#999' : '#13c2c2' }"
          >
            <template #prefix>
              <ManOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="6">
        <a-card :loading="statsLoading">
          <a-statistic
            title="女性"
            :value="statsError ? '—' : statistics.female_count"
            :value-style="{ color: statsError ? '#999' : '#eb2f96' }"
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
      <a-alert
        v-if="listError"
        type="error"
        show-icon
        message="人员列表加载失败"
        :description="listError"
        style="margin-bottom: 16px"
      >
        <template #action>
          <a-button size="small" @click="loadData">重试</a-button>
        </template>
      </a-alert>

      <!-- 搜索和筛选 -->
      <div class="table-filters">
        <a-space :size="8" wrap>
          <a-radio-group v-model:value="leadershipScope" @change="handleSearch">
            <a-radio-button value="all">全部人员</a-radio-button>
            <a-radio-button value="middle">中层领导（含团队负责人）</a-radio-button>
          </a-radio-group>
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
          <a-checkbox-group v-model:value="visibleExtraColumns" :options="extraColumnOptions" />
        </a-space>
      </div>

      <!-- 表格 -->
      <a-table
        :columns="displayColumns"
        :data-source="dataSource"
        :loading="loading"
        :row-selection="rowSelection"
        :pagination="pagination"
        :scroll="{ x: tableScrollX }"
        :locale="{ emptyText: emptyText }"
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
      width="900"
      placement="right"
    >
      <template v-if="currentRecord">
        <a-descriptions :column="2" bordered size="small">
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
          <a-descriptions-item label="职务类别">{{ currentRecord.position_category || '-' }}</a-descriptions-item>
          <a-descriptions-item label="级别">{{ currentRecord.position_level || '-' }}</a-descriptions-item>
          <a-descriptions-item label="任职年限">{{ currentRecord.current_position_years || '-' }}</a-descriptions-item>
          <a-descriptions-item label="任现职时间">{{ currentRecord.current_position_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="任级年限">{{ currentRecord.current_rank_years || '-' }}</a-descriptions-item>
          <a-descriptions-item label="任级时间">{{ currentRecord.current_rank_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="职务层次">{{ currentRecord.position_rank || '-' }}</a-descriptions-item>
          <a-descriptions-item label="警员职级">{{ currentRecord.police_rank || '-' }}</a-descriptions-item>
          <a-descriptions-item label="警衔">{{ currentRecord.police_title }}</a-descriptions-item>
          <a-descriptions-item label="是否干事">{{ currentRecord.is_clerk || '-' }}</a-descriptions-item>
          <a-descriptions-item label="任干事时间">{{ currentRecord.clerk_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="进入单位形式">{{ currentRecord.enter_unit_form || '-' }}</a-descriptions-item>
          <a-descriptions-item label="本部门工作时间">{{ currentRecord.dept_work_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="进入本单位时间">{{ currentRecord.enter_unit_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="最高学历" :span="2">
            {{ currentRecord.highest_education }} - {{ currentRecord.highest_major || currentRecord.highest_school || '' }}
          </a-descriptions-item>
          <a-descriptions-item label="最高学位">{{ currentRecord.highest_degree || '-' }}</a-descriptions-item>
          <a-descriptions-item label="出生年月">{{ currentRecord.birth_date }}</a-descriptions-item>
          <a-descriptions-item label="参加工作时间">{{ currentRecord.join_work_date }}</a-descriptions-item>
          <a-descriptions-item label="电话" :span="2">{{ currentRecord.phone || '-' }}</a-descriptions-item>
          <a-descriptions-item label="备注" :span="2">{{ currentRecord.remark || '-' }}</a-descriptions-item>
          <a-descriptions-item v-if="annualAssessmentText" label="年度考核" :span="2">
            {{ annualAssessmentText }}
          </a-descriptions-item>
        </a-descriptions>

        <div v-if="isMiddleLeader(currentRecord)" class="assessment-section">
          <a-divider orientation="left">中层干部研判（最新版）</a-divider>
          <a-spin :spinning="assessmentLoading">
            <a-alert
              v-if="assessmentError"
              type="error"
              show-icon
              :message="assessmentError"
              style="margin-bottom: 12px"
            />
            <a-empty
              v-else-if="!assessmentLoading && !assessmentMatches.length"
              description="最新研判版本中未找到该姓名对应记录"
            />
            <template v-else-if="assessmentMatches.length">
              <a-alert
                v-if="assessmentDeptWarning"
                type="warning"
                show-icon
                :message="assessmentDeptWarning"
                style="margin-bottom: 12px"
              />
              <a-space v-if="assessmentMatches.length > 1" style="margin-bottom: 12px" wrap>
                <span>同名匹配 {{ assessmentMatches.length }} 条，请核对：</span>
                <a-radio-group v-model:value="selectedAssessmentId" button-style="solid" size="small">
                  <a-radio-button v-for="item in assessmentMatches" :key="item.id" :value="item.id">
                    {{ item.department || '未知部门' }}
                  </a-radio-button>
                </a-radio-group>
              </a-space>
              <a-descriptions v-if="selectedAssessment" :column="2" bordered size="small" class="assessment-summary">
                <a-descriptions-item label="研判期间" :span="2">
                  {{ selectedAssessment.version_date }}
                  <span v-if="selectedAssessment.file_name" class="muted"> · {{ selectedAssessment.file_name }}</span>
                </a-descriptions-item>
                <a-descriptions-item label="研判姓名">{{ selectedAssessment.name }}</a-descriptions-item>
                <a-descriptions-item label="研判单位">{{ selectedAssessment.department || '-' }}</a-descriptions-item>
                <a-descriptions-item label="职务">{{ selectedAssessment.position || '-' }}</a-descriptions-item>
                <a-descriptions-item label="职务类别">{{ selectedAssessment.position_category_display || '-' }}</a-descriptions-item>
                <a-descriptions-item label="综合评分">{{ selectedAssessment.comprehensive_score ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="排名">{{ selectedAssessment.ranking ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="调整建议" :span="2">{{ selectedAssessment.adjustment_suggestion || '-' }}</a-descriptions-item>
              </a-descriptions>
              <a-collapse v-if="selectedAssessment" ghost class="assessment-collapse">
                <a-collapse-panel key="more" header="展开更多研判字段">
                  <a-descriptions :column="2" bordered size="small">
                    <a-descriptions-item
                      v-for="field in assessmentExtraFields"
                      :key="field.key"
                      :label="field.label"
                      :span="field.span || 1"
                    >
                      {{ displayAssessmentValue(selectedAssessment[field.key]) }}
                    </a-descriptions-item>
                  </a-descriptions>
                </a-collapse-panel>
              </a-collapse>
            </template>
          </a-spin>
        </div>
      </template>
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
          <a-space :size="24" wrap>
            <a-statistic title="总行数" :value="importResult.total" />
            <a-statistic title="写入" :value="importResult.created_count ?? importResult.success_count" :value-style="{ color: '#52c41a' }" />
            <a-statistic v-if="importResult.mode === 'replace'" title="已删除原数据" :value="importResult.deleted_count || 0" :value-style="{ color: '#fa8c16' }" />
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
import { message, Modal } from 'ant-design-vue'
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
import { assessmentApi } from '@/api/assessments'
import { registerModelContextTools } from '@/utils/webmcp'

// 响应式数据
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const loading = ref(false)
const statsLoading = ref(false)
const dataSource = ref([])
const searchText = ref('')
const filterGender = ref(undefined)
const leadershipScope = ref('all')
const filterPoliticalStatus = ref(undefined)
const selectedRowKeys = ref([])
const detailVisible = ref(false)
const currentRecord = ref(null)
const importResultVisible = ref(false)
const listError = ref('')
const statsError = ref('')
const visibleExtraColumns = ref([])
const assessmentLoading = ref(false)
const assessmentError = ref('')
const assessmentMatches = ref([])
const selectedAssessmentId = ref(undefined)
const latestAssessmentFile = ref(null)

const MIDDLE_POSITION_CATEGORIES = ['领导职务', '内定领导职务', '监区工作团队正职', '监区工作团队副职']
const assessmentExtraFields = [
  { key: 'age', label: '年龄' },
  { key: 'health_status', label: '健康程度' },
  { key: 'education', label: '学历' },
  { key: 'professional_title', label: '专业技术职称' },
  { key: 'join_prison_date', label: '参加监狱工作时间' },
  { key: 'service_years', label: '任职年限' },
  { key: 'office_work_years', label: '机关工作年限' },
  { key: 'prison_work_years', label: '监区工作年限' },
  { key: 'main_business', label: '主要从事业务', span: 2 },
  { key: 'annual_assessment_3years', label: '近三年年度考核', span: 2 },
  { key: 'quarterly_assessment', label: '今年季度考核', span: 2 },
  { key: 'rewards_3years', label: '近三年奖励', span: 2 },
  { key: 'penalties_3years', label: '近三年受到处理', span: 2 },
  { key: 'personality', label: '性格特点', span: 2 },
  { key: 'ability_assessment', label: '能力评估', span: 2 },
  { key: 'performance_2023', label: '干事评价（2023）', span: 2 },
  { key: 'performance_2024', label: '干事评价（2024）', span: 2 },
  { key: 'main_performance', label: '主要表现', span: 2 },
  { key: 'shortcomings', label: '存在不足', span: 2 },
  { key: 'evaluation_assessment', label: '评价研判', span: 2 },
  { key: 'talk_assessment', label: '谈话研判', span: 2 },
  { key: 'comprehensive_assessment', label: '综合研判', span: 2 },
  { key: 'seven_looks_score', label: '七看评价' },
  { key: 'work_recognition_score', label: '工作认可度' },
  { key: 'talk_score', label: '谈话研判评分' }
]

const normalizeText = (value) => String(value || '').trim().replace(/\s+/g, '')
const isMiddleLeader = (record) => {
  if (!record) return false
  if (normalizeText(record.department) === '监狱领导') return false
  if (String(record.position_rank || '').startsWith('县处级')) return false
  if (MIDDLE_POSITION_CATEGORIES.includes(record.position_category)) return true
  const position = String(record.position || '')
  return position.includes('团队') || position.includes('分监区长')
}
const displayAssessmentValue = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  return value
}
const selectedAssessment = computed(() =>
  assessmentMatches.value.find(item => item.id === selectedAssessmentId.value) || null
)
const annualAssessmentText = computed(() => {
  const data = currentRecord.value?.annual_assessments
  if (!data || typeof data !== 'object') return ''
  return Object.entries(data)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '')
    .map(([year, value]) => `${year}年：${value}`)
    .join('；')
})
const assessmentDeptWarning = computed(() => {
  if (!currentRecord.value || !assessmentMatches.value.length) return ''
  const rosterDept = normalizeText(currentRecord.value.department)
  const mismatched = assessmentMatches.value.filter(item => normalizeText(item.department) !== rosterDept)
  if (!mismatched.length) return ''
  if (assessmentMatches.value.length === 1) {
    return `姓名匹配，但部门不一致：花名册为「${currentRecord.value.department || '空'}」，研判为「${mismatched[0].department || '空'}」。请及时核对。`
  }
  const depts = mismatched.map(item => item.department || '空').join('、')
  return `存在同名但部门不一致的研判记录（花名册部门「${currentRecord.value.department || '空'}」，研判部门：${depts}）。请核对后选用正确记录。`
})

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
  mode: 'replace',
  total: 0,
  success_count: 0,
  created_count: 0,
  deleted_count: 0,
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

const coreColumns = [
  { title: '姓名', dataIndex: 'name', width: 100, fixed: 'left' },
  { title: '部门', dataIndex: 'department', width: 160 },
  { title: '职务', dataIndex: 'position', width: 150 },
  { title: '警员职级', dataIndex: 'police_rank', width: 120 },
  { title: '性别', key: 'gender', width: 80 },
  { title: '政治面貌', dataIndex: 'political_status', width: 120 }
]

const extraColumnDefs = {
  age: { title: '年龄', dataIndex: 'age', width: 80 },
  police_number: { title: '警号', dataIndex: 'police_number', width: 120 },
  id_card: { title: '身份证号', dataIndex: 'id_card', width: 180 },
  police_title: { title: '警衔', dataIndex: 'police_title', width: 120 },
  highest_education: { title: '最高学历', dataIndex: 'highest_education', width: 120 },
  join_work_date: { title: '参加工作时间', dataIndex: 'join_work_date', width: 120 },
  phone: { title: '电话', dataIndex: 'phone', width: 130 },
  created_at: { title: '创建时间', dataIndex: 'created_at', width: 160 }
}

const extraColumnOptions = [
  { label: '年龄', value: 'age' },
  { label: '警号', value: 'police_number' },
  { label: '身份证号', value: 'id_card' },
  { label: '警衔', value: 'police_title' },
  { label: '学历', value: 'highest_education' },
  { label: '参加工作时间', value: 'join_work_date' },
  { label: '电话', value: 'phone' },
  { label: '创建时间', value: 'created_at' }
]

const actionColumn = { title: '操作', key: 'action', width: 150, fixed: 'right' }

const displayColumns = computed(() => [
  ...coreColumns,
  ...visibleExtraColumns.value.map(key => extraColumnDefs[key]).filter(Boolean),
  actionColumn
])

const tableScrollX = computed(() => displayColumns.value.reduce((sum, col) => sum + (col.width || 120), 0))

const hasActiveFilters = computed(() => Boolean(
  searchText.value
  || filterGender.value
  || filterPoliticalStatus.value
  || leadershipScope.value !== 'all'
))

const emptyText = computed(() => {
  if (listError.value) return '加载失败，请重试'
  if (hasActiveFilters.value) return '当前筛选条件下没有匹配人员'
  return '暂无花名册数据'
})

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

  Modal.confirm({
    title: '覆盖导入花名册？',
    content: `将清空并覆盖当前全部花名册数据，再写入「${file.name}」中的记录。此操作不可恢复，是否继续？`,
    okText: '确认覆盖导入',
    okType: 'danger',
    cancelText: '取消',
    onOk: () => handleUpload(file)
  })
  return false
}

// 处理上传（默认覆盖原有数据）
const handleUpload = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('replace', 'true')

  uploading.value = true
  uploadProgress.value = 0
  uploadStatus.value = '正在上传文件...'

  try {
    uploadProgress.value = 30
    uploadStatus.value = '正在解析并覆盖写入...'

    const response = await request.post('/roster/upload-excel/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000,
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress.value = percentCompleted
      }
    })

    uploadProgress.value = 100
    uploadStatus.value = '覆盖导入完成！'

    Object.assign(importResult, {
      message: '',
      mode: 'replace',
      total: 0,
      success_count: 0,
      created_count: 0,
      deleted_count: 0,
      error_count: 0,
      errors: [],
      ...response
    })
    importResultVisible.value = true

    await Promise.all([
      loadStatistics(),
      loadData()
    ])

    message.success(response.message || '花名册已覆盖更新')
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

// 下载模板（优先后端最新版；失败时回退本地 public 模板）
const downloadTemplate = async () => {
  const saveBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  try {
    const response = await request.get('/roster/download-template/', {
      responseType: 'blob'
    })
    const blob = response instanceof Blob
      ? response
      : new Blob([response], { type: 'application/vnd.ms-excel' })
    // 后端新版模板为 .xls（来自 改进要求/新版花名册）
    saveBlob(blob, '花名册数据模版.xls')
    message.success('已开始下载最新花名册模板')
  } catch (error) {
    const link = document.createElement('a')
    link.href = `${import.meta.env.BASE_URL}roster-template.xls`
    link.download = '花名册数据模版.xls'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    message.success('已下载本地最新花名册模板')
  }
}

const refreshAll = async () => {
  await Promise.all([loadStatistics(), loadData()])
}

// 加载统计数据
const loadStatistics = async () => {
  statsLoading.value = true
  statsError.value = ''
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
    statsError.value = error.response?.data?.detail || error.message || '统计加载失败'
    statistics.total = 0
    statistics.departments = 0
    statistics.male_count = 0
    statistics.female_count = 0
  } finally {
    statsLoading.value = false
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  listError.value = ''
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.pageSize,
      leadership_scope: leadershipScope.value
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
    pagination.total = response.count || response.length || 0
  } catch (error) {
    console.error('加载数据失败:', error)
    dataSource.value = []
    pagination.total = 0
    listError.value = error.response?.data?.detail || error.message || '无法连接后端或请求失败'
    message.error('加载数据失败，请检查后端服务后重试')
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
const resetAssessmentState = () => {
  assessmentLoading.value = false
  assessmentError.value = ''
  assessmentMatches.value = []
  selectedAssessmentId.value = undefined
  latestAssessmentFile.value = null
}

const pickPreferredAssessment = (matches, roster) => {
  const rosterDept = normalizeText(roster.department)
  const sameDept = matches.find(item => normalizeText(item.department) === rosterDept)
  return sameDept || matches[0]
}

const loadLatestAssessment = async (roster) => {
  assessmentLoading.value = true
  assessmentError.value = ''
  assessmentMatches.value = []
  selectedAssessmentId.value = undefined
  latestAssessmentFile.value = null
  try {
    const filesData = await assessmentApi.getFiles()
    const files = filesData.results || filesData || []
    if (!files.length) {
      assessmentError.value = ''
      return
    }
    const latest = [...files].sort((a, b) => String(b.version_date).localeCompare(String(a.version_date)))[0]
    latestAssessmentFile.value = latest
    const recordsData = await assessmentApi.getRecords({
      file: latest.id,
      name: roster.name,
      page_size: 100
    })
    const records = recordsData.results || recordsData || []
    const exactMatches = records.filter(item => normalizeText(item.name) === normalizeText(roster.name))
    if (!exactMatches.length) return

    // 列表字段可能不全，再拉详情补全折叠区字段
    const detailed = await Promise.all(
      exactMatches.map(async (item) => {
        try {
          return await assessmentApi.getRecord(item.id)
        } catch {
          return item
        }
      })
    )
    assessmentMatches.value = detailed
    const preferred = pickPreferredAssessment(detailed, roster)
    selectedAssessmentId.value = preferred?.id
  } catch (error) {
    if (error.response?.status === 403) {
      assessmentError.value = '当前账号无中层干部研判查看权限'
    } else {
      assessmentError.value = error.response?.data?.detail || error.message || '加载中层研判失败'
    }
  } finally {
    assessmentLoading.value = false
  }
}

const viewDetail = async (record) => {
  resetAssessmentState()
  currentRecord.value = record
  detailVisible.value = true
  try {
    const full = await request.get(`/roster/${record.id}/`)
    currentRecord.value = full
  } catch (error) {
    console.error('加载花名册详情失败:', error)
  }
  if (isMiddleLeader(currentRecord.value)) {
    await loadLatestAssessment(currentRecord.value)
  }
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
      name: 'read_openhrm_roster_record', title: '读取花名册详情', description: '在当前页面打开并返回一条花名册记录详情，不修改数据。', inputSchema: { type: 'object', properties: { recordId: { type: 'string', minLength: 1, description: '花名册记录 UUID。' } }, required: ['recordId'], additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: true },
      async execute(input) {
        const record = findRosterRecord(input.recordId)
        await viewDetail(record)
        await nextTick()
        return {
          record: currentRecord.value,
          isMiddleLeader: isMiddleLeader(currentRecord.value),
          assessment: {
            latestVersionDate: latestAssessmentFile.value?.version_date || null,
            matches: assessmentMatches.value.map(({ id, name, department, position, comprehensive_score, ranking }) => ({
              id, name, department, position, comprehensiveScore: comprehensive_score, ranking
            })),
            selectedId: selectedAssessmentId.value,
            departmentWarning: assessmentDeptWarning.value || null,
            error: assessmentError.value || null
          }
        }
      }
    },
    {
      name: 'stage_openhrm_roster_record_selection', title: '选择花名册记录', description: '在当前页面勾选要批量处理的花名册记录，仅暂存选择，不会删除数据。', inputSchema: { type: 'object', properties: { recordIds: { type: 'array', items: { type: 'string', minLength: 1 }, uniqueItems: true, description: '花名册记录 UUID 列表。' } }, required: ['recordIds'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { input.recordIds.forEach(findRosterRecord); selectedRowKeys.value = [...input.recordIds]; await nextTick(); return { status: 'staged', recordIds: selectedRowKeys.value } }
    },
    {
      name: 'complete_openhrm_roster_record_deletion', title: '删除花名册记录', description: '永久删除指定的一条花名册记录；这是不可逆的人员数据删除操作。', inputSchema: { type: 'object', properties: { recordId: { type: 'string', minLength: 1, description: '花名册记录 UUID。' } }, required: ['recordId'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { const record = findRosterRecord(input.recordId); await request.delete(`/roster/${record.id}/`); await Promise.all([loadData(), loadStatistics()]); message.success('删除成功'); return { status: 'deleted', recordId: record.id, name: record.name } }
    },
    {
      name: 'complete_openhrm_roster_batch_deletion', title: '批量删除花名册记录', description: '永久删除所列花名册记录；这是不可逆的人员数据删除操作。', inputSchema: { type: 'object', properties: { recordIds: { type: 'array', items: { type: 'string', minLength: 1 }, minItems: 1, uniqueItems: true, description: '花名册记录 UUID 列表。' } }, required: ['recordIds'], additionalProperties: false }, annotations: { readOnlyHint: false },
      async execute(input) { const records = input.recordIds.map(findRosterRecord); await Promise.all(records.map(record => request.delete(`/roster/${record.id}/`))); selectedRowKeys.value = []; await Promise.all([loadData(), loadStatistics()]); message.success(`成功删除 ${records.length} 条记录`); return { status: 'deleted', count: records.length, recordIds: input.recordIds } }
    }
  ])
}

// 页面加载
onMounted(() => {
  registerWebMcpTools()
  refreshAll()
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

.upload-hint {
  margin-top: 8px;
  color: #8c8c8c;
  font-size: 12px;
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

.assessment-section {
  margin-top: 8px;
}

.assessment-summary {
  margin-bottom: 8px;
}

.assessment-collapse {
  margin-top: 4px;
}

.muted {
  color: #8c8c8c;
  margin-left: 4px;
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
