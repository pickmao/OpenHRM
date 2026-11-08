<template>
  <div class="page-shell">
    <a-card title="用户管理" :bordered="false">
      <template #extra><a-button v-if="canCreateUser" type="primary" @click="openCreate">新增用户</a-button></template>
      <a-input-search v-model:value="keyword" placeholder="按账号或姓名搜索" style="max-width: 360px; margin-bottom: 16px" @search="loadUsers" />
      <a-table :columns="columns" :data-source="users" :loading="loading" row-key="id" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'roles'"><a-tag v-for="role in record.roles" :key="role.id">{{ role.name }}</a-tag></template>
          <template v-else-if="column.key === 'action'"><a-button type="link" @click="openEditor(record)">分配角色</a-button></template>
        </template>
      </a-table>
    </a-card>
    <a-modal v-model:open="createVisible" title="新增普通用户" ok-text="创建用户" cancel-text="取消" :confirm-loading="creating" @ok="createUser" @after-close="clearCreateForm">
      <p>新用户默认可查看和填写自己的任务。创建后可在用户列表中分配其他角色。</p>
      <a-alert v-if="createErrors.detail" type="error" show-icon :message="createErrors.detail" style="margin-bottom: 16px" />
      <a-form layout="vertical" @submit.prevent="createUser">
        <a-form-item label="登录账号" required :validate-status="createErrors.username ? 'error' : ''" :help="createErrors.username">
          <a-input v-model:value="createForm.username" placeholder="至少 3 个字符，例如 study01" :maxlength="150" autocomplete="off" />
        </a-form-item>
        <a-form-item label="姓名" required :validate-status="createErrors.real_name ? 'error' : ''" :help="createErrors.real_name">
          <a-input v-model:value="createForm.real_name" placeholder="填报人员姓名" :maxlength="50" autocomplete="off" />
        </a-form-item>
        <a-form-item label="初始密码" required :validate-status="createErrors.password ? 'error' : ''" :help="createErrors.password">
          <a-input-password v-model:value="createForm.password" placeholder="至少 8 位，请勿使用纯数字或常见密码" autocomplete="new-password" />
        </a-form-item>
        <a-form-item label="确认密码" required :validate-status="createErrors.confirm_password ? 'error' : ''" :help="createErrors.confirm_password">
          <a-input-password v-model:value="createForm.confirm_password" placeholder="再次输入初始密码" autocomplete="new-password" />
        </a-form-item>
      </a-form>
    </a-modal>
    <a-modal v-model:open="visible" title="分配角色" @ok="save" :confirm-loading="saving">
      <div v-if="current"><p>{{ current.real_name || current.username }}</p><a-checkbox-group v-model:value="selectedRoleIds"><a-space direction="vertical"><a-checkbox v-for="role in roles" :key="role.id" :value="role.id">{{ role.name }}（{{ role.code }}）</a-checkbox></a-space></a-checkbox-group></div>
    </a-modal>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'; import { message } from 'ant-design-vue'; import { assignUserRoles, createAdminUser, getAdminUsers, getRoles, getUserRoles } from '@/api/admin'
