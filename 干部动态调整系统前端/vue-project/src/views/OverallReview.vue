<template>
  <div class="review-page">
    <a-page-header title="员工整体评价" sub-title="先核对人员和证据，再生成待人工审核的 Qwen 草稿" />
    <a-card title="查找人员">
      <a-space>
        <a-input-search v-model:value="name" placeholder="输入姓名" style="width: 260px" :loading="searching" @search="search" />
        <span>姓名仅用于检索；同名人员须按部门和职务选择。</span>
      </a-space>
      <a-table v-if="candidates.length" :columns="columns" :data-source="candidates" row-key="id" size="small" :pagination="false" style="margin-top: 16px">
        <template #bodyCell="{ column, record }">
          <a-button v-if="column.key === 'action'" type="link" @click="selectPerson(record)">查看资料</a-button>
        </template>
      </a-table>
    </a-card>

    <a-card v-if="snapshot" :title="`${snapshot.person.name} · ${snapshot.person.department} · ${snapshot.person.position || '职务未填'}`" style="margin-top: 16px">
      <a-alert type="info" show-icon message="以下是拟发送给 Qwen 的结构化资料。仅有 Excel 文档的填报不含正文；请核对来源、缺项和年份。" style="margin-bottom: 16px" />
      <a-alert v-for="warning in snapshot.warnings" :key="warning" type="warning" show-icon :message="warning" style="margin-bottom: 8px" />
      <a-collapse>
        <a-collapse-panel v-for="section in sections" :key="section.key" :header="`${section.label}（${snapshot.sections[section.key]?.length || 0}）`">
          <a-empty v-if="!snapshot.sections[section.key]?.length" description="暂无可靠关联的记录" />
          <pre v-else v-for="(row, index) in snapshot.sections[section.key]" :key="row.source || index" class="evidence">{{ pretty(row) }}</pre>
        </a-collapse-panel>
      </a-collapse>
      <a-space style="margin-top: 18px">
        <a-checkbox v-model:checked="confirmed">我已核对预览资料，并同意将其发送至 Qwen 服务生成草稿</a-checkbox>
        <a-button type="primary" :disabled="!confirmed || !canGenerate" :loading="generating" @click="generate">生成评价草稿</a-button>
      </a-space>
      <a-alert v-if="!canGenerate" type="warning" message="生成草稿需要“Qwen评价草稿”权限；当前账号可查看资料。" style="margin-top: 12px" />
    </a-card>

    <a-card v-if="draft" title="Qwen 整体评价草稿 · 待人工核对" style="margin-top: 16px">
      <a-alert type="warning" message="请逐条核对来源，不能将草稿作为自动人事决定。" show-icon style="margin-bottom: 16px" />
      <pre class="draft">{{ draft }}</pre>
    </a-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import { overallReviewApi } from '@/api/overallReview'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const canGenerate = computed(() => userStore.userInfo?.is_superuser || userStore.hasPermission?.('cadres:overall_review:generate'))
const name = ref('')
const searching = ref(false)
const generating = ref(false)
const candidates = ref([])
const snapshot = ref(null)
const confirmed = ref(false)
const draft = ref('')
const columns = [
  { title: '姓名', dataIndex: 'name' }, { title: '部门', dataIndex: 'department' },
  { title: '职务', dataIndex: 'position' }, { title: '干部编号', dataIndex: 'cadre_code' },
  { title: '操作', key: 'action' }
]
const sections = [
  { key: 'basic', label: '人员与职位' }, { key: 'resumes', label: '任职履历' },
  { key: 'assessments', label: '年度研判' }, { key: 'self_forms', label: '自评与述事' },
  { key: 'ratings', label: '个人测评汇总' }, { key: 'work', label: '知事识人纪实' },
  { key: 'anonymous_evaluations', label: '匿名测评汇总' },
  { key: 'recommendations', label: '优秀干部推荐汇总' },
  { key: 'other_forms', label: '其他网上填报' }, { key: 'rewards', label: '个人奖励' }
]
const pretty = value => JSON.stringify(value, null, 2)

async function search() {
  snapshot.value = null
  draft.value = ''
  candidates.value = []
  if (!name.value.trim()) return message.warning('请输入姓名')
  searching.value = true
  try {
    const response = await overallReviewApi.search(name.value.trim())
    candidates.value = response.results || []
    if (!candidates.value.length) message.info('未找到可查看的人员')
  } catch (error) {
    message.error(error.response?.data?.detail || '检索失败')
  } finally {
    searching.value = false
  }
}

async function selectPerson(person) {
  draft.value = ''
  confirmed.value = false
  try {
    snapshot.value = await overallReviewApi.preview(person.id)
  } catch (error) {
    message.error(error.response?.data?.detail || '读取资料失败')
  }
}

async function generate() {
  if (!snapshot.value || !confirmed.value) return
  generating.value = true
  draft.value = ''
  try {
    const response = await overallReviewApi.generate(snapshot.value.person.id, snapshot.value.digest)
    draft.value = response.draft
  } catch (error) {
    message.error(error.response?.data?.detail || '生成失败')
    if (error.response?.status === 409) {
      snapshot.value = await overallReviewApi.preview(snapshot.value.person.id)
      confirmed.value = false
    }
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.review-page { padding: 8px 0; }
.evidence, .draft { white-space: pre-wrap; overflow-wrap: anywhere; font-family: inherit; line-height: 1.65; }
.evidence { padding: 12px; background: #f7f8fa; border-radius: 4px; }
.draft { font-size: 14px; }
</style>
