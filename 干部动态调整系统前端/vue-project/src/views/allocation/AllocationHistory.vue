<template>
  <div class="allocation-page">
    <a-card title="调配历史" :bordered="false">
      <a-alert
        type="info"
        show-icon
        message="调配为直接生效模式"
        description="每次部门调配会写入审计日志。完整历史查询页面尚未恢复，请先使用「部门调配」完成即时调配。"
        style="margin-bottom: 16px"
      />
      <a-empty description="调配历史查询尚未恢复">
        <a-button type="primary" @click="$router.push('/allocation/plan')">前往部门调配</a-button>
      </a-empty>
    </a-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { registerModelContextTools } from '@/utils/webmcp'

let unregisterWebMcpTools = () => {}
onMounted(() => {
  unregisterWebMcpTools = registerModelContextTools([{
    name: 'read_openhrm_allocation_history_status',
    title: '读取调配历史状态',
    description: '读取调配历史页面当前可用性；完整审计日志查询页面尚未恢复。',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
    async execute() {
      return { auditHistoryAvailable: false, mode: 'direct_effect', message: '调配操作会写入审计日志；查询页面尚未恢复。' }
    }
  }])
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
