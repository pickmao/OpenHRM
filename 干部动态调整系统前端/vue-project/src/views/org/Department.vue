<template>
  <div class="department">
    <a-card title="部门管理" :bordered="false">
      <template #extra>
        <a-button type="primary" @click="handleAdd">
          <template #icon>
            <PlusOutlined />
          </template>
          新增部门
        </a-button>
      </template>

      <!-- 搜索表单 -->
      <a-form layout="inline" class="search-form">
        <a-form-item label="部门名称">
          <a-input
            v-model:value="searchForm.search"
            placeholder="请输入部门名称"
            allow-clear
            @pressEnter="handleSearch"
            style="width: 200px"
          />
        </a-form-item>
        <a-form-item label="部门类型">
          <a-select
            v-model:value="searchForm.unit_type"
            placeholder="请选择类型"
            style="width: 150px"
            allow-clear
          >
            <a-select-option value="BRANCH">支部</a-select-option>
            <a-select-option value="DIVISION">处室</a-select-option>
            <a-select-option value="OFFICE">办公室</a-select-option>
            <a-select-option value="DEPARTMENT">部门</a-select-option>
            <a-select-option value="TEAM">团队</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="状态">
          <a-select
            v-model:value="searchForm.is_active"
            placeholder="请选择状态"
            style="width: 120px"
            allow-clear
          >
            <a-select-option :value="true">启用</a-select-option>
            <a-select-option :value="false">禁用</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="handleSearch">
              <template #icon>
                <SearchOutlined />
              </template>
              搜索
            </a-button>
            <a-button @click="handleReset">
              <template #icon>
                <ReloadOutlined />
              </template>
              重置
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <!-- 数据表格 -->
      <a-table
        :columns="columns"
        :data-source="dataSource"
        :loading="loading"
        :pagination="pagination"
        :row-key="(record) => record.id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'unit_type'">
            <a-tag :color="getUnitTypeColor(record.unit_type)">
              {{ getUnitTypeLabel(record.unit_type) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'parent'">
            {{ record.parent_name || '-' }}
          </template>
          <template v-else-if="column.key === 'is_active'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleEdit(record)">
                <template #icon>
                  <EditOutlined />
                </template>
                编辑
              </a-button>
              <a-button
                type="link"
                size="small"
                danger
                @click="handleDelete(record)"
              >
                <template #icon>
                  <DeleteOutlined />
                </template>
                删除
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑对话框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      width="600px"
      :confirm-loading="submitLoading"
      @ok="handleModalOk"
      @cancel="handleModalCancel"
    >
      <a-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="上级部门" name="parent">
          <a-tree-select
            v-model:value="formData.parent"
            :tree-data="departmentTreeData"
            placeholder="请选择上级部门（可选）"
            allow-clear
            tree-default-expand-all
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
          />
        </a-form-item>
        <a-form-item label="部门名称" name="name">
          <a-input v-model:value="formData.name" placeholder="请输入部门名称" />
        </a-form-item>
        <a-form-item label="部门编码" name="code">
          <a-input v-model:value="formData.code" placeholder="请输入部门编码（可选）" />
        </a-form-item>
        <a-form-item label="部门类型" name="unit_type">
          <a-select v-model:value="formData.unit_type" placeholder="请选择部门类型">
            <a-select-option value="BRANCH">支部</a-select-option>
            <a-select-option value="DIVISION">处室</a-select-option>
            <a-select-option value="OFFICE">办公室</a-select-option>
            <a-select-option value="DEPARTMENT">部门</a-select-option>
            <a-select-option value="TEAM">团队</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number
            v-model:value="formData.sort_order"
            :min="0"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="formData.is_active" checked-children="启用" un-checked-children="禁用" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'
import {
  getDepartmentList,
  getOrgTree,
  createDepartment,
  updateDepartment,
  deleteDepartment
} from '@/api/org'

// 表格列配置
const columns = [
  {
    title: 'ID',
    dataIndex: 'id',
    key: 'id',
    width: 80
  },
  {
    title: '部门名称',
    dataIndex: 'name',
    key: 'name'
  },
  {
    title: '部门编码',
    dataIndex: 'code',
    key: 'code',
    width: 120
  },
  {
    title: '类型',
    dataIndex: 'unit_type',
    key: 'unit_type',
    width: 100
  },
  {
    title: '上级部门',
    dataIndex: 'parent_name',
    key: 'parent',
    width: 150
  },
  {
    title: '排序',
    dataIndex: 'sort_order',
    key: 'sort_order',
    width: 80
  },
  {
    title: '状态',
    dataIndex: 'is_active',
    key: 'is_active',
    width: 80
  },
  {
    title: '操作',
    key: 'action',
    width: 180,
    fixed: 'right'
  }
]

// 响应式数据
const dataSource = ref([])
const departmentTreeData = ref([])
const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const modalTitle = ref('新增部门')
const formRef = ref()
const currentRecord = ref(null)
const isEdit = ref(false)

// 搜索表单
const searchForm = reactive({
  search: '',
  unit_type: undefined,
  is_active: undefined
})

// 分页配置
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条`
})

// 表单数据
const formData = reactive({
  parent: undefined,
  name: '',
  code: '',
  unit_type: 'DEPARTMENT',
  sort_order: 0,
  is_active: true
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入部门名称', trigger: 'blur' }
  ],
  unit_type: [
    { required: true, message: '请选择部门类型', trigger: 'change' }
  ]
}

// 获取部门类型颜色
const getUnitTypeColor = (type) => {
  const colorMap = {
    BRANCH: 'purple',
    DIVISION: 'magenta',
    OFFICE: 'orange',
    DEPARTMENT: 'blue',
    TEAM: 'green'
  }
  return colorMap[type] || 'default'
}

// 获取部门类型标签
const getUnitTypeLabel = (type) => {
  const labelMap = {
    BRANCH: '支部',
    DIVISION: '处室',
    OFFICE: '办公室',
    DEPARTMENT: '部门',
    TEAM: '团队'
  }
  return labelMap[type] || type
}

// 加载部门列表
const loadDepartmentList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.pageSize,
      ...searchForm
    }

    // 移除空值
    Object.keys(params).forEach(key => {
      if (params[key] === undefined || params[key] === '') {
        delete params[key]
      }
    })

    const response = await getDepartmentList(params)
    console.log('部门列表响应:', response)

    // 响应拦截器已经返回了 response.data
    if (response) {
      dataSource.value = response.results || response
      pagination.total = response.count || (Array.isArray(response) ? response.length : 0)
    } else {
      dataSource.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('加载部门列表失败:', error)
    message.error(error.message || '加载部门列表失败')
  } finally {
    loading.value = false
  }
}

// 加载部门树
const loadDepartmentTree = async () => {
  try {
    const response = await getOrgTree()
    console.log('部门树响应:', response)

    if (response && response.length > 0) {
      // 添加一个顶级选项"无（作为根部门）"
      const treeData = [
        { id: null, name: '无（作为根部门）', children: [] }
      ]

      const data = Array.isArray(response) ? response : [response]
      treeData[0].children = data
      departmentTreeData.value = treeData
    } else {
      departmentTreeData.value = [
        { id: null, name: '无（作为根部门）', children: [] }
      ]
    }
  } catch (error) {
    console.error('加载部门树失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadDepartmentList()
}

// 重置
const handleReset = () => {
  searchForm.search = ''
  searchForm.unit_type = undefined
  searchForm.is_active = undefined
  pagination.current = 1
  loadDepartmentList()
}

// 新增
const handleAdd = () => {
  isEdit.value = false
  currentRecord.value = null
  modalTitle.value = '新增部门'
  resetForm()
  modalVisible.value = true
}

// 编辑
const handleEdit = (record) => {
  isEdit.value = true
  currentRecord.value = record
  modalTitle.value = '编辑部门'
  formData.parent = record.parent
  formData.name = record.name
  formData.code = record.code || ''
  formData.unit_type = record.unit_type
  formData.sort_order = record.sort_order || 0
  formData.is_active = record.is_active !== undefined ? record.is_active : true
  modalVisible.value = true
}

// 删除
const handleDelete = (record) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除部门"${record.name}"吗？删除后子部门和成员关系也会被删除。`,
    okText: '确定',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deleteDepartment(record.id)
        message.success('删除成功')
        loadDepartmentList()
        loadDepartmentTree()
      } catch (error) {
        message.error(error.message || '删除失败')
      }
    }
  })
}

