<template>
  <div>
    <el-tabs v-model="activeTab" class="iv-tabs">
      <el-tab-pane label="面试日程" name="schedule">
        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><Calendar /></el-icon>面试日程</span>
            <el-button type="primary" :icon="Plus" @click="openInterviewDialog()">添加面试</el-button>
          </header>

          <el-table :data="interviews">
            <el-table-column label="公司 / 职位" min-width="200">
              <template #default="{ row }">
                <div class="job-title">{{ row.job_title || '-' }}</div>
                <div class="company">{{ row.company_name }}</div>
              </template>
            </el-table-column>
            <el-table-column label="类型 / 轮次" width="130">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.interview_type }}</el-tag>
                <span class="round">第 {{ row.round_no }} 轮</span>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="165">
              <template #default="{ row }">{{ fmtTime(row.scheduled_at) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="ivType(row.status)" size="small" effect="plain">{{ ivText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="推进" width="140">
              <template #default="{ row }">
                <template v-if="nextRows(row).length">
                  <el-dropdown trigger="click" @command="(s) => advance(row, s)">
                    <el-button link type="primary">推进<el-icon><ArrowDown /></el-icon></el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item v-for="s in nextRows(row)" :key="s" :command="s">{{ ivText(s) }}</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </template>
                <span v-else class="text-muted">终态</span>
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.notes || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openInterviewDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="handleInterviewDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!interviews.length" description="暂无面试记录" :image-size="80" />
        </section>
      </el-tab-pane>

      <el-tab-pane label="面试知识库" name="knowledge">
        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><Collection /></el-icon>面试知识库</span>
            <div class="panel-actions">
              <el-input v-model="searchKeyword" placeholder="搜索公司 / 岗位 / 标题" clearable :prefix-icon="Search" style="width: 240px" />
              <el-button type="primary" :icon="Plus" @click="openNewSession">新建会话</el-button>
            </div>
          </header>

          <p class="kb-hint">整段录音、腾讯会议录屏或手动录入的问答会汇总在这里，形成可持续积累的面试知识库。</p>

          <div v-loading="sessionsLoading" class="session-grid">
            <div v-for="s in filteredSessions" :key="s.id" class="session-card" @click="openSessionDetailById(s.id)">
              <div class="session-card-head">
                <span class="session-title">{{ s.title }}</span>
                <el-tag :type="sourceMeta(s.source).type" size="small" effect="plain">{{ sourceMeta(s.source).label }}</el-tag>
              </div>
              <div class="session-sub">
                <span v-if="s.company_name">{{ s.company_name }}</span>
                <span v-if="s.job_title">{{ s.job_title }}</span>
                <span v-if="!s.company_name && !s.job_title" class="text-muted">未关联公司 / 岗位</span>
              </div>
              <div class="session-foot">
                <span class="text-muted">{{ fmtTime(s.created_at) }}</span>
                <span class="qa-count">{{ s.question_count }} 条问答</span>
              </div>
            </div>
          </div>
          <el-empty v-if="!sessionsLoading && !filteredSessions.length" description="还没有面试会话，点击「新建会话」开始记录" :image-size="90" />
        </section>
      </el-tab-pane>
    </el-tabs>

    <!-- 面试日程编辑 -->
    <el-dialog v-model="interviewDialogVisible" :title="interviewEditing ? '编辑面试' : '添加面试'" width="560px">
      <el-form :model="interviewForm" label-width="90px">
        <el-form-item label="岗位">
          <el-select v-model="interviewForm.job_id" placeholder="关联岗位（选填）" clearable filterable style="width: 100%">
            <el-option v-for="j in appliedJobs" :key="j.job_id" :label="`${j.job_title}（${j.company_name}）`" :value="j.job_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="面试类型">
          <el-select v-model="interviewForm.interview_type" style="width: 100%">
            <el-option label="电话面试" value="电话面试" />
            <el-option label="视频面试" value="视频面试" />
            <el-option label="现场面试" value="现场面试" />
            <el-option label="笔试" value="笔试" />
          </el-select>
        </el-form-item>
        <el-form-item label="轮次"><el-input-number v-model="interviewForm.round_no" :min="1" :max="10" /></el-form-item>
        <el-form-item label="时间">
          <el-date-picker v-model="interviewForm.scheduled_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="interviewForm.status" style="width: 100%">
            <el-option label="已安排" value="SCHEDULED" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已完成" value="COMPLETED" />
            <el-option label="已复盘" value="REVIEWED" />
            <el-option label="已取消" value="CANCELLED" />
          </el-select>
        </el-form-item>
        <el-form-item label="会议链接"><el-input v-model="interviewForm.meeting_url" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="interviewForm.contact_person" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="interviewForm.contact_phone" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="interviewForm.notes" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="反馈"><el-input v-model="interviewForm.feedback" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="interviewDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="interviewSaving" @click="handleInterviewSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建会话 -->
    <el-dialog v-model="newDialogVisible" title="新建面试会话" width="620px" @closed="onNewDialogClosed">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="newForm.title" placeholder="如：字节跳动 后端一面" /></el-form-item>
        <el-form-item label="公司"><el-input v-model="newForm.company_name" placeholder="选填" /></el-form-item>
        <el-form-item label="岗位"><el-input v-model="newForm.job_title" placeholder="选填" /></el-form-item>
        <el-form-item label="方式">
          <el-radio-group v-model="newMode">
            <el-radio-button label="recording">录音</el-radio-button>
            <el-radio-button label="upload">上传</el-radio-button>
            <el-radio-button label="manual">手动</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <div class="new-mode-body">
        <template v-if="newMode === 'recording'">
          <div class="record-zone">
            <div class="record-status">
              <span v-if="recording" class="rec-dot"></span>
              <span>{{ recording ? `正在录音 ${formatSeconds(recordingSeconds)}` : '点击开始后整段录制，停止后自动转写并拆分问答' }}</span>
            </div>
          </div>
        </template>
        <template v-else-if="newMode === 'upload'">
          <div class="upload-zone">
            <el-icon :size="26"><UploadFilled /></el-icon>
            <p>上传音频或视频文件（支持 mp3 / wav / m4a / mp4 / mov 等，腾讯会议录屏请选 mp4）</p>
            <p v-if="selectedFile" class="selected-file">已选择：{{ selectedFile.name }}</p>
          </div>
        </template>
        <template v-else>
          <div class="manual-hint">创建空会话后，可在详情中手动逐条添加问答。</div>
        </template>
      </div>

      <template #footer>
        <el-button @click="newDialogVisible = false">取消</el-button>
        <el-button
          v-if="newMode === 'manual'"
          type="primary"
          :loading="submitting"
          @click="createManualSession"
        >创建会话</el-button>
        <el-button
          v-else-if="newMode === 'upload'"
          type="primary"
          :loading="submitting"
          @click="triggerFilePick"
        >选择文件并转写</el-button>
        <el-button
          v-else
          :type="recording ? 'danger' : 'primary'"
          :loading="submitting"
          @click="recording ? stopAndTranscribe() : startRecording()"
        >{{ recording ? '停止并转写' : '开始录音' }}</el-button>
      </template>
    </el-dialog>

    <!-- 会话详情 -->
    <el-drawer v-model="detailVisible" size="820px" destroy-on-close>
      <template #header>
        <div class="detail-head">
          <div>
            <div class="detail-title">{{ currentSession?.title || '面试会话' }}</div>
            <div class="detail-sub">
              <span v-if="currentSession?.company_name">{{ currentSession.company_name }}</span>
              <span v-if="currentSession?.job_title">{{ currentSession.job_title }}</span>
              <el-tag v-if="currentSession" :type="sourceMeta(currentSession.source).type" size="small" effect="plain">{{ sourceMeta(currentSession.source).label }}</el-tag>
            </div>
          </div>
          <div class="detail-actions">
            <el-button link type="primary" :icon="Edit" @click="openSessionMetaDialog">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="handleSessionDelete">删除</el-button>
          </div>
        </div>
      </template>

      <div v-loading="loadingDetail">
        <div class="kb-toolbar">
          <el-button type="primary" :icon="Plus" @click="openQuestionDialog()">添加问答</el-button>
          <el-button :icon="MagicStick" :loading="generatingReview" @click="handleGenerateReview">AI 复盘</el-button>
        </div>

        <div v-if="sessionReview" class="review-card">
          <div class="review-head">
            <span class="review-title"><el-icon><MagicStick /></el-icon>复盘结果</span>
            <el-tag v-if="sessionReview.model" size="small" effect="plain">{{ sessionReview.model }}</el-tag>
          </div>
          <p class="review-summary">{{ sessionReview.summary }}</p>
          <div v-if="sessionReview.focus_areas?.length" class="review-tags">
            <span class="review-label">考察方向</span>
            <el-tag v-for="a in sessionReview.focus_areas" :key="a" size="small" effect="plain">{{ a }}</el-tag>
          </div>
          <div v-if="sessionReview.weaknesses?.length" class="review-tags">
            <span class="review-label">薄弱项</span>
            <el-tag v-for="w in sessionReview.weaknesses" :key="w" size="small" type="warning" effect="plain">{{ w }}</el-tag>
          </div>
          <div v-if="sessionReview.knowledge_points?.length" class="kp-list">
            <span class="review-label">知识点</span>
            <div v-for="(p, i) in sessionReview.knowledge_points" :key="i" class="kp-item">
              <b>{{ p.topic }}</b>
              <span v-if="p.level">{{ p.level }}</span>
              <span v-if="p.note">{{ p.note }}</span>
            </div>
          </div>
          <p v-if="sessionReview.review_advice" class="review-advice">复习建议：{{ sessionReview.review_advice }}</p>
        </div>

        <el-empty v-if="!sessionQuestions.length" description="还没有问答记录" :image-size="70" />
        <div class="qa-list">
          <div v-for="q in sessionQuestions" :key="q.id" class="qa-item">
            <div class="qa-main">
              <div class="qa-question">{{ q.question }}</div>
              <div v-if="q.my_answer" class="qa-answer">{{ q.my_answer }}</div>
            </div>
            <div class="qa-meta">
              <el-tag size="small" :type="resultType(q.result)">{{ resultText(q.result) || '未标注' }}</el-tag>
              <el-tag v-if="q.category" size="small" type="info" effect="plain">{{ q.category }}</el-tag>
              <el-tag v-if="q.mastery" size="small" :type="masteryType(q.mastery)" effect="plain">{{ masteryText(q.mastery) }}</el-tag>
            </div>
            <div class="qa-actions">
              <el-button link type="primary" :icon="Edit" @click="openQuestionDialog(q)">编辑</el-button>
              <el-button link type="danger" :icon="Delete" @click="handleQuestionDelete(q)">删除</el-button>
            </div>
          </div>
        </div>

        <el-collapse v-if="currentSession?.raw_transcript" class="transcript-collapse">
          <el-collapse-item title="查看原始转写文本" name="raw">
            <p class="raw-transcript">{{ currentSession.raw_transcript }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>

    <!-- 会话元信息编辑 -->
    <el-dialog v-model="sessionMetaDialogVisible" title="编辑会话" width="480px">
      <el-form label-width="70px">
        <el-form-item label="标题"><el-input v-model="sessionMetaForm.title" /></el-form-item>
        <el-form-item label="公司"><el-input v-model="sessionMetaForm.company_name" /></el-form-item>
        <el-form-item label="岗位"><el-input v-model="sessionMetaForm.job_title" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sessionMetaDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="sessionMetaSaving" @click="handleSessionMetaSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 问答编辑 -->
    <el-dialog v-model="questionDialogVisible" :title="questionEditing ? '编辑问答' : '添加问答'" width="600px" append-to-body>
      <el-form label-width="80px">
        <el-form-item label="面试问题">
          <el-input v-model="questionForm.question" type="textarea" :rows="3" placeholder="面试官提问" />
        </el-form-item>
        <el-form-item label="我的回答">
          <el-input v-model="questionForm.my_answer" type="textarea" :rows="5" placeholder="你的回答" />
        </el-form-item>
        <el-form-item label="表现">
          <el-select v-model="questionForm.result" style="width: 200px">
            <el-option label="完整" value="完整" />
            <el-option label="部分" value="部分" />
            <el-option label="不会" value="不会" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="questionSaving" @click="handleQuestionSave">保存</el-button>
      </template>
    </el-dialog>

    <input ref="fileInput" type="file" accept="audio/*,video/*" class="hidden-input" @change="onFileChange" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown, Calendar, Collection, Delete, Edit, MagicStick, Microphone, Plus, Search, UploadFilled,
} from '@element-plus/icons-vue'
import {
  createInterview, createInterviewSession, createSessionQuestion, deleteInterview,
  deleteInterviewQuestion, deleteInterviewSession, deleteSessionQuestion, generateSessionReview,
  getApplications, getInterviewSession, getInterviewSessions, getInterviews, transcribeSession,
  updateInterview, updateInterviewSession, updateSessionQuestion,
} from '@/api'

