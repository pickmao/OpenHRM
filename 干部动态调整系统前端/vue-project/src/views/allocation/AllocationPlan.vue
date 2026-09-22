<template>
  <div class="allocation-page">
    <a-card title="部门调配" :bordered="false">
      <a-alert
        type="info"
        show-icon
        message="直接生效模式"
        description="提交成功后人员组织归属会立即变更，系统当前不提供调配审批环节。"
        style="margin-bottom: 16px"
      />

      <a-alert
        v-if="!canTransfer"
        type="warning"
        show-icon
        message="当前账号没有人员调配权限"
        description="需要 orgs:membership:transfer 权限。"
        style="margin-bottom: 16px"
      />

      <a-form ref="formRef" :model="form" :rules="rules" :label-col="{ span: 4 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="调出部门" name="fromDeptId">
          <a-tree-select
            v-model:value="form.fromDeptId"
            :tree-data="deptTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            tree-default-expand-all
            placeholder="请选择调出部门"
            :disabled="!canTransfer"
            @change="loadMembers"
          />
        </a-form-item>

        <a-form-item label="调配人员" name="memberIds">
          <a-select
            v-model:value="form.memberIds"
            mode="multiple"
            :loading="membersLoading"
            :disabled="!canTransfer || !form.fromDeptId"
            :options="memberOptions"
            placeholder="请先选择调出部门"
            option-filter-prop="label"
            show-search
          />
        </a-form-item>

        <a-form-item label="调入部门" name="toDeptId">
          <a-tree-select
            v-model:value="form.toDeptId"
            :tree-data="deptTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            tree-default-expand-all
            placeholder="请选择调入部门"
            :disabled="!canTransfer"
          />
        </a-form-item>

        <a-form-item label="生效日期" name="effectiveDate">
          <a-input v-model:value="form.effectiveDate" type="date" :disabled="!canTransfer" />
        </a-form-item>

        <a-form-item label="新职务">
          <a-input v-model:value="form.newPosition" :disabled="!canTransfer" placeholder="不填写则沿用原职务" />
        </a-form-item>

        <a-form-item label="调配原因" name="reason">
          <a-textarea v-model:value="form.reason" :rows="3" :maxlength="500" show-count :disabled="!canTransfer" />
        </a-form-item>

        <a-form-item :wrapper-col="{ offset: 4, span: 16 }">
          <a-space>
            <a-button type="primary" :disabled="!canTransfer" :loading="submitting" @click="confirmAndSubmit">
              提交并立即生效
            </a-button>
            <a-button @click="reset">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-card
        v-if="lastResult"
        type="inner"
        title="最近一次调配结果"
        style="margin-top: 16px"
      >
        <a-space style="margin-bottom: 12px">
          <a-tag color="success">成功 {{ lastResult.success }} 人</a-tag>
          <a-tag v-if="lastResult.failed" color="error">失败 {{ lastResult.failed }} 人</a-tag>
        </a-space>

        <a-table
          v-if="failedRows.length"
          size="small"
          :columns="failColumns"
          :data-source="failedRows"
          :pagination="false"
          row-key="user_id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-button type="link" size="small" :disabled="!canTransfer" @click="retryFailed([record.user_id])">
                单独重试
              </a-button>
            </template>
          </template>
        </a-table>

        <a-space v-if="failedRows.length" style="margin-top: 12px">
          <a-button type="primary" ghost :disabled="!canTransfer" :loading="submitting" @click="retryFailed()">
            重试全部失败人员
          </a-button>
          <a-button @click="keepFailedOnly">仅保留失败人员到表单</a-button>
        </a-space>
      </a-card>
    </a-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { createTransferRequest, getDepartmentMembers, getOrgTree } from '@/api/org'
import { useUserStore } from '@/stores/user'
import { registerModelContextTools } from '@/utils/webmcp'

const userStore = useUserStore()
const route = useRoute()
const formRef = ref()
const deptTree = ref([])
const members = ref([])
const membersLoading = ref(false)
const submitting = ref(false)
const lastResult = ref(null)
const today = () => new Date().toISOString().slice(0, 10)

const form = reactive({
  fromDeptId: undefined,
  toDeptId: undefined,
  memberIds: [],
  effectiveDate: today(),
  newPosition: '',
  reason: ''
})

