<template>
  <div class="org-structure">
    <a-card title="组织架构" :bordered="false">
      <template #extra>
        <a-space>
          <a-button type="primary" @click="handleAddRoot">
            <template #icon>
              <PlusOutlined />
            </template>
            新增根节点
          </a-button>
          <a-button @click="handleRefresh" :loading="loading">
            <template #icon>
              <SyncOutlined />
            </template>
            刷新
          </a-button>
        </a-space>
      </template>

      <!-- 组织架构树 -->
      <div class="org-tree-container">
        <a-tree
          v-if="treeData.length > 0"
          :tree-data="treeData"
          show-icon
          default-expand-all
          :field-names="fieldNames"
          @select="handleSelect"
        >
          <template #icon="{ dataRef }">
            <ApartmentOutlined v-if="dataRef.unit_type === 'BRANCH'" style="color: #667eea;" />
            <TeamOutlined v-else-if="dataRef.unit_type === 'TEAM'" style="color: #52c41a;" />
            <HomeOutlined v-else-if="dataRef.unit_type === 'OFFICE'" style="color: #faad14;" />
            <ApartmentOutlined v-else-if="dataRef.unit_type === 'DIVISION'" style="color: #722ed1;" />
            <TeamOutlined v-else style="color: #1890ff;" />
          </template>
          <template #title="{ dataRef }">
            <div class="tree-node-title">
              <div class="node-info">
                <span class="node-name">{{ dataRef.name }}</span>
                <a-tag v-if="dataRef.code" color="blue" size="small">{{ dataRef.code }}</a-tag>
                <a-tag v-if="!dataRef.is_active" color="red" size="small">已禁用</a-tag>
              </div>
              <div class="node-stats" v-if="dataRef.member_count !== undefined">
                <span style="color: #666; font-size: 12px;">
                  <UserOutlined style="margin-right: 4px;" />
                  {{ dataRef.member_count }} 人
                </span>
              </div>
              <a-space :size="4" class="node-actions">
                <a-tooltip title="新增子部门">
                  <a-button
                    type="link"
                    size="small"
                    @click.stop="handleAddChild(dataRef)"
                  >
                    <PlusOutlined />
                  </a-button>
                </a-tooltip>
                <a-tooltip title="编辑">
                  <a-button
                    type="link"
                    size="small"
                    @click.stop="handleEdit(dataRef)"
                  >
                    <EditOutlined />
                  </a-button>
                </a-tooltip>
                <a-tooltip title="删除">
                  <a-button
                    type="link"
                    size="small"
                    danger
                    @click.stop="handleDelete(dataRef)"
                  >
                    <DeleteOutlined />
                  </a-button>
                </a-tooltip>
              </a-space>
            </div>
          </template>
        </a-tree>

        <a-empty v-else-if="!loading" description="暂无组织架构数据">
          <a-button type="primary" @click="handleAddRoot">创建根部门</a-button>
        </a-empty>

        <a-spin v-if="loading" :spinning="loading" tip="加载中...">
          <div style="height: 400px;"></div>
        </a-spin>
      </div>
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
        <a-form-item label="上级部门" name="parent" v-if="currentNode && !isEdit">
          <a-input :value="currentNode.name" disabled />
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
  SyncOutlined,
  EditOutlined,
  DeleteOutlined,
  ApartmentOutlined,
  TeamOutlined,
  UserOutlined,
  HomeOutlined
} from '@ant-design/icons-vue'
import {
  getOrgTree,
  createDepartment,
  updateDepartment,
  deleteDepartment
} from '@/api/org'

// 响应式数据
const treeData = ref([])
const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const modalTitle = ref('新增部门')
const formRef = ref()
const currentNode = ref(null)
const isEdit = ref(false)

// Tree 字段映射
const fieldNames = {
  title: 'name',
  key: 'id',
  children: 'children'
}

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