const activeTab = ref('schedule')

// ===== 面试日程 =====
const interviews = ref([])
const appliedJobs = ref([])
const interviewDialogVisible = ref(false)
const interviewEditing = ref(false)
const interviewSaving = ref(false)

const emptyInterview = {
  id: null, application_id: null, company_id: null, job_id: null,
  interview_type: '视频面试', round_no: 1, scheduled_at: null,
  status: 'SCHEDULED', contact_person: '', contact_phone: '',
  address: '', meeting_url: '', notes: '', feedback: '',
}
const interviewForm = reactive({ ...emptyInterview })

// ===== 面试知识库 =====
const sessions = ref([])
const sessionsLoading = ref(false)
const searchKeyword = ref('')

const newDialogVisible = ref(false)
const newMode = ref('recording')
const newForm = reactive({ title: '', company_name: '', job_title: '' })
const submitting = ref(false)
const selectedFile = ref(null)

const recording = ref(false)
const recordingSeconds = ref(0)
let mediaRecorder = null
let recordingTimer = null
let audioChunks = []

const detailVisible = ref(false)
const currentSession = ref(null)
const sessionQuestions = ref([])
const sessionReview = ref(null)
const loadingDetail = ref(false)
const generatingReview = ref(false)

const sessionMetaDialogVisible = ref(false)
const sessionMetaSaving = ref(false)
const sessionMetaForm = reactive({ id: null, title: '', company_name: '', job_title: '' })

