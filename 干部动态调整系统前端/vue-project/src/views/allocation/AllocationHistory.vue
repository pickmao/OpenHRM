<template>
  <div class="allocation-page">
    <a-card title="调配历史" :bordered="false">
      <a-alert type="info" show-icon message="调配操作会写入审计日志。" description="审计日志查询页面恢复后，可在其中按组织成员变更查看完整历史。" />
    </a-card>
  </div>
</template>

<style scoped>
.allocation-page { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }
</style>