// 提交表单
const handleModalOk = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    const data = {
      name: formData.name,
      code: formData.code || undefined,
      unit_type: formData.unit_type,
      sort_order: formData.sort_order,
      is_active: formData.is_active
    }

    // 如果选择了上级部门
    if (formData.parent !== null && formData.parent !== undefined) {
      data.parent = formData.parent
    }

    if (isEdit.value) {
      await updateDepartment(currentRecord.value.id, data)
      message.success('更新成功')
    } else {
      await createDepartment(data)
      message.success('新增成功')
    }

    modalVisible.value = false
    loadDepartmentList()
    loadDepartmentTree()
  } catch (error) {
    if (error.errorFields) {
      message.error('请检查表单填写')
    } else {
      message.error(error.message || '操作失败')
    }
  } finally {
    submitLoading.value = false
  }
}

// 取消弹窗
const handleModalCancel = () => {
  modalVisible.value = false
  resetForm()
}

// 重置表单
const resetForm = () => {
  formData.parent = undefined
  formData.name = ''
  formData.code = ''
  formData.unit_type = 'DEPARTMENT'
  formData.sort_order = 0
  formData.is_active = true
  formRef.value?.clearValidate()
}

// 表格变化
const handleTableChange = (pag) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadDepartmentList()
}

// 页面加载
onMounted(() => {
  loadDepartmentList()
  loadDepartmentTree()
})
</script>

<style scoped>
.department {
  padding: 0;
}

.search-form {
  margin-bottom: 16px;
}
</style>