const questionDialogVisible = ref(false)
const questionEditing = ref(false)
const questionSaving = ref(false)
const questionForm = reactive({ id: null, question: '', my_answer: '', result: '完整' })

const fileInput = ref(null)

const filteredSessions = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return sessions.value
  return sessions.value.filter((s) =>
    [s.title, s.company_name, s.job_title].filter(Boolean).some((v) => v.toLowerCase().includes(kw)),
  )
})

// ===== 工具函数 =====
function fmtTime(v) {
  if (!v) return '-'
  return String(v).slice(0, 16).replace('T', ' ')
}
function normalizeIvStatus(s) {
  if (s === 'PENDING') return 'IN_PROGRESS'
  if (s === 'DONE') return 'COMPLETED'
  return s
}
const IV_TRANSITIONS = {
  SCHEDULED: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: ['REVIEWED'],
  REVIEWED: [],
  CANCELLED: [],
}
function ivText(s) {
  return { SCHEDULED: '已安排', IN_PROGRESS: '进行中', COMPLETED: '已完成', REVIEWED: '已复盘', CANCELLED: '已取消', PENDING: '进行中', DONE: '已完成' }[s] || s
}
function ivType(s) {
  return { SCHEDULED: 'primary', IN_PROGRESS: 'warning', COMPLETED: 'success', REVIEWED: 'info', CANCELLED: 'info', PENDING: 'warning', DONE: 'success' }[s] || 'info'
}
function nextRows(row) {
  return IV_TRANSITIONS[normalizeIvStatus(row.status)] || []
}
function resultText(r) {
  return { 完整: '完整', 部分: '部分', 不会: '不会' }[r] || r
}
function resultType(r) {
  return { 完整: 'success', 部分: 'warning', 不会: 'danger' }[r] || 'info'
}
function masteryText(m) {
  return { mastered: '已掌握', partial: '部分掌握', missed: '未掌握' }[m] || m
}
function masteryType(m) {
  return { mastered: 'success', partial: 'warning', missed: 'danger' }[m] || 'info'
}
function sourceMeta(s) {
  return { recording: { label: '录音', type: 'primary' }, upload: { label: '上传', type: 'success' }, manual: { label: '手动', type: 'info' } }[s] || { label: s, type: 'info' }
}
function formatSeconds(s) {
  const m = String(Math.floor(s / 60)).padStart(2, '0')
  const sec = String(s % 60).padStart(2, '0')
  return `${m}:${sec}`
}

