<template>
  <div v-if="job" class="detail-page">
    <div class="back-bar">
      <el-button text :icon="ArrowLeft" @click="$router.back()">返回</el-button>
    </div>

    <div class="detail-grid">
      <!-- 左：岗位信息 -->
      <div class="main-col">
        <section class="panel job-card">
          <div class="job-head">
            <div class="job-title-block">
              <h2 class="job-title">{{ job.title }}</h2>
              <div class="job-sub">
                <el-tag size="small" effect="plain">{{ job.job_type || '全职' }}</el-tag>
                <el-tag v-if="job.status && job.status !== 'ACTIVE'" size="small" type="info" effect="plain">{{ statusText(job.status) }}</el-tag>
                <span class="company">{{ job.company_name }}</span>
                <span class="dot">·</span>
                <span>{{ job.city }}{{ job.district ? '·' + job.district : '' }}</span>
              </div>
            </div>
            <div class="salary-text job-salary">{{ job.salary_text }}</div>
          </div>

          <div class="meta-grid">
            <div class="meta-item"><span class="meta-label">学历要求</span><b>{{ job.education || '不限' }}</b></div>
            <div class="meta-item"><span class="meta-label">经验要求</span><b>{{ job.experience || '不限' }}</b></div>
            <div class="meta-item"><span class="meta-label">发布时间</span><b>{{ (job.publish_time || '').slice(0, 10) || '-' }}</b></div>
          </div>

          <div class="tag-row">
            <el-tag v-for="t in displayTags" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
          </div>

          <el-divider content-position="left">职位描述</el-divider>
          <pre class="desc-pre">{{ job.description || '暂无职位描述' }}</pre>

          <el-divider content-position="left">岗位职责</el-divider>
          <pre class="desc-pre">{{ job.responsibilities || '暂无' }}</pre>

          <el-divider content-position="left">任职要求</el-divider>
          <pre class="desc-pre">{{ job.requirements || '暂无' }}</pre>
        </section>
      </div>

      <!-- 右：操作 / 匹配 / 公司 -->
      <div class="side-col">
        <section class="panel action-card">
          <div class="action-btns">
            <el-button v-if="job.is_applied" disabled type="primary" size="large" class="apply-btn">已投递该岗位</el-button>
            <el-button v-else type="primary" size="large" class="apply-btn" :icon="Promotion" @click="handleApply">
              投递该岗位
            </el-button>
            <el-button :icon="Star" size="large" :type="job.is_favorite ? 'warning' : 'default'" @click="toggleFavorite">
              {{ job.is_favorite ? '已收藏' : '收藏' }}
            </el-button>
            <el-button v-if="job.source_url" size="large" :icon="Link" @click="openSource">查看原岗位</el-button>
          </div>
          <el-alert
            v-if="job.is_applied"
            type="success"
            :closable="false"
            show-icon
            title="该岗位已创建投递记录，可前往「投递看板」查看状态和邮件发送情况。"
          />
        </section>

        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><DataAnalysis /></el-icon>匹配分析</span>
            <el-button v-if="!job.match" type="primary" size="small" :loading="matching" @click="handleMatch">开始分析</el-button>
          </header>
          <template v-if="job.match">
            <el-alert
              v-if="job.match.hard_fail"
              type="error"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
              :title="(job.match.hard_fail_reasons || []).join('；') || '存在硬性要求不满足'"
            />
            <div class="match-head">
              <el-progress type="circle" :percentage="Number(job.match.match_score || 0)" :width="104" :stroke-width="9" :color="scoreColor(job.match.match_score)">
                <template #default>
                  <div class="match-score">{{ Math.round(Number(job.match.match_score || 0)) }}</div>
                  <div class="match-level">推荐等级 {{ job.match.recommend_level }}</div>
                </template>
              </el-progress>
              <div class="match-reason">
                <p class="reason-label">推荐理由</p>
                <p>{{ job.match.recommend_reason }}</p>
              </div>
            </div>
            <div class="dims">
              <div class="dim-row">
                <span class="dim-label">技能匹配</span>
                <el-progress :percentage="Number(job.match.skill_score || 0)" :stroke-width="8" color="#0d9488" />
              </div>
              <div class="dim-row">
                <span class="dim-label">经历匹配</span>
                <el-progress :percentage="Number(job.match.experience_score || 0)" :stroke-width="8" color="#16a34a" />
              </div>
              <div class="dim-row">
                <span class="dim-label">学历匹配</span>
                <el-progress :percentage="Number(job.match.education_score || 0)" :stroke-width="8" color="#d97706" />
              </div>
              <div class="dim-row">
                <span class="dim-label">偏好匹配</span>
                <el-progress :percentage="Number(job.match.preference_score || 0)" :stroke-width="8" color="#dc2626" />
              </div>
            </div>
            <el-tag type="info" effect="plain" size="small" class="engine-tag">
              分析引擎：{{ job.match.model_used === 'llm' ? 'LLM Agent' : '规则引擎' }}
            </el-tag>
          </template>
          <el-empty v-else description="点击「开始分析」查看匹配结果" :image-size="70" />
        </section>

        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><OfficeBuilding /></el-icon>公司信息</span>
            <el-button type="primary" link size="small" :loading="researching" @click="handleResearch">联网补充</el-button>
          </header>
          <div class="company-head">
            <el-avatar :size="44" shape="square" class="company-avatar">{{ job.company_name?.[0] }}</el-avatar>
            <div>
              <div class="company-name">{{ job.company_name }}</div>
              <div class="company-meta">{{ company.industry || job.industry || '-' }} · {{ company.company_type || '-' }}</div>
            </div>
          </div>
          <div class="company-rows">
            <div class="company-row"><span>公司规模</span><b>{{ company.scale || '-' }}</b></div>
            <div class="company-row"><span>所在城市</span><b>{{ company.address || job.city || '-' }}</b></div>
            <div class="company-row" v-if="company.website">
              <span>公司官网</span>
              <a :href="company.website" target="_blank" rel="noreferrer">{{ hostOf(company.website) }}</a>
            </div>
            <div class="company-row">
              <span>资料状态</span>
              <el-tag :type="company.profile_status === 'ANALYZED' ? 'success' : 'info'" size="small" effect="plain">
                {{ company.profile_status === 'ANALYZED' ? '已联网补充' : '待补充' }}
              </el-tag>
            </div>
          </div>
          <p class="desc-text company-desc">{{ company.description || '暂无公司介绍，可点击「联网补充」检索公开信息。' }}</p>
        </section>
      </div>
    </div>

    <!-- 投递确认弹窗 -->
    <el-dialog v-model="applyDialogVisible" title="确认投递" width="520px">
      <el-alert type="warning" :closable="false" show-icon title="演示模式：投递邮件将发送至你的演示收件箱，不会打扰真实 HR。" style="margin-bottom: 12px" />
      <el-form label-width="80px">
        <el-form-item label="岗位">
          <b>{{ job.title }}</b>（{{ job.company_name }}）
        </el-form-item>
        <el-form-item label="选择简历">
          <el-select v-model="applyResumeId" placeholder="选择要投递的简历" style="width: 100%">
            <el-option v-for="r in resumes" :key="r.id" :label="r.file_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="applyNote" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="applying" @click="confirmApply">确认投递</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, DataAnalysis, Link, OfficeBuilding, Promotion, Star } from '@element-plus/icons-vue'
