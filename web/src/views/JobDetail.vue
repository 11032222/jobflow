<template>
  <div v-if="job">
    <el-page-header content="岗位详情" @back="$router.back()" style="margin-bottom: 16px" />

    <el-row :gutter="16">
      <el-col :span="15">
        <el-card>
          <div class="job-head">
            <div>
              <h2>{{ job.title }}</h2>
              <div class="job-sub">
                <el-tag size="small" effect="plain">{{ job.job_type }}</el-tag>
                <span>{{ job.company_name }}</span>
                <span>·</span>
                <span>{{ job.city }}{{ job.district ? '·' + job.district : '' }}</span>
              </div>
            </div>
            <div class="salary">{{ job.salary_text }}</div>
          </div>

          <el-descriptions :column="3" border size="small" style="margin-top: 16px">
            <el-descriptions-item label="学历要求">{{ job.education }}</el-descriptions-item>
            <el-descriptions-item label="经验要求">{{ job.experience }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ (job.publish_time || '').slice(0, 10) }}</el-descriptions-item>
            <el-descriptions-item label="岗位标签" :span="3">
              <el-tag v-for="t in job.tags" :key="t" size="small" type="info" effect="plain" style="margin: 2px">{{ t }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">岗位职责</el-divider>
          <p class="desc-text">{{ job.responsibilities }}</p>

          <el-divider content-position="left">任职要求</el-divider>
          <p class="desc-text">{{ job.requirements }}</p>

          <div class="job-actions" style="margin-top: 16px">
            <el-button v-if="job.is_applied" disabled type="primary" size="large">已投递该岗位</el-button>
            <el-button v-else type="primary" size="large" @click="handleApply">
              📮 投递该岗位（发送简历邮件）
            </el-button>
            <el-button v-if="!job.is_favorite" size="large" @click="toggleFavorite">☆ 收藏</el-button>
            <el-button v-else size="large" @click="toggleFavorite">★ 已收藏</el-button>
            <el-button v-if="job.source_url" size="large" @click="openSource">查看原岗位</el-button>
          </div>
          <el-alert
            v-if="job.is_applied"
            type="success"
            :closable="false"
            show-icon
            title="该岗位已创建投递记录，可前往「投递看板」查看状态和邮件发送情况。"
            style="margin-top: 12px"
          />
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>🧠 匹配分析</span>
              <el-button v-if="!job.match" type="primary" size="small" :loading="matching" @click="handleMatch">开始分析</el-button>
            </div>
          </template>
          <template v-if="job.match">
            <div class="match-head">
              <el-progress type="circle" :percentage="Number(job.match.match_score || 0)" :width="110" :stroke-width="10">
                <template #default>
                  <div class="match-score">{{ job.match.match_score }}</div>
                  <div class="match-level">推荐等级 {{ job.match.recommend_level }}</div>
                </template>
              </el-progress>
              <div class="match-reason">
                <p style="font-weight: 600; color: #303133">推荐理由</p>
                <p>{{ job.match.recommend_reason }}</p>
              </div>
            </div>
            <el-row :gutter="12" style="margin-top: 16px">
              <el-col :span="6">
                <div class="dim-card"><div class="dim-score" style="color: #409eff">{{ job.match.skill_score ?? '-' }}</div><div class="dim-label">技能匹配</div></div>
              </el-col>
              <el-col :span="6">
                <div class="dim-card"><div class="dim-score" style="color: #67c23a">{{ job.match.experience_score ?? '-' }}</div><div class="dim-label">经历匹配</div></div>
              </el-col>
              <el-col :span="6">
                <div class="dim-card"><div class="dim-score" style="color: #e6a23c">{{ job.match.education_score ?? '-' }}</div><div class="dim-label">学历匹配</div></div>
              </el-col>
              <el-col :span="6">
                <div class="dim-card"><div class="dim-score" style="color: #f56c6c">{{ job.match.preference_score ?? '-' }}</div><div class="dim-label">偏好匹配</div></div>
              </el-col>
            </el-row>
            <el-tag type="info" effect="plain" size="small" style="margin-top: 12px">分析引擎：{{ job.match.model_used === 'llm' ? 'LLM Agent' : '规则引擎' }}</el-tag>
          </template>
          <el-empty v-else description="点击「开始分析」查看匹配结果" :image-size="80" />
        </el-card>
      </el-col>

      <el-col :span="9">
        <el-card>
          <template #header><span>🏢 公司信息</span></template>
          <div class="company-head">
            <el-avatar :size="48" shape="square">{{ job.company_name?.[0] }}</el-avatar>
            <div>
              <div class="company-name">{{ job.company_name }}</div>
              <div class="company-meta">{{ job.industry || '-' }} · {{ job.company_type || '-' }}</div>
            </div>
          </div>
          <el-descriptions :column="1" size="small" style="margin-top: 12px">
            <el-descriptions-item label="公司规模">{{ company.scale || '-' }}</el-descriptions-item>
            <el-descriptions-item label="所在城市">{{ company.address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag :type="riskType(company.risk_level)" size="small">{{ riskText(company.risk_level) }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <p class="desc-text" style="margin-top: 12px">{{ company.description || '暂无公司介绍' }}</p>
        </el-card>
      </el-col>
    </el-row>

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
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  addFavorite, createApplication, getCompany, getJob, getResumes, matchJob, removeFavorite, submitApplication,
} from '@/api'

const route = useRoute()
const job = ref(null)
const company = ref({})
const resumes = ref([])
const matching = ref(false)
const applying = ref(false)
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
.job-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.job-sub {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #606266;
  margin-top: 8px;
  font-size: 14px;
}
.salary {
  color: #f56c6c;
  font-size: 22px;
  font-weight: 700;
  white-space: nowrap;
}
.desc-text {
  color: #303133;
  line-height: 1.8;
  font-size: 14px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.match-head {
  display: flex;
  gap: 24px;
  align-items: center;
}
.match-score {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}
.match-level {
  font-size: 12px;
  color: #909399;
}
.match-reason {
  flex: 1;
  color: #606266;
  font-size: 14px;
  line-height: 1.8;
}
.dim-card {
  text-align: center;
  padding: 12px;
  background: #f7fafc;
  border-radius: 8px;
}
.dim-score {
  font-size: 22px;
  font-weight: 700;
}
.dim-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.company-head {
  display: flex;
  gap: 12px;
  align-items: center;
}
.company-name {
  font-size: 16px;
  font-weight: 600;
}
.company-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
</style>