// ===== 面试日程 CRUD =====
async function load() {
  interviews.value = await getInterviews()
  appliedJobs.value = await getApplications()
  await loadSessions()
}

function openInterviewDialog(row) {
  interviewEditing.value = !!row
  if (row) {
    Object.assign(interviewForm, emptyInterview, {
      id: row.id, application_id: row.application_id, company_id: row.company_id,
      job_id: row.job_id, interview_type: row.interview_type, round_no: row.round_no,
      scheduled_at: row.scheduled_at, status: normalizeIvStatus(row.status), contact_person: row.contact_person,
      contact_phone: row.contact_phone, address: row.address, meeting_url: row.meeting_url,
      notes: row.notes, feedback: row.feedback,
    })
  } else {
    Object.assign(interviewForm, emptyInterview)
  }
  interviewDialogVisible.value = true
}

async function handleInterviewSave() {
  interviewSaving.value = true
  try {
    const payload = { ...interviewForm }
    delete payload.id
    const app = appliedJobs.value.find((a) => a.job_id === interviewForm.job_id)
    if (app) {
      payload.application_id = app.id
      payload.company_id = app.company_id
    }
    if (interviewEditing.value) {
      await updateInterview(interviewForm.id, payload)
    } else {
      await createInterview(payload)
    }
    ElMessage.success('已保存')
    interviewDialogVisible.value = false
    await load()
  } finally {
    interviewSaving.value = false
  }
}

