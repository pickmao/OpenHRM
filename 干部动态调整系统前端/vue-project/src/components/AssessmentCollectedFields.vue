<template>
  <div v-if="record" class="collected-fields">
    <a-alert v-if="record.collection_data?.campaign_id" type="info" show-icon>
      <template #message>来源批次：{{ record.collection_data.campaign_name }}</template>
      <template #description>
        已关联 {{ record.collection_data.source_task_ids?.length || 0 }} 份填报原表。
        <span v-if="record.collection_data.protected_fields?.length">已保留 {{ record.collection_data.protected_fields.length }} 项手工修改。</span>
        <a-button type="link" @click="openSource">查看填报来源</a-button>
      </template>
    </a-alert>
    <a-descriptions v-if="!editing && years.length" bordered size="small" :column="1" class="annual-fields">
      <a-descriptions-item v-for="year in years" :key="year" :label="`干事评价（${year}）`"><div class="material-text">{{ record.performance_by_year[year] }}</div></a-descriptions-item>
    </a-descriptions>
    <template v-if="editing">
      <a-form-item v-for="year in years" :key="year" :label="`干事评价（${year}）`"><a-textarea v-model:value="annual[year]" :rows="4" /></a-form-item>
    </template>
    <a-collapse v-if="!editing && (record.collection_data?.warnings?.length || (record.collection_data?.talk_notes && !record.talk_assessment))" ghost>
      <a-collapse-panel key="source" header="谈话材料与待核对事项">
        <div v-if="!record.talk_assessment" class="material-text">{{ record.collection_data?.talk_notes }}</div>
        <p v-for="item in record.collection_data?.warnings || []" :key="item">{{ item }}</p>
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
const props = defineProps({ record: Object, editing: Boolean, annual: { type: Object, default: () => ({}) } })
const router = useRouter()
const years = computed(() => Object.keys(props.editing ? props.annual : props.record?.performance_by_year || {}).sort())
const openSource = () => router.push({ name: 'KnowingPeopleProgress', query: { campaign: props.record.collection_data.campaign_id } })
</script>

<style scoped>
.collected-fields { margin: 16px 0; }
.annual-fields { margin-top: 12px; }
.material-text { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
