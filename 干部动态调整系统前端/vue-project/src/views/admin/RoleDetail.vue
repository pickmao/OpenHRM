<template>
  <div class="page-shell">
    <a-card :title="role ? `配置角色：${role.name}` : '配置角色'" :loading="loading" :bordered="false">
      <a-alert v-if="role" type="info" show-icon :message="`${role.code} · 已分配 ${role.user_count} 名用户`" style="margin-bottom: 16px" />
      <a-checkbox-group v-model:value="selected">
        <a-card v-for="group in catalog" :key="group.module" size="small" :title="group.module" style="margin-bottom: 12px">
          <a-row><a-col v-for="item in group.permissions" :key="item.code" :span="12"><a-checkbox :value="item.code">{{ item.name }} <span class="code">{{ item.code }}</span></a-checkbox></a-col></a-row>
        </a-card>
      </a-checkbox-group>
      <a-space><a-button type="primary" :loading="saving" @click="save">保存权限</a-button><a-button @click="router.push('/admin/roles')">返回</a-button></a-space>
    </a-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { getPermissionCatalog, getRole, updateRolePermissions } from '@/api/admin'
import { registerModelContextTools } from '@/utils/webmcp'
const route = useRoute(); const router = useRouter(); const role = ref(); const catalog = ref([]); const selected = ref([]); const loading = ref(true); const saving = ref(false)
const load = async () => { try { const [roleData, catalogData] = await Promise.all([getRole(route.params.id), getPermissionCatalog()]); role.value = roleData; selected.value = roleData.permissions || []; catalog.value = catalogData.catalog || [] } catch { message.error('角色信息加载失败') } finally { loading.value = false } }
const save = async () => { try { saving.value = true; await updateRolePermissions(route.params.id, selected.value); message.success('权限配置已保存') } catch (error) { message.error(error.response?.data?.permissions?.[0] || '保存失败') } finally { saving.value = false } }
const permissionSchema = { type: 'object', properties: { permissions: { type: 'array', items: { type: 'string', minLength: 1 }, uniqueItems: true, description: '权限编码列表' } }, required: ['permissions'], additionalProperties: false }
const validatePermissions = values => {
  const known = new Set(catalog.value.flatMap(group => group.permissions.map(item => item.code)))
  const unknown = values.find(code => !known.has(code))
  if (unknown) throw new Error(`未知权限编码：${unknown}`)
}
let unregisterWebMcpTools = () => {}
const registerWebMcpTools = () => {
  unregisterWebMcpTools = registerModelContextTools([
    {
      name: 'read_openhrm_role_permissions', title: '读取角色权限',
      description: '读取当前角色及可分配权限目录，不修改数据。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true },
      async execute() { await load(); return { role: role.value && { id: role.value.id, code: role.value.code, name: role.value.name }, selectedPermissions: selected.value, catalog: catalog.value.map(group => ({ module: group.module, permissions: group.permissions.map(({ code, name }) => ({ code, name })) })) } }
    },
    {
      name: 'stage_openhrm_role_permissions', title: '配置角色权限',
      description: '在当前角色页面选择权限，仅修改当前页面的暂存选择，不会保存到系统。',
      inputSchema: permissionSchema, annotations: { readOnlyHint: false },
      async execute(input) { validatePermissions(input.permissions); selected.value = [...input.permissions]; await nextTick(); return { status: 'staged', selectedPermissions: selected.value } }
    },
    {
      name: 'complete_openhrm_role_permissions_update', title: '保存角色权限',
      description: '将给定权限列表保存到当前角色；这是会修改角色授权的操作。',
      inputSchema: permissionSchema, annotations: { readOnlyHint: false },
      async execute(input) { validatePermissions(input.permissions); saving.value = true; try { await updateRolePermissions(route.params.id, input.permissions); selected.value = [...input.permissions]; message.success('权限配置已保存'); return { status: 'saved', roleId: Number(route.params.id), permissionCount: selected.value.length } } finally { saving.value = false } }
    }
  ])
}
onMounted(async () => { registerWebMcpTools(); await load() })
onUnmounted(() => unregisterWebMcpTools())
</script>

<style scoped>.page-shell { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; } .code { color: #8c8c8c; font-size: 12px; }</style>