async function handleInterviewDelete(row) {
  await ElMessageBox.confirm('确定删除这条面试记录吗？', '提示', { type: 'warning' })
  await deleteInterview(row.id)
  ElMessage.success('已删除')
  await load()
}

async function advance(row, target) {
  await updateInterview(row.id, { status: target })
  ElMessage.success(`已推进为「${ivText(target)}」`)
  await load()
}

// ===== 面试知识库 =====
async function loadSessions() {
  sessionsLoading.value = true
  try {
    sessions.value = await getInterviewSessions()
  } finally {
    sessionsLoading.value = false
  }
}

function openNewSession() {
  Object.assign(newForm, { title: '', company_name: '', job_title: '' })
  newMode.value = 'recording'
  selectedFile.value = null
  newDialogVisible.value = true
}

function onNewDialogClosed() {
  cancelRecording()
  selectedFile.value = null
}

async function createManualSession() {
  if (!newForm.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  submitting.value = true
  try {
    const res = await createInterviewSession({
      title: newForm.title.trim(), company_name: newForm.company_name, job_title: newForm.job_title, source: 'manual',
    })
    newDialogVisible.value = false
    await loadSessions()
    await openSessionDetailById(res.id)
  } finally {
    submitting.value = false
  }
}

function triggerFilePick() {
  fileInput.value?.click()
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  selectedFile.value = file
  transcribeAndCreate(file, 'upload')
}

async function startRecording() {
  if (recording.value) return
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.error('当前环境不支持录音')
    return
  }
  let stream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    ElMessage.error('无法访问麦克风，请检查系统麦克风权限')
    return
  }
  const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
  mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
  audioChunks = []
  mediaRecorder.ondataavailable = (ev) => {
    if (ev.data && ev.data.size) audioChunks.push(ev.data)
  }
  mediaRecorder.onstop = async () => {
    stream.getTracks().forEach((t) => t.stop())
    clearInterval(recordingTimer)
    recording.value = false
    recordingSeconds.value = 0
    if (!audioChunks.length) return
    const type = mediaRecorder.mimeType || 'audio/webm'
    const ext = type.includes('mp4') ? 'm4a' : 'webm'
    const blob = new Blob(audioChunks, { type })
    const file = new File([blob], `recording.${ext}`, { type })
    await transcribeAndCreate(file, 'recording')
  }
  recording.value = true
  recordingSeconds.value = 0
  recordingTimer = setInterval(() => { recordingSeconds.value += 1 }, 1000)
  mediaRecorder.start()
}

