<template>
  <div class="page-shell"><a-card title="用户角色分配" :bordered="false"><a-input-search v-model:value="keyword" placeholder="按账号或姓名搜索" style="max-width: 360px; margin-bottom: 16px" @search="loadUsers" /><a-table :columns="columns" :data-source="users" :loading="loading" row-key="id" :pagination="false"><template #bodyCell="{ column, record }"><template v-if="column.key === 'roles'"><a-tag v-for="role in record.roles" :key="role.id">{{ role.name }}</a-tag></template><template v-else-if="column.key === 'action'"><a-button type="link" @click="openEditor(record)">分配角色</a-button></template></template></a-table></a-card><a-modal v-model:open="visible" title="分配角色" @ok="save" :confirm-loading="saving"><div v-if="current"><p>{{ current.real_name || current.username }}</p><a-checkbox-group v-model:value="selectedRoleIds"><a-space direction="vertical"><a-checkbox v-for="role in roles" :key="role.id" :value="role.id">{{ role.name }}（{{ role.code }}）</a-checkbox></a-space></a-checkbox-group></div></a-modal></div>
</template>
<script setup>
import { onMounted, ref } from 'vue'; import { message } from 'ant-design-vue'; import { assignUserRoles, getAdminUsers, getRoles, getUserRoles } from '@/api/admin'
const keyword = ref(''); const users = ref([]); const roles = ref([]); const loading = ref(false); const visible = ref(false); const saving = ref(false); const current = ref(); const selectedRoleIds = ref([])
const columns = [{ title: '账号', dataIndex: 'username' }, { title: '姓名', dataIndex: 'real_name' }, { title: '已分配角色', key: 'roles' }, { title: '操作', key: 'action' }]
const loadUsers = async () => { loading.value = true; try { users.value = await getAdminUsers(keyword.value ? { keyword: keyword.value } : undefined) } catch { message.error('用户列表加载失败') } finally { loading.value = false } }
const openEditor = async (user) => { current.value = user; try { const data = await getUserRoles(user.id); selectedRoleIds.value = data.roles.map(item => item.id); visible.value = true } catch { message.error('用户角色加载失败') } }
const save = async () => { try { saving.value = true; await assignUserRoles(current.value.id, selectedRoleIds.value); message.success('角色已分配'); visible.value = false; loadUsers() } catch (error) { message.error(error.response?.data?.detail || '保存失败') } finally { saving.value = false } }
onMounted(async () => { await Promise.all([loadUsers(), getRoles().then(data => { roles.value = data })]) })
</script>
<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
