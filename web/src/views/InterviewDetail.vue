<template>
  <div v-if="interview" class="detail-page">
    <div class="back-bar">
      <el-button text :icon="ArrowLeft" @click="$router.back()">返回</el-button>
    </div>

    <div class="detail-grid">
      <div class="main-col">
        <!-- 基本信息 -->
        <section class="panel">
          <div class="iv-head">
            <div>
              <h2 class="iv-title">{{ interview.job_title || '未关联岗位' }}</h2>
              <div class="iv-sub">
                <span class="company">{{ interview.company_name || '-' }}</span>
                <span class="dot">·</span>
                <span>{{ label(INTERVIEW_TYPE, interview.interview_type) }}</span>
                <span class="dot">·</span>
                <span>{{ label(ROUND_TYPE, interview.round_type) }}</span>
                <span class="dot">·</span>
                <span>第 {{ interview.round_no }} 轮</span>
              </div>
            </div>
            <div class="head-tags">
              <el-tag :type="INTERVIEW_STATUS_TAG[interview.status] || 'info'" effect="plain">
                {{ label(INTERVIEW_STATUS, interview.status) }}
              </el-tag>
              <el-tag
                v-if="interview.result"
                :type="INTERVIEW_RESULT_TAG[interview.result] || 'info'"
                effect="plain"
              >
                {{ label(INTERVIEW_RESULT, interview.result) }}
              </el-tag>
            </div>
          </div>

          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">面试时间</span>
              <b>{{ fmt(interview.scheduled_at) || '未安排' }}</b>
            </div>
            <div class="meta-item">
              <span class="meta-label">面试官</span><b>{{ interview.interviewer || '-' }}</b>
            </div>
            <div class="meta-item">
              <span class="meta-label">联系人</span><b>{{ interview.contact_person || '-' }}</b>
            </div>
          </div>

          <div v-if="interview.meeting_url" class="meta-item">
            <span class="meta-label">会议链接</span>
            <a class="link" :href="interview.meeting_url" target="_blank" rel="noopener">
              {{ interview.meeting_url }}
            </a>
          </div>

          <el-divider content-position="left">备注</el-divider>
          <p class="desc-text">{{ interview.notes || '暂无备注' }}</p>

          <!-- 状态流转：只列出后端允许的下一步 -->
          <div v-if="nextStatuses.length" class="action-row">
            <span class="action-label">状态流转</span>
            <el-button
              v-for="s in nextStatuses"
              :key="s"
              size="small"
              :type="s === 'CANCELLED' ? 'danger' : 'primary'"
              :plain="s === 'CANCELLED'"
              :loading="statusLoading === s"
              @click="handleTransition(s)"
            >
              {{ label(INTERVIEW_STATUS, s) }}
            </el-button>
            <span v-if="canAutoReview" class="hint">
              标记「已完成」时会自动触发 Agent 复盘
            </span>
          </div>
        </section>

        <!-- 面试问题记录 -->
        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><ChatLineSquare /></el-icon>面试问题记录</span>
            <el-button size="small" type="primary" :icon="Plus" @click="openQuestionDialog()">
              添加问题
            </el-button>
          </header>

          <el-table :data="questions" row-key="id">
            <el-table-column label="问题" min-width="220">
              <template #default="{ row }">
                <div class="q-text">{{ row.question }}</div>
                <div v-if="row.my_answer" class="q-answer">我的回答：{{ row.my_answer }}</div>
              </template>
            </el-table-column>
            <el-table-column label="自评" width="120">
              <template #default="{ row }">
                <el-tag :type="SELF_RESULT_TAG[row.self_result] || 'info'" size="small" effect="plain">
                  {{ label(SELF_RESULT, row.self_result) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="分类 / 知识点" min-width="180">
              <template #default="{ row }">
                <div v-if="row.category" class="q-cat">
                  {{ row.category }}
                  <el-tag v-if="row.source === 'AGENT'" size="small" type="info" effect="plain">
                    Agent
                  </el-tag>
                </div>
                <div v-else class="q-muted">未分类</div>
                <div v-if="row.knowledge_point" class="q-kp">{{ row.knowledge_point }}</div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openQuestionDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeQuestion(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!questions.length" description="还没有录入面试问题" :image-size="80" />
        </section>
      </div>

      <!-- 右：复盘 -->
      <div class="side-col">
        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><DataAnalysis /></el-icon>面试复盘</span>
            <el-tag size="small" effect="plain" :type="reviewTag">
              {{ label(REVIEW_STATUS, review.status) }}
            </el-tag>
          </header>

          <el-alert
            v-if="review.status === 'FAILED'"
            type="error"
            :closable="false"
            :title="`复盘失败：${review.error_message || '未知原因'}`"
            style="margin-bottom: 12px"
          />

          <div v-if="review.status === 'RUNNING'" class="review-running">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>Interview Agent 正在分析…</span>
          </div>

          <template v-if="review.status === 'SUCCESS'">
            <p class="review-summary">{{ review.summary }}</p>

            <el-divider content-position="left">能力画像</el-divider>
            <div v-for="d in sortedDimensions" :key="d.category" class="dim-row">
              <span class="dim-name">{{ d.category }}</span>
              <el-rate :model-value="d.stars" disabled size="small" />
              <span class="dim-count">{{ d.count }} 题</span>
            </div>

            <template v-if="review.weak_points.length">
              <el-divider content-position="left">薄弱项</el-divider>
              <ul class="review-list">
                <li v-for="(w, i) in review.weak_points" :key="i">{{ w }}</li>
              </ul>
            </template>

            <template v-if="review.review_points.length">
              <el-divider content-position="left">需复习知识点</el-divider>
              <ul class="review-list">
                <li v-for="(p, i) in review.review_points" :key="i">{{ p }}</li>
              </ul>
            </template>

            <div class="review-meta">
              来源：{{ label(REVIEW_SOURCE, review.source) }}
              <template v-if="review.model_name">（{{ review.model_name }}）</template>
              <template v-if="review.duration_ms">· 耗时 {{ review.duration_ms }}ms</template>
            </div>
          </template>

          <el-empty
            v-else-if="review.status === 'NONE'"
            description="尚未复盘"
            :image-size="70"
          />

          <el-button
            v-if="canReview"
            style="width: 100%; margin-top: 12px"
            :loading="review.status === 'RUNNING'"
            @click="handleReview"
          >
            {{ review.status === 'SUCCESS' ? '重新复盘' : '开始复盘' }}
          </el-button>
          <div v-else-if="review.status !== 'RUNNING'" class="hint center">
            面试完成且录入问题后可复盘
          </div>
        </section>

        <!-- 状态流转时间线 -->
        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><Clock /></el-icon>状态记录</span>
          </header>
          <el-timeline v-if="interview.events.length">
            <el-timeline-item
              v-for="e in interview.events"
              :key="e.id"
              :timestamp="fmt(e.created_at)"
              placement="top"
            >
              <div class="tl-main">
                <span v-if="e.from_status">{{ label(INTERVIEW_STATUS, e.from_status) }} →</span>
                <b>{{ label(INTERVIEW_STATUS, e.to_status) }}</b>
                <el-tag size="small" effect="plain">{{ e.operator }}</el-tag>
              </div>
              <div v-if="e.comment" class="tl-comment">{{ e.comment }}</div>
            </el-timeline-item>
          </el-timeline>
          <!-- 早于事件表存在的历史记录没有流转事件，属正常 -->
          <el-empty v-else description="暂无状态流转记录" :image-size="70" />
        </section>
      </div>
    </div>

    <!-- 问题编辑弹窗 -->
    <el-dialog v-model="questionDialog" :title="editingQuestion ? '编辑问题' : '添加问题'" width="560px">
      <el-form :model="questionForm" label-width="90px">
        <el-form-item label="问题" required>
          <el-input v-model="questionForm.question" type="textarea" :rows="2" placeholder="面试官问了什么" />
        </el-form-item>
        <el-form-item label="我的回答">
          <el-input v-model="questionForm.my_answer" type="textarea" :rows="3" placeholder="当时是怎么答的" />
        </el-form-item>
        <el-form-item label="自评">
          <el-select v-model="questionForm.self_result" style="width: 100%">
            <el-option v-for="o in selfResultOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="questionForm.category" placeholder="留空则由 Agent 自动分类" />
        </el-form-item>
        <el-form-item label="知识点">
          <el-input v-model="questionForm.knowledge_point" placeholder="留空则由 Agent 自动填写" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingQuestion" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, ChatLineSquare, Clock, DataAnalysis, Loading, Plus,
} from '@element-plus/icons-vue'
import {
  createInterviewQuestion, deleteInterviewQuestion, getInterview, getInterviewQuestions,
  getInterviewReview, triggerInterviewReview, updateInterviewQuestion, updateInterviewStatus,
} from '@/api'
import {
  INTERVIEW_RESULT, INTERVIEW_RESULT_TAG, INTERVIEW_STATUS, INTERVIEW_STATUS_TAG,
  INTERVIEW_TRANSITIONS, INTERVIEW_TYPE, REVIEW_SOURCE, REVIEW_STATUS, ROUND_TYPE,
  SELF_RESULT, SELF_RESULT_TAG, label, options,
} from '@/constants/interview'

const route = useRoute()
// 同路由换参数时 vue-router 会复用组件实例，onMounted 不会重跑，
// 所以 id 必须是响应式的，并 watch 它重新加载。
const interviewId = computed(() => Number(route.params.id))

const interview = ref(null)
const questions = ref([])
const review = ref({ status: 'NONE', dimensions: [], weak_points: [], review_points: [] })
const statusLoading = ref('')
const selfResultOptions = options(SELF_RESULT)

const questionDialog = ref(false)
const editingQuestion = ref(null)
const savingQuestion = ref(false)
const emptyQuestion = {
  question: '', my_answer: '', self_result: 'PARTIAL', category: '', knowledge_point: '',
}
const questionForm = reactive({ ...emptyQuestion })

let pollTimer = null

const nextStatuses = computed(() => INTERVIEW_TRANSITIONS[interview.value?.status] || [])
const canAutoReview = computed(
  () => interview.value?.status === 'IN_PROGRESS' && questions.value.length > 0,
)
const canReview = computed(
  () => ['COMPLETED', 'REVIEWED'].includes(interview.value?.status)
    && questions.value.length > 0
    && review.value.status !== 'RUNNING',
)
const reviewTag = computed(
  () => ({ SUCCESS: 'success', RUNNING: 'warning', FAILED: 'danger' }[review.value.status] || 'info'),
)
const sortedDimensions = computed(
  () => [...(review.value.dimensions || [])].sort((a, b) => b.score - a.score),
)

function fmt(v) {
  return v ? String(v).slice(0, 16).replace('T', ' ') : ''
}

async function loadInterview() {
  interview.value = await getInterview(interviewId.value)
}
async function loadQuestions() {
  questions.value = await getInterviewQuestions(interviewId.value)
}
async function loadReview() {
  review.value = await getInterviewReview(interviewId.value)
  return review.value.status
}

/** 复盘为异步任务，轮询到 SUCCESS/FAILED 为止 */
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    const status = await loadReview()
    if (status !== 'RUNNING') {
      stopPolling()
      await Promise.all([loadInterview(), loadQuestions()])
      ElMessage[status === 'SUCCESS' ? 'success' : 'error'](
        status === 'SUCCESS' ? '复盘完成' : '复盘失败',
      )
    }
  }, 2000)
}
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleTransition(status) {
  if (status === 'CANCELLED') {
    await ElMessageBox.confirm('确定取消这场面试吗？取消后不可再流转。', '提示', { type: 'warning' })
  }
  statusLoading.value = status
  try {
    interview.value = await updateInterviewStatus(interviewId.value, { status })
    ElMessage.success(`已标记为${label(INTERVIEW_STATUS, status)}`)
    // 流转到 COMPLETED 且已有问题时后端会自动触发复盘
    if (status === 'COMPLETED' && questions.value.length) {
      if ((await loadReview()) === 'RUNNING') startPolling()
    }
  } finally {
    statusLoading.value = ''
  }
}