import {
  addFavorite, createApplication, getCompany, getJob, getResumes, matchJob, removeFavorite, researchCompany, submitApplication,
} from '@/api'

const route = useRoute()
const job = ref(null)
const company = ref({})
const resumes = ref([])
const matching = ref(false)
const researching = ref(false)
const applying = ref(false)
const displayTags = computed(() => {
  const tags = job.value?.tags || []
  const skip = new Set([job.value?.education, job.value?.experience, job.value?.job_type].filter(Boolean))
  return tags.filter((t) => t && !skip.has(t))
})
const applyDialogVisible = ref(false)
const applyResumeId = ref(null)
const applyNote = ref('')

async function load() {
  job.value = await getJob(route.params.id)
  if (job.value.company_id) {
    try {
      company.value = await getCompany(job.value.company_id)
    } catch { /* 忽略 */ }
  }
}

function riskType(level) {
  return { NORMAL: 'success', WARNING: 'warning', HIGH: 'danger' }[level] || 'info'
}
function riskText(level) {
  return { NORMAL: '正常', WARNING: '谨慎', HIGH: '高风险' }[level] || level
}
function scoreColor(score) {
  if (score >= 80) return '#16a34a'
  if (score >= 60) return '#0d9488'
  if (score >= 40) return '#d97706'
  return '#dc2626'
}
function statusText(status) {
  return { ACTIVE: '招聘中', CLOSED: '已关闭', EXPIRED: '已过期', OFFLINE: '已下线' }[status] || status
}
function hostOf(url) {
  try {
    return new URL(url).host
  } catch {
    return url
  }
}

async function handleResearch() {
  if (!job.value?.company_id) {
    ElMessage.warning('没有关联公司')
    return
  }
  researching.value = true
  try {
    company.value = await researchCompany(job.value.company_id)
    ElMessage.success('已补充公司公开信息')
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '检索失败')
  } finally {
    researching.value = false
  }
}

