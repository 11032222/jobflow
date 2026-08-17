<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #409eff">{{ stats.jobTotal }}</div>
          <div class="stat-label">岗位总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #e6a23c">{{ stats.applying }}</div>
          <div class="stat-label">投递中</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #67c23a">{{ stats.interviewing }}</div>
          <div class="stat-label">面试中</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #f56c6c">{{ stats.offers }}</div>
          <div class="stat-label">拿到 Offer</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🔥 智能推荐</span>
              <el-link type="primary" @click="$router.push('/recommendations')">查看全部</el-link>
            </div>
          </template>
          <el-table :data="recommendations" size="small" @row-click="goDetail">
            <el-table-column prop="title" label="职位" min-width="170" show-overflow-tooltip />
            <el-table-column label="公司" min-width="100" show-overflow-tooltip>
              <template #default="{ row }">{{ row.company_name }}</template>
            </el-table-column>
            <el-table-column label="城市" width="70">
              <template #default="{ row }">{{ row.city }}</template>
            </el-table-column>
            <el-table-column label="薪资" width="100">
              <template #default="{ row }">{{ row.salary_text }}</template>
            </el-table-column>
            <el-table-column label="匹配" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.match" :type="levelType(row.match.recommend_level)" size="small">
                  {{ row.match.match_score }}分 {{ row.match.recommend_level }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!recommendations.length" description="暂无推荐，请先完善简历画像" :image-size="80" />
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📬 最近投递</span>
              <el-link type="primary" @click="$router.push('/applications')">投递看板</el-link>
            </div>
          </template>
          <el-timeline v-if="applications.length">
            <el-timeline-item
              v-for="app in applications.slice(0, 6)"
              :key="app.id"
              :timestamp="formatTime(app.updated_at)"
              :color="statusColor(app.status)"
            >
              <div class="timeline-body">
                <b>{{ app.job_title }}</b>
                <span class="timeline-company">{{ app.company_name }}</span>
                <el-tag size="small" :type="statusTagType(app.status)">{{ statusText(app.status) }}</el-tag>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无投递记录" :image-size="80" />
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>👤 我的画像</span>
              <el-link type="primary" @click="$router.push('/resumes')">管理</el-link>
            </div>
          </template>
          <template v-if="profile">
            <div class="profile-line">
              <b>{{ profile.name }}</b>
              <el-tag size="small" style="margin-left: 8px">{{ profile.title }}</el-tag>
            </div>
            <div class="profile-meta">
              <span>{{ profile.education_level }} · {{ profile.school }} · {{ profile.major }}</span>
              <span>{{ profile.city }} · {{ profile.years_of_experience || 0 }}年经验</span>
            </div>
            <el-progress :percentage="profileProgress" :stroke-width="10" style="margin-top: 8px" />
            <div style="margin-top: 4px; color: #909399; font-size: 12px">画像完整度 {{ profileProgress }}%</div>
          </template>
          <el-empty v-else description="尚未建立求职画像" :image-size="80">
            <el-button type="primary" size="small" @click="$router.push('/resumes')">去完善</el-button>
          </el-empty>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
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
  return { INTERVIEW: 'warning', TEST: 'warning', OFFER: 'success', REJECTED: 'danger', CLOSED: 'info', SUBMITTED: 'success', WAITING: 'primary' }[s] || 'info'
}
function statusColor(s) {
  return { INTERVIEW: '#e6a23c', TEST: '#e6a23c', OFFER: '#67c23a', REJECTED: '#f56c6c', SUBMITTED: '#67c23a' }[s] || '#c0c4cc'
}
function levelType(level) {
  return { S: 'danger', A: 'warning', B: 'primary', C: 'info', D: 'info' }[level] || 'info'
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
    recommendations.value = (await getRecommendations({ limit: 6 })).items
  } catch { /* 忽略 */ }
  try {
    profile.value = await getCurrentProfile()
  } catch { /* 忽略 */ }
})
</script>

<style scoped>
.stat-card {
  text-align: center;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
}
.stat-label {
  color: #909399;
  margin-top: 4px;
  font-size: 14px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.timeline-body {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.timeline-company {
  color: #909399;
  font-size: 13px;
}
.profile-line {
  font-size: 16px;
}
.profile-meta {
  color: #606266;
  font-size: 13px;
  margin-top: 6px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>