function stopAndTranscribe() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
}

function cancelRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.onstop = null
    mediaRecorder.stop()
  }
  clearInterval(recordingTimer)
  recording.value = false
  recordingSeconds.value = 0
}

async function transcribeAndCreate(file, source) {
  submitting.value = true
  try {
    const res = await transcribeSession(file, {
      title: newForm.title, company_name: newForm.company_name, job_title: newForm.job_title, source,
    })
    newDialogVisible.value = false
    await loadSessions()
    await openSessionDetailById(res.session.id)
    ElMessage.success('转写完成，已生成面试会话')
  } finally {
    submitting.value = false
  }
}

async function openSessionDetailById(id) {
  detailVisible.value = true
  loadingDetail.value = true
  try {
    const detail = await getInterviewSession(id)
    currentSession.value = detail
    sessionQuestions.value = detail.questions || []
    sessionReview.value = detail.review || null
  } finally {
    loadingDetail.value = false
  }
}

function openSessionMetaDialog() {
  Object.assign(sessionMetaForm, {
    id: currentSession.value?.id, title: currentSession.value?.title || '',
    company_name: currentSession.value?.company_name || '', job_title: currentSession.value?.job_title || '',
  })
  sessionMetaDialogVisible.value = true
}

async function handleSessionMetaSave() {
  if (!sessionMetaForm.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  sessionMetaSaving.value = true
  try {
    await updateInterviewSession(sessionMetaForm.id, {
      title: sessionMetaForm.title, company_name: sessionMetaForm.company_name, job_title: sessionMetaForm.job_title,
    })
    ElMessage.success('已保存')
    sessionMetaDialogVisible.value = false
    await openSessionDetailById(sessionMetaForm.id)
    await loadSessions()
  } finally {
    sessionMetaSaving.value = false
  }
}

async function handleSessionDelete() {
  await ElMessageBox.confirm('确定删除这个面试会话及其全部问答吗？', '提示', { type: 'warning' })
  await deleteInterviewSession(currentSession.value.id)
  ElMessage.success('已删除')
  detailVisible.value = false
  await loadSessions()
}

function openQuestionDialog(item) {
  questionEditing.value = !!item
  if (item) {
    Object.assign(questionForm, { id: item.id, question: item.question, my_answer: item.my_answer || '', result: item.result || '完整' })
  } else {
    Object.assign(questionForm, { id: null, question: '', my_answer: '', result: '完整' })
  }
  questionDialogVisible.value = true
}

async function handleQuestionSave() {
  if (!questionForm.question.trim()) {
    ElMessage.warning('请填写面试问题')
    return
  }
  questionSaving.value = true
  try {
    const payload = { question: questionForm.question.trim(), my_answer: questionForm.my_answer, result: questionForm.result }
    if (questionEditing.value) {
      await updateSessionQuestion(currentSession.value.id, questionForm.id, payload)
    } else {
      await createSessionQuestion(currentSession.value.id, payload)
    }
    ElMessage.success('已保存')
    questionDialogVisible.value = false
    await openSessionDetailById(currentSession.value.id)
  } finally {
    questionSaving.value = false
  }
}

async function handleQuestionDelete(item) {
  await ElMessageBox.confirm('确定删除这条问答记录吗？', '提示', { type: 'warning' })
  await deleteSessionQuestion(currentSession.value.id, item.id)
  ElMessage.success('已删除')
  await openSessionDetailById(currentSession.value.id)
}

async function handleGenerateReview() {
  generatingReview.value = true
  try {
    sessionReview.value = await generateSessionReview(currentSession.value.id)
    ElMessage.success('复盘完成')
    await openSessionDetailById(currentSession.value.id)
  } finally {
    generatingReview.value = false
  }
}

onBeforeUnmount(() => {
  cancelRecording()
})

onMounted(load)
</script>

<style scoped>
.iv-tabs :deep(.el-tabs__header) { margin-bottom: 16px; }

.panel {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 16px 20px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: var(--jf-ink);
}
.panel-actions { display: flex; align-items: center; gap: 10px; }

.job-title { font-weight: 600; color: var(--jf-ink); }
.company { color: var(--jf-muted); font-size: 12px; margin-top: 2px; }
.round { margin-left: 6px; color: var(--jf-ink-soft); font-size: 13px; }
.text-muted { color: var(--jf-muted); font-size: 12px; }

.kb-hint { color: var(--jf-muted); font-size: 13px; margin: 0 0 14px; }

.session-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  min-height: 80px;
}
.session-card {
  border: 1px solid var(--jf-border);
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  background: var(--jf-surface);
  transition: all 0.16s ease;
}
.session-card:hover {
  border-color: var(--jf-primary);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}