// 加载组织架构数据
const loadTreeData = async () => {
  loading.value = true
  try {
    const response = await getOrgTree()

    console.log('组织架构响应数据:', response)

    // 响应拦截器已经返回了 response.data，所以 response 就是数据
    if (response) {
      // 后端返回的是数组
      treeData.value = Array.isArray(response) ? response : [response]

      if (treeData.value.length > 0) {
        message.success(`加载成功，共 ${treeData.value.length} 个根节点`)
      } else {
        message.warning('暂无组织架构数据')
      }
    } else {
      treeData.value = []
      message.warning('暂无组织架构数据')
    }
  } catch (error) {
    console.error('加载组织架构失败:', error)
    message.error(error.message || '加载组织架构失败')
    treeData.value = []
  } finally {
    loading.value = false
  }
}

// 刷新
const handleRefresh = () => {
  loadTreeData()
}

// 选中节点
const handleSelect = (selectedKeys, { node }) => {
  console.log('选中节点:', node)
}

// 新增根节点
const handleAddRoot = () => {
  isEdit.value = false
  currentNode.value = null
  modalTitle.value = '新增根部门'
  resetForm()
  formData.parent = null
  modalVisible.value = true
}

// 新增子节点
const handleAddChild = (node) => {
  isEdit.value = false
  currentNode.value = node
  modalTitle.value = `新增子部门 - ${node.name}`
  resetForm()
  formData.parent = node.id
  modalVisible.value = true
}

// 编辑节点
const handleEdit = (node) => {
  isEdit.value = true
  currentNode.value = node
  modalTitle.value = '编辑部门'
  formData.name = node.name
  formData.code = node.code || ''
  formData.unit_type = node.unit_type || 'DEPARTMENT'
  formData.sort_order = node.sort_order || 0
  formData.is_active = node.is_active !== undefined ? node.is_active : true
  modalVisible.value = true
}

// 删除节点
const handleDelete = (node) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除部门"${node.name}"吗？删除后子部门和成员关系也会被删除。`,
    okText: '确定',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deleteDepartment(node.id)
        message.success('删除成功')
        loadTreeData()
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
      unit_type: formData.unit_type,
      sort_order: formData.sort_order,
      is_active: formData.is_active
    }

    // 只有当 code 有值时才发送
    if (formData.code) {
      data.code = formData.code
    }

    // 处理 parent 字段
    if (!isEdit.value && currentNode.value) {
      // 新增子部门
      data.parent = currentNode.value.id
    } else if (!isEdit.value) {
      // 新增根部门，不发送 parent 字段（让后端使用默认值 null）
    }

    console.log('提交数据:', data)

    if (isEdit.value) {
      await updateDepartment(currentNode.value.id, data)
      message.success('更新成功')
    } else {
      await createDepartment(data)
      message.success('新增成功')
    }

    modalVisible.value = false
    loadTreeData()
  } catch (error) {
    console.error('提交错误:', error)

    if (error.errorFields) {
      message.error('请检查表单填写')
    } else if (error.response && error.response.data) {
      // 显示后端返回的详细错误信息
      const errorData = error.response.data
      if (typeof errorData === 'string') {
        message.error(errorData)
      } else if (errorData.detail) {
        message.error(errorData.detail)
      } else if (errorData.error) {
        message.error(errorData.error)
      } else {
        // 显示字段错误
        const errors = []
        for (const [field, msgs] of Object.entries(errorData)) {
          if (Array.isArray(msgs)) {
            errors.push(`${field}: ${msgs.join(', ')}`)
          } else {
            errors.push(`${field}: ${msgs}`)
          }
        }
        message.error(errors.join('; ') || '操作失败')
      }
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

// 页面加载
onMounted(() => {
  loadTreeData()
})
</script>

<style scoped>
.org-structure {
  padding: 0;
}

.org-tree-container {
  min-height: 400px;
  padding: 16px 0;
}

.tree-node-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 4px 0;
  flex-wrap: wrap;
  gap: 8px;
}

.node-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 200px;
}

.node-name {
  font-size: 14px;
  font-weight: 500;
}

.node-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-right: auto;
}

.node-actions {
  opacity: 0;
  transition: opacity 0.2s;
  margin-left: auto;
}

.tree-node-title:hover .node-actions {
  opacity: 1;
}

/* 响应式 */
@media (max-width: 768px) {
  .tree-node-title {
    flex-direction: column;
    align-items: flex-start;
  }

  .node-actions {
    opacity: 1;
    margin-left: 0;
  }
}
</style>