async function handleReview() {
  review.value = await triggerInterviewReview(interviewId.value)
  if (review.value.status === 'RUNNING') startPolling()
}

function openQuestionDialog(row) {
  editingQuestion.value = row || null
  Object.assign(questionForm, emptyQuestion, row ? {
    question: row.question,
    my_answer: row.my_answer || '',
    self_result: row.self_result,
    category: row.category || '',
    knowledge_point: row.knowledge_point || '',
  } : {})
  questionDialog.value = true
}

async function saveQuestion() {
  if (!questionForm.question.trim()) {
    ElMessage.warning('请填写面试问题')
    return
  }
  savingQuestion.value = true
  try {
    const payload = { ...questionForm }
    if (editingQuestion.value) {
      await updateInterviewQuestion(interviewId.value, editingQuestion.value.id, payload)
    } else {
      await createInterviewQuestion(interviewId.value, payload)
    }
    ElMessage.success('已保存')
    questionDialog.value = false
    await loadQuestions()
  } finally {
    savingQuestion.value = false
  }
}

async function removeQuestion(row) {
  await ElMessageBox.confirm('确定删除这条面试问题吗？', '提示', { type: 'warning' })
  await deleteInterviewQuestion(interviewId.value, row.id)
  ElMessage.success('已删除')
  await loadQuestions()
}