.session-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.session-title { font-weight: 600; color: var(--jf-ink); line-height: 1.4; }
.session-sub { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; color: var(--jf-ink-soft); font-size: 13px; }
.session-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
.qa-count { font-size: 12px; color: var(--jf-primary-darker); font-weight: 600; }

.new-mode-body { min-height: 120px; margin: 4px 0 8px; }
.record-zone, .upload-zone, .manual-hint {
  border: 1px dashed var(--jf-border);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  color: var(--jf-ink-soft);
  font-size: 13px;
}
.record-status { display: flex; align-items: center; justify-content: center; gap: 8px; }
.upload-zone { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.upload-zone p { margin: 0; color: var(--jf-muted); }
.selected-file { color: var(--jf-primary-darker) !important; font-weight: 600; }
.rec-dot { width: 8px; height: 8px; border-radius: 50%; background: #ef4444; animation: pulse 1s infinite; }
.hidden-input { display: none; }

.detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; width: 100%; }
.detail-title { font-weight: 700; color: var(--jf-ink); font-size: 16px; }
.detail-sub { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 4px; color: var(--jf-muted); font-size: 13px; }
.detail-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.kb-toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.qa-list { display: flex; flex-direction: column; gap: 10px; }
.qa-item {
  border: 1px solid var(--jf-border);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.qa-main { flex: 1; min-width: 0; }
.qa-question { font-weight: 600; color: var(--jf-ink); line-height: 1.6; }
.qa-answer { color: var(--jf-ink-soft); font-size: 13px; line-height: 1.7; margin-top: 6px; white-space: pre-wrap; }
.qa-meta { display: flex; flex-direction: column; gap: 4px; align-items: flex-end; flex-shrink: 0; }
.qa-actions { display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }

.review-card {
  border: 1px solid var(--jf-border);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
  background: var(--jf-primary-softer, #f0faf9);
}
.review-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.review-title { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; color: var(--jf-ink); }
.review-summary { color: var(--jf-ink-soft); line-height: 1.8; font-size: 13px; margin: 0 0 10px; }
.review-tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 8px 0; }
.review-label { font-size: 12px; color: var(--jf-muted); margin-right: 2px; }
.kp-list { margin: 8px 0; }
.kp-item { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 6px 0; font-size: 13px; color: var(--jf-ink-soft); border-bottom: 1px dashed var(--jf-border); }
.kp-item b { color: var(--jf-ink); }
.review-advice { color: var(--jf-ink-soft); line-height: 1.8; font-size: 13px; margin: 10px 0 0; }

.transcript-collapse { margin-top: 16px; }
.raw-transcript { white-space: pre-wrap; color: var(--jf-ink-soft); font-size: 13px; line-height: 1.7; margin: 0; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
</style>
