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
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { deleteRole, getRoles } from '@/api/admin'

const router = useRouter()
const loading = ref(false)
const roles = ref([])
const columns = [
  { title: '角色编码', dataIndex: 'code' }, { title: '角色名称', dataIndex: 'name' },
  { title: '权限数', key: 'permissions' }, { title: '用户数', dataIndex: 'user_count' },
  { title: '状态', key: 'active' }, { title: '操作', key: 'actions', width: 180 }
]
const load = async () => { loading.value = true; try { roles.value = await getRoles() } catch { message.error('角色列表加载失败') } finally { loading.value = false } }
const remove = async (role) => { try { await deleteRole(role.id); message.success('角色已删除'); load() } catch (error) { message.error(error.response?.data?.detail || '删除失败') } }
onMounted(load)
</script>

<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }</style>