const rules = {
  fromDeptId: [{ required: true, message: '请选择调出部门', trigger: 'change' }],
  toDeptId: [{ required: true, message: '请选择调入部门', trigger: 'change' }],
  memberIds: [{ required: true, type: 'array', min: 1, message: '请选择至少一名人员', trigger: 'change' }],
  effectiveDate: [{ required: true, message: '请选择生效日期', trigger: 'change' }],
  reason: [{ required: true, message: '请填写调配原因', trigger: 'blur' }]
}

const canTransfer = computed(() => userStore.isAdmin || userStore.hasPermission('orgs:membership:transfer'))
const memberOptions = computed(() => members.value.map(item => ({
  value: item.user,
  label: `${item.user_info?.real_name || item.user_info?.username || '未命名'}${item.position ? `（${item.position}）` : ''}`
})))

const memberLabelMap = computed(() => {
  const map = {}
  memberOptions.value.forEach(item => { map[item.value] = item.label })
  return map
})

const failedRows = computed(() => {
  if (!lastResult.value?.results) return []
  return lastResult.value.results
    .filter(item => !item.success)
    .map(item => ({
      user_id: item.user_id,
      name: memberLabelMap.value[item.user_id] || item.user_id,
      error: item.error || '未知错误'
    }))
})

const failColumns = [
  { title: '人员', dataIndex: 'name', key: 'name' },
  { title: '失败原因', dataIndex: 'error', key: 'error' },
  { title: '操作', key: 'action', width: 120 }
]

const loadTree = async () => {
  try {
    const data = await getOrgTree()
    deptTree.value = Array.isArray(data) ? data : []
  } catch (error) {
    message.error(error.response?.data?.detail || '组织架构加载失败')
  }
}

const loadMembers = async (unitId) => {
  form.memberIds = []
  members.value = []
  if (!unitId) return
  membersLoading.value = true
  try {
    const data = await getDepartmentMembers(unitId, { primary_only: true })
    members.value = Array.isArray(data) ? data : (data.results || [])
  } catch (error) {
    message.error(error.response?.data?.detail || '部门人员加载失败')
  } finally {
    membersLoading.value = false
  }
}

const reset = () => {
  Object.assign(form, {
    fromDeptId: undefined,
    toDeptId: undefined,
    memberIds: [],
    effectiveDate: today(),
    newPosition: '',
    reason: ''
  })
  members.value = []
  lastResult.value = null
  formRef.value?.clearValidate()
}

const buildPayload = (memberIds) => ({
  members: memberIds,
  from_dept: form.fromDeptId,
  to_dept: form.toDeptId,
  effective_date: form.effectiveDate,
  reason: form.reason,
  new_position: form.newPosition || undefined
})

const applySubmitResult = (result, submittedIds) => {
  lastResult.value = result
  if (result.failed) {
    const failedIds = (result.results || [])
      .filter(item => !item.success)
      .map(item => item.user_id)
    form.memberIds = failedIds.length ? failedIds : [...submittedIds]
    message.warning(`调配完成：成功 ${result.success} 人，失败 ${result.failed} 人。失败人员已保留在表单中。`)
  } else {
    message.success(`已完成 ${result.success} 人的部门调配（立即生效）`)
    form.memberIds = []
  }
}

const submitTransfer = async (memberIds) => {
  submitting.value = true
  try {
    const result = await createTransferRequest(buildPayload(memberIds))
    applySubmitResult(result, memberIds)
    return result
  } finally {
    submitting.value = false
  }
}

const confirmAndSubmit = async () => {
  try {
    await formRef.value.validate()
    if (form.fromDeptId === form.toDeptId) {
      message.warning('调出部门和调入部门不能相同')
      return
    }
    const count = form.memberIds.length
    Modal.confirm({
      title: '确认立即调配？',
      content: `将调配 ${count} 人，提交后组织归属立即变更，无法通过本页撤销。`,
      okText: '确认提交并立即生效',
      cancelText: '取消',
      onOk: () => submitTransfer([...form.memberIds])
    })
  } catch (error) {
    if (!error?.errorFields) message.error(error.response?.data?.error || '提交调配失败')
  }
}