import { registerModelContextTools } from '@/utils/webmcp'
import { useUserStore } from '@/stores/user'
const keyword = ref(''); const users = ref([]); const roles = ref([]); const loading = ref(false); const visible = ref(false); const saving = ref(false); const current = ref(); const selectedRoleIds = ref([])
const columns = [{ title: '账号', dataIndex: 'username' }, { title: '姓名', dataIndex: 'real_name' }, { title: '已分配角色', key: 'roles' }, { title: '操作', key: 'action' }]
const userStore = useUserStore()
const canCreateUser = computed(() => userStore.isAdmin || userStore.hasPermission('accounts:user:manage'))
const createVisible = ref(false); const creating = ref(false)
const createForm = reactive({ username: '', real_name: '', password: '', confirm_password: '' })
const createErrors = reactive({})
const clearCreateForm = () => { Object.keys(createForm).forEach(key => { createForm[key] = '' }); Object.keys(createErrors).forEach(key => { delete createErrors[key] }) }
const openCreate = () => { clearCreateForm(); createVisible.value = true }
const createUser = async () => {
  if (creating.value) return
  Object.keys(createErrors).forEach(key => { delete createErrors[key] })
  if (createForm.username.trim().length < 3) createErrors.username = '登录账号至少 3 个字符'
  if (!createForm.real_name.trim()) createErrors.real_name = '请输入姓名'
  if (createForm.password.length < 8) createErrors.password = '密码至少 8 位'
  if (createForm.password !== createForm.confirm_password) createErrors.confirm_password = '两次输入的密码不一致'
  if (Object.keys(createErrors).length) return
  creating.value = true
  try {
    const user = await createAdminUser({ ...createForm, username: createForm.username.trim(), real_name: createForm.real_name.trim() })
    createVisible.value = false
    keyword.value = user.username
    message.success(`用户 ${user.username} 已创建`)
    await loadUsers()
  } catch (error) {
    const data = error.response?.data
    if (data && typeof data === 'object') Object.entries(data).forEach(([key, value]) => { createErrors[key] = Array.isArray(value) ? value.join('；') : String(value) })
    else createErrors.detail = '创建失败，请稍后重试'
  } finally { creating.value = false }
}
const loadUsers = async () => { loading.value = true; try { const data = await getAdminUsers(keyword.value ? { keyword: keyword.value } : undefined); users.value = Array.isArray(data) ? data : data?.results || [] } catch { message.error('用户列表加载失败') } finally { loading.value = false } }
const openEditor = async (user) => { current.value = user; try { const data = await getUserRoles(user.id); selectedRoleIds.value = data.roles.map(item => item.id); visible.value = true } catch { message.error('用户角色加载失败') } }
const save = async () => { try { saving.value = true; await assignUserRoles(current.value.id, selectedRoleIds.value); message.success('角色已分配'); visible.value = false; loadUsers() } catch (error) { message.error(error.response?.data?.detail || '保存失败') } finally { saving.value = false } }
const assignmentSchema = { type: 'object', properties: { userId: { type: 'string', minLength: 1, description: '用户 UUID' }, roleIds: { type: 'array', items: { type: 'string', minLength: 1 }, uniqueItems: true, description: '要分配的角色 UUID 列表' } }, required: ['userId', 'roleIds'], additionalProperties: false }
const stageAssignment = async input => {
  const user = users.value.find(item => item.id === input.userId)
  if (!user) throw new Error('未找到指定用户，请先读取用户列表')
  const knownRoleIds = new Set(roles.value.map(item => item.id)); const unknownId = input.roleIds.find(id => !knownRoleIds.has(id))
  if (unknownId) throw new Error(`未知角色 ID：${unknownId}`)
  current.value = user; selectedRoleIds.value = [...input.roleIds]; visible.value = true; await nextTick()
  return user
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_admin_users', title: '读取可授权用户',
      description: '按可选关键词读取管理员用户、现有角色和角色目录，不修改数据。',
      inputSchema: { type: 'object', properties: { keyword: { type: 'string', description: '账号或姓名关键词' } }, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute(input) { keyword.value = input.keyword?.trim() || ''; await Promise.all([loadUsers(), getRoles().then(data => { roles.value = Array.isArray(data) ? data : data?.results || [] })]); return { users: users.value.map(({ id, username, real_name, roles: userRoles }) => ({ id, username, realName: real_name, roles: (userRoles || []).map(({ id: roleId, code, name }) => ({ id: roleId, code, name })) })), roles: roles.value.map(({ id, code, name }) => ({ id, code, name })) } }
    },
    {
      name: 'stage_openhrm_user_role_assignment', title: '配置用户角色',
      description: '在当前页面选择某用户的角色，仅暂存，不会写入系统。', inputSchema: assignmentSchema, annotations: { readOnlyHint: false },
      async execute(input) { const user = await stageAssignment(input); return { status: 'staged', userId: user.id, username: user.username, roleIds: selectedRoleIds.value } }
    },
    {
      name: 'complete_openhrm_user_role_assignment', title: '保存用户角色',
      description: '为指定用户保存完整角色列表；这会替换该用户现有的角色授权。', inputSchema: assignmentSchema, annotations: { readOnlyHint: false },
      async execute(input) { const user = await stageAssignment(input); saving.value = true; try { await assignUserRoles(user.id, selectedRoleIds.value); await loadUsers(); visible.value = false; message.success('角色已分配'); return { status: 'saved', userId: user.id, roleIds: input.roleIds } } finally { saving.value = false } }
    }
  ])
}
onMounted(async () => { registerWebMcpTools(); await Promise.all([loadUsers(), getRoles().then(data => { roles.value = Array.isArray(data) ? data : data?.results || [] })]) })
onUnmounted(() => unregisterWebMcpTools())
</script>
<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
