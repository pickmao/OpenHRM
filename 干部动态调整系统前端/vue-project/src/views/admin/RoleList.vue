<template>
  <div class="page-shell">
    <a-card title="角色管理" :bordered="false">
      <template #extra><a-button type="primary" @click="router.push('/admin/roles/create')">新建角色</a-button></template>
      <a-table :data-source="roles" :columns="columns" :loading="loading" row-key="id" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'active'"><a-tag :color="record.is_active ? 'green' : 'default'">{{ record.is_active ? '启用' : '停用' }}</a-tag></template>
          <template v-else-if="column.key === 'permissions'">{{ record.permissions.length }} 项权限</template>
          <template v-else-if="column.key === 'actions'"><a-space><a-button type="link" @click="router.push(`/admin/roles/${record.id}`)">配置权限</a-button><a-popconfirm title="确认删除此角色？" @confirm="remove(record)"><a-button type="link" danger>删除</a-button></a-popconfirm></a-space></template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { deleteRole, getRoles } from '@/api/admin'
import { registerModelContextTools } from '@/utils/webmcp'

const router = useRouter()
const loading = ref(false)
const roles = ref([])
const columns = [
  { title: '角色编码', dataIndex: 'code' }, { title: '角色名称', dataIndex: 'name' },
  { title: '权限数', key: 'permissions' }, { title: '用户数', dataIndex: 'user_count' },
  { title: '状态', key: 'active' }, { title: '操作', key: 'actions', width: 180 }
]
const load = async () => {
  loading.value = true
  try {
    const data = await getRoles()
    roles.value = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []
  } catch {
    message.error('角色列表加载失败')
  } finally {
    loading.value = false
  }
}
const remove = async (role) => { try { await deleteRole(role.id); message.success('角色已删除'); load() } catch (error) { message.error(error.response?.data?.detail || '删除失败') } }
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'list_openhrm_roles', title: '读取角色列表',
      description: '读取当前角色及其启用状态、权限数和用户数，不修改数据。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true },
      async execute() { await load(); return { roles: roles.value.map(({ id, code, name, is_active, user_count, permissions }) => ({ id, code, name, isActive: is_active, userCount: user_count, permissionCount: permissions?.length || 0 })) } }
    },
    {
      name: 'start_openhrm_role_creation', title: '开始新建角色',
      description: '打开新建角色页面，仅开始配置，不会创建角色。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true },
      async execute() { await router.push('/admin/roles/create'); return { status: 'ready', route: '/admin/roles/create' } }
    },
    {
      name: 'complete_openhrm_role_deletion', title: '删除角色',
      description: '永久删除指定角色；仅在确认该角色不再需要时使用。',
      inputSchema: { type: 'object', properties: { roleId: { type: 'integer', minimum: 1, description: '要删除的角色 ID' } }, required: ['roleId'], additionalProperties: false },
      annotations: { readOnlyHint: false },
      async execute(input) {
        const role = roles.value.find(item => item.id === input?.roleId)
        if (!role) throw new Error('未找到指定角色，请先读取角色列表')
        await deleteRole(role.id); await load(); message.success('角色已删除')
        return { status: 'deleted', roleId: role.id, roleName: role.name }
      }
    }
  ])
}
onMounted(async () => { registerWebMcpTools(); await load() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
