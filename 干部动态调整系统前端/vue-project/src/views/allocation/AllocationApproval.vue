<template>
  <div class="allocation-page">
    <a-card title="调配审批" :bordered="false">
      <a-empty description="当前恢复的调配功能为直接生效模式，暂无待审批调配单。" />
    </a-card>
  </div>
</template>

<style scoped>
.allocation-page { min-height: calc(100vh - 48px); padding: 24px; background: #f5f7fa; }
</style>
