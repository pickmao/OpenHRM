<template>
  <div class="allocation-page">
    <a-card title="部门调配" :bordered="false">
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
            <a-button type="primary" :disabled="!canTransfer" :loading="submitting" @click="submit">提交调配</a-button>
            <a-button @click="reset">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
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
const today = () => new Date().toISOString().slice(0, 10)

const form = reactive({ fromDeptId: undefined, toDeptId: undefined, memberIds: [], effectiveDate: today(), newPosition: '', reason: '' })
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
  Object.assign(form, { fromDeptId: undefined, toDeptId: undefined, memberIds: [], effectiveDate: today(), newPosition: '', reason: '' })
  members.value = []
  formRef.value?.clearValidate()
}

const submit = async () => {
  try {
    await formRef.value.validate()
    if (form.fromDeptId === form.toDeptId) {
      message.warning('调出部门和调入部门不能相同')
      return
    }
    submitting.value = true
    const result = await createTransferRequest({
      members: form.memberIds,
      from_dept: form.fromDeptId,
      to_dept: form.toDeptId,
      effective_date: form.effectiveDate,
      reason: form.reason,
      new_position: form.newPosition || undefined
    })
    if (result.failed) message.warning(`调配完成：成功 ${result.success} 人，失败 ${result.failed} 人`)
    else message.success(`已完成 ${result.success} 人的部门调配`)
    reset()
  } catch (error) {
    if (!error?.errorFields) message.error(error.response?.data?.error || '提交调配失败')
  } finally {
    submitting.value = false
  }
}

const transferSchema = { type: 'object', properties: { fromDepartmentId: { type: 'integer', minimum: 1 }, toDepartmentId: { type: 'integer', minimum: 1 }, memberIds: { type: 'array', items: { type: 'integer', minimum: 1 }, minItems: 1, uniqueItems: true }, effectiveDate: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' }, reason: { type: 'string', minLength: 1, maxLength: 500 }, newPosition: { type: 'string' } }, required: ['fromDepartmentId', 'toDepartmentId', 'memberIds', 'effectiveDate', 'reason'], additionalProperties: false }
const stageTransfer = async input => {
  if (!canTransfer.value) throw new Error('当前账号没有人员调配权限')
  if (input.fromDepartmentId === input.toDepartmentId) throw new Error('调出部门和调入部门不能相同')
  form.fromDeptId = input.fromDepartmentId; await loadMembers(input.fromDepartmentId)
  const allowedMemberIds = new Set(memberOptions.value.map(item => item.value)); const unknown = input.memberIds.find(id => !allowedMemberIds.has(id))
  if (unknown) throw new Error(`人员 ${unknown} 不属于所选调出部门`)
  Object.assign(form, { toDeptId: input.toDepartmentId, memberIds: [...input.memberIds], effectiveDate: input.effectiveDate, reason: input.reason.trim(), newPosition: input.newPosition?.trim() || '' })
  await nextTick()
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_transfer_options', title: '读取调配选项', description: '读取组织树；提供调出部门后同时读取可调配人员，不会提交调配。',
      inputSchema: { type: 'object', properties: { fromDepartmentId: { type: 'integer', minimum: 1 } }, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { await loadTree(); if (input.fromDepartmentId) { form.fromDeptId = input.fromDepartmentId; await loadMembers(input.fromDepartmentId) } return { canTransfer: canTransfer.value, departmentTree: deptTree.value, members: memberOptions.value.map(({ value, label }) => ({ userId: value, label })) } }
    },
    {
      name: 'stage_openhrm_department_transfer', title: '配置人员调配', description: '在当前调配页面选择部门、人员、日期和原因，仅暂存，不会提交调配。', inputSchema: transferSchema, annotations: { readOnlyHint: false },
      async execute(input) { await stageTransfer(input); return { status: 'staged', fromDepartmentId: form.fromDeptId, toDepartmentId: form.toDeptId, memberIds: form.memberIds, effectiveDate: form.effectiveDate } }
    },
    {
      name: 'complete_openhrm_department_transfer', title: '提交人员调配', description: '将指定人员从调出部门调配到调入部门；这会立即修改人员组织归属。', inputSchema: transferSchema, annotations: { readOnlyHint: false },
      async execute(input) { await stageTransfer(input); await formRef.value.validate(); submitting.value = true; try { const result = await createTransferRequest({ members: form.memberIds, from_dept: form.fromDeptId, to_dept: form.toDeptId, effective_date: form.effectiveDate, reason: form.reason, new_position: form.newPosition || undefined }); message.success(`已完成 ${result.success || 0} 人的部门调配`); reset(); return { status: 'completed', success: result.success || 0, failed: result.failed || 0 } } finally { submitting.value = false } }
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
.allocation-page { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }
</style>
