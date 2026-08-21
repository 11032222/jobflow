<template>
  <div>
    <!-- 面试知识库：跨面试沉淀的能力画像（文档 3.10 结尾） -->
    <section v-if="knowledge.total_questions" class="panel kb-panel">
      <header class="panel-header">
        <span class="panel-title"><el-icon><TrendCharts /></el-icon>我的面试能力画像</span>
        <span class="kb-meta">
          {{ knowledge.total_questions }} 题 · {{ knowledge.interview_count }} 场面试
          <template v-if="knowledge.uncategorized">· {{ knowledge.uncategorized }} 题未分类</template>
        </span>
      </header>

      <el-alert
        v-if="knowledge.weak_categories.length"
        type="warning"
        :closable="false"
        show-icon
        :title="`薄弱方向：${knowledge.weak_categories.join('、')}`"
        style="margin-bottom: 12px"
      />

      <div class="kb-grid">
        <div v-for="d in knowledge.categories" :key="d.category" class="kb-item">
          <div class="kb-row">
            <span class="kb-name">{{ d.category }}</span>
            <el-rate :model-value="d.stars" disabled size="small" />
            <span :class="['kb-trend', trendClass(d.delta)]">{{ trendText(d.delta) }}</span>
          </div>
          <div class="kb-sub">
            {{ d.count }} 题 / {{ d.interview_count }} 场 ·
            掌握 {{ d.mastered }} · 不完整 {{ d.partial }} · 不会 {{ d.failed }}
          </div>
        </div>
      </div>

      <template v-if="knowledge.review_points.length">
        <el-divider content-position="left">待复习知识点</el-divider>
        <div class="kb-tags">
          <el-tag
            v-for="rp in knowledge.review_points"
            :key="rp.knowledge_point"
            size="small"
            type="info"
            effect="plain"
          >
            {{ rp.knowledge_point }}<template v-if="rp.count > 1"> × {{ rp.count }}</template>
          </el-tag>
        </div>
      </template>
    </section>

    <section class="panel">
      <header class="panel-header">
        <span class="panel-title"><el-icon><Calendar /></el-icon>面试日程</span>
        <el-button type="primary" :icon="Plus" @click="openDialog()">添加面试</el-button>
      </header>

      <el-table :data="interviews" @row-click="goDetail" class="clickable">
        <el-table-column label="公司 / 职位" min-width="200">
          <template #default="{ row }">
            <div class="job-title">{{ row.job_title || '未关联岗位' }}</div>
            <div class="company">{{ row.company_name || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="方式 / 性质" width="160">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ label(INTERVIEW_TYPE, row.interview_type) }}</el-tag>
            <span class="round">{{ label(ROUND_TYPE, row.round_type) }} · 第 {{ row.round_no }} 轮</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="150">
          <template #default="{ row }">{{ fmt(row.scheduled_at) || '未安排' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="INTERVIEW_STATUS_TAG[row.status] || 'info'" size="small" effect="plain">
              {{ label(INTERVIEW_STATUS, row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag
              v-if="row.result"
              :type="INTERVIEW_RESULT_TAG[row.result] || 'info'"
              size="small"
              effect="plain"
            >
              {{ label(INTERVIEW_RESULT, row.result) }}
            </el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.notes || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="goDetail(row)">详情 / 复盘</el-button>
            <el-button link type="primary" @click.stop="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!interviews.length" description="暂无面试记录" :image-size="80" />
    </section>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑面试' : '添加面试'" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="岗位">
          <el-select v-model="form.job_id" placeholder="关联岗位（选填）" clearable filterable style="width: 100%">
            <el-option
              v-for="j in appliedJobs"
              :key="j.job_id"
              :label="`${j.job_title}（${j.company_name}）`"
              :value="j.job_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="面试方式">
          <el-select v-model="form.interview_type" clearable style="width: 100%">
            <el-option v-for="o in typeOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="面试性质">
          <el-select v-model="form.round_type" clearable style="width: 100%">
            <el-option v-for="o in roundTypeOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="轮次">
          <el-input-number v-model="form.round_no" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker
            v-model="form.scheduled_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="面试官"><el-input v-model="form.interviewer" /></el-form-item>
        <el-form-item label="面试结果">
          <el-select v-model="form.result" clearable style="width: 100%">
            <el-option v-for="o in resultOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="会议链接"><el-input v-model="form.meeting_url" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="反馈">
          <el-input v-model="form.feedback" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, Plus, TrendCharts } from '@element-plus/icons-vue'
import {
  createInterview, deleteInterview, getApplications, getInterviewKnowledge,
  getInterviews, updateInterview,
} from '@/api'
import {
  INTERVIEW_RESULT, INTERVIEW_RESULT_TAG, INTERVIEW_STATUS, INTERVIEW_STATUS_TAG,
  INTERVIEW_TYPE, ROUND_TYPE, label, options,
} from '@/constants/interview'

const router = useRouter()
const interviews = ref([])
const knowledge = ref({
  total_questions: 0, uncategorized: 0, interview_count: 0,
  categories: [], weak_categories: [], review_points: [],
})
const appliedJobs = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const saving = ref(false)

const typeOptions = options(INTERVIEW_TYPE)
const roundTypeOptions = options(ROUND_TYPE)
const resultOptions = options(INTERVIEW_RESULT)

// 注意：不含 status。状态一律走详情页的状态机接口，PUT 不接受 status。
const emptyForm = {
  id: null, application_id: null, company_id: null, job_id: null,
  interview_type: 'VIDEO', round_type: 'TECHNICAL', round_no: 1, scheduled_at: null,
  interviewer: '', result: null, contact_person: '', contact_phone: '',
  address: '', meeting_url: '', notes: '', feedback: '',
}
const form = reactive({ ...emptyForm })

function fmt(v) {
  return v ? String(v).slice(0, 16).replace('T', ' ') : ''
}

function goDetail(row) {
  router.push({ name: 'InterviewDetail', params: { id: row.id } })
}

async function load() {
  interviews.value = await getInterviews()
  appliedJobs.value = await getApplications()
  knowledge.value = await getInterviewKnowledge()
}

/** delta 为 null 表示该分类只出现在前期或只出现在近期，无法比较 */
function trendText(delta) {
  if (delta === null || delta === undefined) return ''
  if (delta > 0) return `↑ +${delta}`
  if (delta < 0) return `↓ ${delta}`
  return '→ 持平'
}
function trendClass(delta) {
  if (delta === null || delta === undefined) return ''
  return delta > 0 ? 'up' : (delta < 0 ? 'down' : '')
}

function openDialog(row) {
  editing.value = !!row
  if (row) {
    Object.assign(form, emptyForm, {
      id: row.id, application_id: row.application_id, company_id: row.company_id,
      job_id: row.job_id, interview_type: row.interview_type, round_type: row.round_type,
      round_no: row.round_no, scheduled_at: row.scheduled_at, interviewer: row.interviewer,
      result: row.result, contact_person: row.contact_person, contact_phone: row.contact_phone,
      address: row.address, meeting_url: row.meeting_url, notes: row.notes, feedback: row.feedback,
    })
  } else {
    Object.assign(form, emptyForm)
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form }
    delete payload.id
    const app = appliedJobs.value.find((a) => a.job_id === form.job_id)
    if (app) {
      payload.application_id = app.id
      payload.company_id = app.company_id
    }
    if (editing.value) {
      await updateInterview(form.id, payload)
    } else {
      await createInterview(payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除这条面试记录吗？关联的问题与复盘会一并删除。', '提示', {
    type: 'warning',
  })
  await deleteInterview(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.panel {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 16px 20px;
}
.clickable :deep(.el-table__row) { cursor: pointer; }
.job-title { font-weight: 600; color: var(--jf-ink); }
.company { color: var(--jf-muted); font-size: 12px; margin-top: 2px; }
.round { margin-left: 6px; color: var(--jf-ink-soft); font-size: 12px; }
.muted { color: var(--jf-muted); }
.kb-panel { margin-bottom: 16px; }
.kb-meta { color: var(--jf-muted); font-size: 12px; }
.kb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px 20px; }
.kb-row { display: flex; align-items: center; gap: 8px; }
.kb-name { flex: 1; font-size: 13px; color: var(--jf-ink); min-width: 0; }
.kb-trend { font-size: 12px; color: var(--jf-muted); flex-shrink: 0; }
.kb-trend.up { color: var(--el-color-success); }
.kb-trend.down { color: var(--el-color-danger); }
.kb-sub { color: var(--jf-muted); font-size: 12px; margin-top: 2px; }
.kb-tags { display: flex; flex-wrap: wrap; gap: 6px; }
</style>
