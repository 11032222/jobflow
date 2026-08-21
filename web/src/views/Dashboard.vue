<template>
  <div>
    <div class="stat-grid">
      <div class="stat-card hoverable" v-for="s in statCards" :key="s.label">
        <span class="icon-chip" :style="{ background: s.soft, color: s.color }"><el-icon :size="20"><component :is="s.icon" /></el-icon></span>
        <div class="stat-body">
          <div class="stat-value" :style="{ color: s.color }">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="dash-grid">
      <section class="panel">
        <header class="panel-header">
          <span class="panel-title"><el-icon><TrendCharts /></el-icon>智能推荐</span>
          <el-link type="primary" :underline="false" @click="$router.push('/recommendations')">查看全部<el-icon class="link-icon"><Right /></el-icon></el-link>
        </header>
        <div v-if="recommendations.length" class="rec-list">
          <div v-for="item in recommendations" :key="item.id" class="rec-row hoverable" @click="goDetail(item)">
            <div class="rec-main">
              <div class="rec-title">{{ item.title }}</div>
              <div class="rec-meta">
                <span>{{ item.company_name }}</span>
                <span class="dot">·</span>
                <span>{{ item.city }}</span>
                <span class="dot">·</span>
                <span class="salary-text">{{ item.salary_text }}</span>
              </div>
            </div>
            <div class="rec-match">
              <span v-if="item.match" class="score-badge" :class="levelClass(item.match.recommend_level)">
                {{ item.match.match_score }}<small>分</small>
              </span>
              <el-tag v-if="item.match" :type="levelType(item.match.recommend_level)" size="small" effect="plain">
                {{ item.match.recommend_level }}
              </el-tag>
              <el-button v-else link type="primary" size="small">查看</el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无推荐，请先完善简历画像" :image-size="80" />
      </section>

      <div class="right-col">
        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><Message /></el-icon>最近投递</span>
            <el-link type="primary" :underline="false" @click="$router.push('/applications')">投递看板</el-link>
          </header>
          <el-timeline v-if="applications.length">
            <el-timeline-item
              v-for="app in applications.slice(0, 6)"
              :key="app.id"
              :timestamp="formatTime(app.updated_at)"
              :color="statusColor(app.status)"
            >
              <div class="timeline-body">
                <b class="tl-title">{{ app.job_title }}</b>
                <span class="text-muted tl-company">{{ app.company_name }}</span>
                <el-tag size="small" :type="statusTagType(app.status)" effect="plain">{{ statusText(app.status) }}</el-tag>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无投递记录" :image-size="70" />
        </section>

        <section class="panel">
          <header class="panel-header">
            <span class="panel-title"><el-icon><User /></el-icon>我的画像</span>
            <el-link type="primary" :underline="false" @click="$router.push('/resumes')">管理</el-link>
          </header>
          <template v-if="profile">
            <div class="profile-line">
              <b>{{ profile.name }}</b>
              <el-tag v-if="profile.title" size="small" effect="plain" class="profile-tag">{{ profile.title }}</el-tag>
            </div>
            <div class="profile-meta">
              <span v-if="profile.education_level">{{ profile.education_level }}</span>
              <span v-if="profile.school">{{ profile.school }}</span>
              <span v-if="profile.city">{{ profile.city }}</span>
              <span v-if="profile.years_of_experience != null">{{ profile.years_of_experience }} 年经验</span>
            </div>
            <el-progress :percentage="profileProgress" :stroke-width="10" class="profile-progress" />
            <div class="progress-caption">画像完整度 {{ profileProgress }}%</div>
          </template>
          <el-empty v-else description="尚未建立求职画像" :image-size="70">
            <el-button type="primary" size="small" @click="$router.push('/resumes')">去完善</el-button>
          </el-empty>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Briefcase, Calendar, Message, Promotion, Right, TrendCharts, Trophy, User } from '@element-plus/icons-vue'
import { getApplications, getCurrentProfile, getJobs, getRecommendations } from '@/api'

const recommendations = ref([])
const applications = ref([])
const profile = ref(null)
const jobTotal = ref(0)

const stats = computed(() => {
  const applying = applications.value.filter((a) => ['PENDING', 'SUBMITTING', 'SUBMITTED', 'WAITING', 'FAILED'].includes(a.status)).length
  const interviewing = applications.value.filter((a) => ['TEST', 'INTERVIEW'].includes(a.status)).length
  const offers = applications.value.filter((a) => a.status === 'OFFER').length
  return { jobTotal: jobTotal.value, applying, interviewing, offers }
})

