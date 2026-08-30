<template>
  <div class="page-shell"><a-card title="用户角色分配" :bordered="false"><a-input-search v-model:value="keyword" placeholder="按账号或姓名搜索" style="max-width: 360px; margin-bottom: 16px" @search="loadUsers" /><a-table :columns="columns" :data-source="users" :loading="loading" row-key="id" :pagination="false"><template #bodyCell="{ column, record }"><template v-if="column.key === 'roles'"><a-tag v-for="role in record.roles" :key="role.id">{{ role.name }}</a-tag></template><template v-else-if="column.key === 'action'"><a-button type="link" @click="openEditor(record)">分配角色</a-button></template></template></a-table></a-card><a-modal v-model:open="visible" title="分配角色" @ok="save" :confirm-loading="saving"><div v-if="current"><p>{{ current.real_name || current.username }}</p><a-checkbox-group v-model:value="selectedRoleIds"><a-space direction="vertical"><a-checkbox v-for="role in roles" :key="role.id" :value="role.id">{{ role.name }}（{{ role.code }}）</a-checkbox></a-space></a-checkbox-group></div></a-modal></div>
</template>
<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'; import { message } from 'ant-design-vue'; import { assignUserRoles, getAdminUsers, getRoles, getUserRoles } from '@/api/admin'
import { registerModelContextTools } from '@/utils/webmcp'
const keyword = ref(''); const users = ref([]); const roles = ref([]); const loading = ref(false); const visible = ref(false); const saving = ref(false); const current = ref(); const selectedRoleIds = ref([])
const columns = [{ title: '账号', dataIndex: 'username' }, { title: '姓名', dataIndex: 'real_name' }, { title: '已分配角色', key: 'roles' }, { title: '操作', key: 'action' }]
const loadUsers = async () => { loading.value = true; try { const data = await getAdminUsers(keyword.value ? { keyword: keyword.value } : undefined); users.value = Array.isArray(data) ? data : data?.results || [] } catch { message.error('用户列表加载失败') } finally { loading.value = false } }
const openEditor = async (user) => { current.value = user; try { const data = await getUserRoles(user.id); selectedRoleIds.value = data.roles.map(item => item.id); visible.value = true } catch { message.error('用户角色加载失败') } }
const save = async () => { try { saving.value = true; await assignUserRoles(current.value.id, selectedRoleIds.value); message.success('角色已分配'); visible.value = false; loadUsers() } catch (error) { message.error(error.response?.data?.detail || '保存失败') } finally { saving.value = false } }
const assignmentSchema = { type: 'object', properties: { userId: { type: 'integer', minimum: 1, description: '用户 ID' }, roleIds: { type: 'array', items: { type: 'integer', minimum: 1 }, uniqueItems: true, description: '要分配的角色 ID 列表' } }, required: ['userId', 'roleIds'], additionalProperties: false }
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