async function loadAll() {
  await Promise.all([loadInterview(), loadQuestions()])
  if ((await loadReview()) === 'RUNNING') startPolling()
}

// 详情页之间互相跳转时组件被复用，靠 watch 重新拉数据
watch(interviewId, () => {
  stopPolling()
  loadAll()
})

onMounted(loadAll)
onUnmounted(stopPolling)
</script>

<style scoped>
.back-bar { margin-bottom: 12px; }
.detail-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; }
.main-col, .side-col { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.panel {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 16px 20px;
}
.iv-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.iv-title { margin: 0 0 6px; font-size: 20px; color: var(--jf-ink); }
.iv-sub { color: var(--jf-muted); font-size: 13px; }
.iv-sub .company { color: var(--jf-ink-soft); font-weight: 600; }
.dot { margin: 0 6px; }
.head-tags { display: flex; gap: 6px; flex-shrink: 0; }
.meta-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
.meta-item { font-size: 13px; }
.meta-label { display: block; color: var(--jf-muted); margin-bottom: 2px; }
.link { color: var(--el-color-primary); word-break: break-all; }
.desc-text { color: var(--jf-ink-soft); line-height: 1.7; white-space: pre-wrap; margin: 0; }
.action-row {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--jf-border);
}
.action-label { color: var(--jf-muted); font-size: 13px; margin-right: 4px; }
.hint { color: var(--jf-muted); font-size: 12px; }
.hint.center { display: block; text-align: center; margin-top: 12px; }
.q-text { color: var(--jf-ink); }
.q-answer { color: var(--jf-muted); font-size: 12px; margin-top: 4px; }
.q-cat { display: flex; align-items: center; gap: 6px; color: var(--jf-ink); }
.q-kp { color: var(--jf-muted); font-size: 12px; margin-top: 2px; }
.q-muted { color: var(--jf-muted); }
.review-running { display: flex; align-items: center; gap: 8px; color: var(--jf-muted); padding: 12px 0; }
.review-summary { color: var(--jf-ink-soft); line-height: 1.7; margin: 0; }
.dim-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dim-name { flex: 1; font-size: 13px; color: var(--jf-ink); min-width: 0; }
.dim-count { color: var(--jf-muted); font-size: 12px; flex-shrink: 0; }
.review-list { margin: 0; padding-left: 18px; color: var(--jf-ink-soft); font-size: 13px; line-height: 1.8; }
.review-meta { margin-top: 14px; color: var(--jf-muted); font-size: 12px; }
.tl-main { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--jf-ink-soft); }
.tl-comment { color: var(--jf-muted); font-size: 12px; margin-top: 2px; }
@media (max-width: 1100px) {
  .detail-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