const statCards = computed(() => [
  { label: '岗位总数', value: stats.value.jobTotal, icon: Briefcase, color: '#0d9488', soft: '#ccfbf1' },
  { label: '投递中', value: stats.value.applying, icon: Promotion, color: '#ea580c', soft: '#ffedd5' },
  { label: '面试中', value: stats.value.interviewing, icon: Calendar, color: '#d97706', soft: '#fef3c7' },
  { label: '拿到 Offer', value: stats.value.offers, icon: Trophy, color: '#16a34a', soft: '#dcfce7' },
])

const profileProgress = computed(() => {
  if (!profile.value) return 0
  const fields = ['name', 'title', 'phone', 'email', 'city', 'education_level', 'school', 'major', 'summary']
  const filled = fields.filter((f) => profile.value[f]).length
  return Math.round((filled / fields.length) * 100)
})

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : ''
}
function statusText(s) {
  return { PENDING: '待投递', SUBMITTING: '投递中', SUBMITTED: '已投递', FAILED: '投递失败', WAITING: '待反馈', TEST: '笔试', INTERVIEW: '面试', OFFER: 'Offer', REJECTED: '未通过', CLOSED: '已关闭' }[s] || s
}
function statusTagType(s) {
  return { INTERVIEW: 'warning', TEST: 'warning', OFFER: 'success', REJECTED: 'danger', CLOSED: 'info', SUBMITTED: 'success', WAITING: 'primary', FAILED: 'danger' }[s] || 'info'
}
function statusColor(s) {
  return { INTERVIEW: '#d97706', TEST: '#d97706', OFFER: '#16a34a', REJECTED: '#dc2626', SUBMITTED: '#16a34a' }[s] || '#94a3b8'
}
function levelType(level) {
  return { S: 'danger', A: 'warning', B: 'primary', C: 'info', D: 'info' }[level] || 'info'
}
function levelClass(level) {
  return { S: 'level-s', A: 'level-a', B: 'level-b', C: 'level-c', D: 'level-d' }[level] || 'level-d'
}

function goDetail(row) {
  window.location.hash = `#/jobs/${row.id}`
}

onMounted(async () => {
  try {
    const [jobRes, appRes] = await Promise.all([getJobs({ page: 1, page_size: 1 }), getApplications()])
    jobTotal.value = jobRes.total
    applications.value = appRes
  } catch { /* 忽略 */ }
  try {
    recommendations.value = (await getRecommendations({ limit: 5 })).items
  } catch { /* 忽略 */ }
  try {
    profile.value = await getCurrentProfile()
  } catch { /* 忽略 */ }
})
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.stat-card {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-value { font-size: 28px; font-weight: 800; line-height: 1.1; }
.stat-label { font-size: 13px; color: var(--jf-ink-soft); margin-top: 4px; }

.dash-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(300px, 1fr);
  gap: 16px;
  margin-top: 16px;
}
@media (max-width: 1100px) {
  .dash-grid { grid-template-columns: 1fr; }
}
.panel {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 16px 20px;
}
.right-col { display: flex; flex-direction: column; gap: 16px; }
.link-icon { margin-left: 2px; }

.rec-list { margin-top: 8px; }
.rec-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 10px;
  border-radius: 10px;
  border-bottom: 1px solid var(--jf-border-lighter, #eef8f5);
}
.rec-row:last-child { border-bottom: none; }
.rec-main { flex: 1; min-width: 0; }
.rec-title { font-size: 14px; font-weight: 600; color: var(--jf-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rec-meta { display: flex; align-items: center; gap: 6px; color: var(--jf-ink-soft); font-size: 12px; margin-top: 4px; flex-wrap: wrap; }
.dot { color: var(--jf-border-strong); }
.rec-match { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.score-badge {
  min-width: 46px;
  text-align: center;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 800;
  color: #fff;
}
.score-badge small { font-size: 10px; font-weight: 600; }
.level-s { background: #dc2626; }
.level-a { background: #ea580c; }
.level-b { background: #0d9488; }
.level-c { background: #94a3b8; }
.level-d { background: #cbd5e1; }

.timeline-body { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tl-title { font-size: 13px; }
.tl-company { font-size: 12px; }

.profile-line { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.profile-tag { margin-left: 0; }
.profile-meta { color: var(--jf-ink-soft); font-size: 12px; margin-top: 8px; display: flex; gap: 12px; flex-wrap: wrap; }
.profile-progress { margin-top: 14px; }
.progress-caption { margin-top: 6px; color: var(--jf-muted); font-size: 12px; }
</style>