const retryFailed = async (ids) => {
  const targetIds = ids || failedRows.value.map(item => item.user_id)
  if (!targetIds.length) {
    message.info('没有可重试的失败人员')
    return
  }
  form.memberIds = [...targetIds]
  try {
    await formRef.value.validate()
    await submitTransfer(targetIds)
  } catch (error) {
    if (!error?.errorFields) message.error(error.response?.data?.error || '重试调配失败')
  }
}

const keepFailedOnly = () => {
  form.memberIds = failedRows.value.map(item => item.user_id)
  message.success('已将失败人员保留到调配人员中')
}

const transferSchema = {
  type: 'object',
  properties: {
    fromDepartmentId: { type: 'string', minLength: 1, description: '调出部门 UUID。' },
    toDepartmentId: { type: 'string', minLength: 1, description: '调入部门 UUID。' },
    memberIds: { type: 'array', items: { type: 'string', minLength: 1 }, minItems: 1, uniqueItems: true, description: '成员关系 UUID 列表。' },
    effectiveDate: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' },
    reason: { type: 'string', minLength: 1, maxLength: 500 },
    newPosition: { type: 'string' }
  },
  required: ['fromDepartmentId', 'toDepartmentId', 'memberIds', 'effectiveDate', 'reason'],
  additionalProperties: false
}

const stageTransfer = async input => {
  if (!canTransfer.value) throw new Error('当前账号没有人员调配权限')
  if (input.fromDepartmentId === input.toDepartmentId) throw new Error('调出部门和调入部门不能相同')
  form.fromDeptId = input.fromDepartmentId
  await loadMembers(input.fromDepartmentId)
  const allowedMemberIds = new Set(memberOptions.value.map(item => item.value))
  const unknown = input.memberIds.find(id => !allowedMemberIds.has(id))
  if (unknown) throw new Error(`人员 ${unknown} 不属于所选调出部门`)
  Object.assign(form, {
    toDeptId: input.toDepartmentId,
    memberIds: [...input.memberIds],
    effectiveDate: input.effectiveDate,
    reason: input.reason.trim(),
    newPosition: input.newPosition?.trim() || ''
  })
  await nextTick()
}

let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_transfer_options',
      title: '读取调配选项',
      description: '读取组织树；提供调出部门后同时读取可调配人员，不会提交调配。',
      inputSchema: { type: 'object', properties: { fromDepartmentId: { type: 'string', minLength: 1, description: '调出部门 UUID。' } }, additionalProperties: false },
      annotations: { readOnlyHint: true },
      async execute(input) {
        await loadTree()
        if (input.fromDepartmentId) {
          form.fromDeptId = input.fromDepartmentId
          await loadMembers(input.fromDepartmentId)
        }
        return {
          canTransfer: canTransfer.value,
          mode: 'direct_effect',
          departmentTree: deptTree.value,
          members: memberOptions.value.map(({ value, label }) => ({ userId: value, label }))
        }
      }
    },
    {
      name: 'stage_openhrm_department_transfer',
      title: '配置人员调配',
      description: '在当前调配页面选择部门、人员、日期和原因，仅暂存，不会提交调配。',
      inputSchema: transferSchema,
      annotations: { readOnlyHint: false },
      async execute(input) {
        await stageTransfer(input)
        return {
          status: 'staged',
          fromDepartmentId: form.fromDeptId,
          toDepartmentId: form.toDeptId,
          memberIds: form.memberIds,
          effectiveDate: form.effectiveDate
        }
      }
    },
    {
      name: 'complete_openhrm_department_transfer',
      title: '提交人员调配',
      description: '将指定人员从调出部门调配到调入部门；这会立即修改人员组织归属。',
      inputSchema: transferSchema,
      annotations: { readOnlyHint: false },
      async execute(input) {
        await stageTransfer(input)
        await formRef.value.validate()
        const result = await submitTransfer([...form.memberIds])
        return { status: 'completed', success: result.success || 0, failed: result.failed || 0, results: result.results || [] }
      }
    }
  ])
}

onMounted(async () => {
  registerWebMcpTools()
  await loadTree()
  const sourceId = route.query.fromDeptId
  if (sourceId) {
    form.fromDeptId = sourceId
    await loadMembers(sourceId)
  }
})
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>
.allocation-page {
  min-height: calc(100vh - 48px);
  padding: 24px;
  background: #f5f7fa;
}
</style>