async function toggleFavorite() {
  if (job.value.is_favorite) {
    await removeFavorite(job.value.id)
    ElMessage.success('已取消收藏')
  } else {
    await addFavorite(job.value.id)
    ElMessage.success('收藏成功')
  }
  await load()
}

async function handleMatch() {
  matching.value = true
  try {
    await matchJob(job.value.id)
    ElMessage.success('匹配分析完成')
    await load()
  } finally {
    matching.value = false
  }
}

async function handleApply() {
  resumes.value = await getResumes()
  if (!resumes.value.length) {
    ElMessage.warning('请先在「简历管理」上传简历')
    return
  }
  applyResumeId.value = resumes.value[0].id
  applyDialogVisible.value = true
}

async function confirmApply() {
  if (!applyResumeId.value) {
    ElMessage.warning('请选择要投递的简历')
    return
  }
  applying.value = true
  try {
    const app = await createApplication({
      job_id: job.value.id,
      resume_id: applyResumeId.value,
      note: applyNote.value || '通过 JobFlow 投递',
    })
    // 触发邮件投递（后台执行）
    await submitApplication(app.id)
    applyDialogVisible.value = false
    ElMessage.success('已创建投递并触发邮件发送，可前往「投递看板」查看')
    await load()
  } finally {
    applying.value = false
  }
}

function openSource() {
  if (job.value.source_url) window.open(job.value.source_url, '_blank')
}

onMounted(load)
</script>

<style scoped>
.back-bar { margin-bottom: 12px; }
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}
@media (max-width: 1100px) {
  .detail-grid { grid-template-columns: 1fr; }
}
.panel {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 18px 20px;
}
.main-col, .side-col { display: flex; flex-direction: column; gap: 16px; }

.job-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.job-title { font-size: 22px; font-weight: 800; color: var(--jf-ink); line-height: 1.3; }
.job-sub { display: flex; gap: 8px; align-items: center; color: var(--jf-ink-soft); margin-top: 10px; font-size: 14px; flex-wrap: wrap; }
.job-sub .company { font-weight: 600; color: var(--jf-ink); }
.dot { color: var(--jf-border-strong); }
.job-salary { font-size: 24px; white-space: nowrap; }

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 18px;
}
.meta-item {
  background: var(--jf-primary-softer);
  border: 1px solid var(--jf-border);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.meta-label { font-size: 12px; color: var(--jf-muted); }
.meta-item b { font-size: 14px; color: var(--jf-ink); }

.tag-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 14px; }
.desc-text { color: #334155; line-height: 1.8; font-size: 14px; }
.desc-pre {
  white-space: pre-wrap;
  word-break: break-word;
  color: #334155;
  line-height: 1.85;
  font-size: 14px;
  font-family: inherit;
  margin: 0;
  background: var(--jf-primary-softer);
  border: 1px solid var(--jf-border);
  border-radius: 10px;
  padding: 12px 14px;
}

.action-btns { display: flex; flex-direction: column; gap: 10px; }
.action-btns .apply-btn { width: 100%; margin-left: 0; }
.action-btns .el-button:not(.apply-btn) { margin-left: 0; }

.match-head { display: flex; gap: 16px; align-items: center; }
.match-score { font-size: 20px; font-weight: 800; color: var(--jf-ink); }
.match-level { font-size: 11px; color: var(--jf-muted); }
.match-reason { flex: 1; min-width: 0; }
.reason-label { font-weight: 600; color: var(--jf-ink); margin-bottom: 4px; font-size: 13px; }
.match-reason p:last-child { color: var(--jf-ink-soft); font-size: 13px; line-height: 1.7; }
.dims { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.dim-row { display: grid; grid-template-columns: 64px 1fr; align-items: center; gap: 10px; }
.dim-label { font-size: 12px; color: var(--jf-ink-soft); }
.engine-tag { margin-top: 12px; }

.company-avatar { background: var(--jf-primary-softer); color: var(--jf-primary-dark); font-weight: 700; }
.company-head { display: flex; gap: 12px; align-items: center; }
.company-name { font-size: 16px; font-weight: 700; color: var(--jf-ink); }
.company-meta { font-size: 12px; color: var(--jf-muted); margin-top: 2px; }
.company-rows { margin-top: 12px; border-top: 1px solid var(--jf-border); }
.company-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--jf-border);
  font-size: 13px;
}
.company-row span { color: var(--jf-muted); }
.company-desc { margin-top: 10px; }
</style>