<template>
  <div>
    <el-alert
      v-if="!profile"
      type="warning"
      :closable="false"
      show-icon
      title="尚未建立求职画像。可以上传简历，或手动填写画像信息。"
      style="margin-bottom: 16px"
    />
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📄 简历文件</span>
              <el-button type="primary" size="small" :loading="uploading" @click="fileInput?.click()">上传简历</el-button>
              <input ref="fileInput" type="file" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg" hidden @change="handleUpload" />
            </div>
          </template>
          <el-empty v-if="!resumes.length" description="暂无简历文件" :image-size="80" />
          <div v-for="r in resumes" :key="r.id" class="resume-item">
            <el-icon :size="24" color="#409eff"><Document /></el-icon>
            <div class="resume-info">
              <div class="resume-name">{{ r.file_name }}</div>
              <div class="resume-meta">
                <el-tag size="small" :type="parseTag(r.parse_status)" effect="plain">{{ parseText(r.parse_status) }}</el-tag>
                <span>{{ (r.file_size / 1024).toFixed(0) }} KB</span>
              </div>
            </div>
            <el-button v-if="r.parse_status !== 'SUCCESS' && r.parse_status !== 'PARSING'" link type="primary" size="small" @click="handleParse(r)">解析</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(r)">删除</el-button>
          </div>
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>🎯 求职偏好</span>
              <el-button type="primary" size="small" :loading="savingPref" @click="handleSavePref">保存</el-button>
            </div>
          </template>
          <el-form label-width="80px" label-position="left" size="small">
            <el-form-item label="目标职位">
              <el-select v-model="pref.target_positions" multiple filterable allow-create default-first-option style="width: 100%" placeholder="如 Java后端开发" />
            </el-form-item>
            <el-form-item label="期望城市">
              <el-select v-model="pref.cities" multiple filterable allow-create default-first-option style="width: 100%" placeholder="如 上海" />
            </el-form-item>
            <el-form-item label="薪资范围">
              <el-input-number v-model="pref.salary_min" :min="0" :step="1000" controls-position="right" style="width: 45%" />
              <span style="margin: 0 6px">~</span>
              <el-input-number v-model="pref.salary_max" :min="0" :step="1000" controls-position="right" style="width: 45%" />
            </el-form-item>
            <el-form-item label="岗位类型">
              <el-checkbox-group v-model="pref.job_types">
                <el-checkbox value="全职">全职</el-checkbox>
                <el-checkbox value="实习">实习</el-checkbox>
                <el-checkbox value="校招">校招</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="关键词">
              <el-select v-model="pref.keywords" multiple filterable allow-create default-first-option style="width: 100%" placeholder="如 Java" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右列：画像 -->
      <el-col :span="16">
        <el-card v-if="profile">
          <template #header>
            <div class="card-header">
              <span>👤 求职画像 <el-tag size="small" effect="plain">当前生效</el-tag></span>
              <el-button type="primary" size="small" :loading="savingProfile" @click="handleSaveProfile">保存画像</el-button>
            </div>
          </template>
          <el-form label-width="100px" label-position="left">
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="姓名"><el-input v-model="profileForm.name" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="求职意向"><el-input v-model="profileForm.title" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="所在城市"><el-input v-model="profileForm.city" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="电话"><el-input v-model="profileForm.phone" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="邮箱"><el-input v-model="profileForm.email" /></el-form-item></el-col>
              <el-col :span="8">
                <el-form-item label="学历">
                  <el-select v-model="profileForm.education_level" style="width: 100%">
                    <el-option v-for="e in ['博士', '硕士', '本科', '大专']" :key="e" :label="e" :value="e" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="学校"><el-input v-model="profileForm.school" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="专业"><el-input v-model="profileForm.major" /></el-form-item></el-col>
              <el-col :span="8">
                <el-form-item label="工作年限">
                  <el-input-number v-model="profileForm.years_of_experience" :min="0" :max="40" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="个人简介">
              <el-input v-model="profileForm.summary" type="textarea" :rows="3" />
            </el-form-item>
          </el-form>

          <el-divider content-position="left">技能</el-divider>
          <div class="skill-area">
            <el-tag v-for="s in profile.skills" :key="s.id" closable size="large" style="margin: 4px" @close="handleDeleteSkill(s)">
              {{ s.name }}
            </el-tag>
            <el-input v-model="newSkill" size="small" placeholder="添加技能，回车确认" style="width: 160px" @keyup.enter="handleAddSkill" />
          </div>

          <el-divider content-position="left">教育 / 工作 / 项目经历</el-divider>
          <el-timeline>
            <el-timeline-item v-for="e in profile.experiences" :key="e.id" :timestamp="expRange(e)">
              <div class="exp-item">
                <b>{{ e.school_or_company }}</b>
                <el-tag size="small" style="margin-left: 8px">{{ expTypeText(e.type) }}</el-tag>
                <el-tag v-if="e.title" size="small" type="info" effect="plain" style="margin-left: 4px">{{ e.title }}</el-tag>
                <el-button link type="danger" size="small" style="margin-left: 8px" @click="handleDeleteExp(e)">删除</el-button>
                <div class="exp-desc">{{ e.description }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-button type="primary" plain size="small" @click="expDialogVisible = true">+ 添加经历</el-button>
        </el-card>

        <el-card v-else>
          <template #header><span>👤 手动创建求职画像</span></template>
          <el-form :model="profileForm" label-width="100px" style="max-width: 560px">
            <el-form-item label="姓名"><el-input v-model="profileForm.name" /></el-form-item>
            <el-form-item label="求职意向"><el-input v-model="profileForm.title" /></el-form-item>
            <el-form-item label="城市"><el-input v-model="profileForm.city" /></el-form-item>
            <el-form-item label="电话"><el-input v-model="profileForm.phone" /></el-form-item>
            <el-form-item label="邮箱"><el-input v-model="profileForm.email" /></el-form-item>
            <el-button type="primary" :loading="savingProfile" @click="handleCreateProfile">创建画像</el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>


    <!-- 添加经历弹窗 -->
    <el-dialog v-model="expDialogVisible" title="添加经历" width="520px">
      <el-form :model="expForm" label-width="90px">
        <el-form-item label="类型">
          <el-select v-model="expForm.type" style="width: 100%">
            <el-option label="教育经历" value="education" />
            <el-option label="工作经历" value="work" />
            <el-option label="项目经历" value="project" />
            <el-option label="证书" value="certificate" />
            <el-option label="获奖" value="award" />
          </el-select>
        </el-form-item>
        <el-form-item label="机构/公司"><el-input v-model="expForm.school_or_company" /></el-form-item>
        <el-form-item v-if="expForm.type === 'education'" label="学历"><el-input v-model="expForm.degree" /></el-form-item>
        <el-form-item v-if="expForm.type === 'education'" label="专业"><el-input v-model="expForm.major" /></el-form-item>
        <el-form-item v-else label="职位/名称"><el-input v-model="expForm.title" /></el-form-item>
        <el-form-item label="起止时间">
          <el-date-picker v-model="expRangeValue" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="expForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="expDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddExp">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import {
  addExperience, addSkill, createProfile, deleteExperience, deleteResume, deleteSkill,
  getCurrentProfile, getPreference, getResumes, parseResume, savePreference, updateProfile, uploadResume,
} from '@/api'

const resumes = ref([])
const profile = ref(null)
const uploading = ref(false)
const savingProfile = ref(false)
const savingPref = ref(false)
const newSkill = ref('')
const fileInput = ref(null)
const expDialogVisible = ref(false)

const pref = reactive({
  target_positions: [], cities: [], salary_min: null, salary_max: null,
  job_types: [], industries: [], company_types: [], keywords: [], is_auto_match: true,
})

const profileForm = reactive({
  name: '', title: '', phone: '', email: '', city: '',
  education_level: '', school: '', major: '', years_of_experience: 0, summary: '',
})

const expForm = reactive({
  type: 'work', school_or_company: '', degree: '', major: '', title: '',
  description: '', start_date: null, end_date: null,
})
const expRangeValue = ref([])


function fillProfileForm(p) {
  Object.assign(profileForm, {
    name: p.name || '', title: p.title || '', phone: p.phone || '', email: p.email || '',
    city: p.city || '', education_level: p.education_level || '', school: p.school || '',
    major: p.major || '', years_of_experience: p.years_of_experience || 0, summary: p.summary || '',
  })
}

function parseText(s) {
  return { PENDING: '待解析', PARSING: '解析中', SUCCESS: '解析成功', FAILED: '解析失败' }[s] || s
}
function parseTag(s) {
  return { SUCCESS: 'success', FAILED: 'danger', PARSING: 'warning' }[s] || 'info'
}
function expTypeText(t) {
  return { education: '教育', work: '工作', project: '项目', certificate: '证书', award: '获奖', other: '其他' }[t] || t
}
function expRange(e) {
  const fmt = (d) => (d ? d.slice(0, 10) : '至今')
  return `${fmt(e.start_date)} ~ ${fmt(e.end_date)}`
}

async function loadAll() {
  try { resumes.value = await getResumes() } catch { /* 忽略 */ }
  try {
    profile.value = await getCurrentProfile()
    if (profile.value) fillProfileForm(profile.value)
  } catch {
    profile.value = null
  }
  try {
    Object.assign(pref, await getPreference())
  } catch { /* 忽略 */ }
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    await uploadResume(file)
    ElMessage.success('上传成功')
    await loadAll()
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

async function handleParse(r) {
  await parseResume(r.id)
  ElMessage.info('解析任务已启动，完成后将自动生成新画像')
  for (let i = 0; i < 10; i++) {
    await new Promise((res) => setTimeout(res, 2000))
    const list = await getResumes()
    const cur = list.find((x) => x.id === r.id)
    if (cur && cur.parse_status !== 'PARSING') {
      if (cur.parse_status === 'SUCCESS') {
        ElMessage.success('简历解析完成，已生成新的求职画像')
      } else {
        ElMessage.warning('简历解析失败，可检查文件内容后重试')
      }
      break
    }
  }
  await loadAll()
}

async function handleDelete(r) {
  await ElMessageBox.confirm(`确定删除简历「${r.file_name}」吗？`, '提示', { type: 'warning' })
  await deleteResume(r.id)
  ElMessage.success('已删除')
  await loadAll()
}

async function handleSaveProfile() {
  savingProfile.value = true
  try {
    await updateProfile(profile.value.id, { ...profileForm })
    ElMessage.success('画像已保存')
    await loadAll()
  } finally {
    savingProfile.value = false
  }
}

async function handleCreateProfile() {
  savingProfile.value = true
  try {
    await createProfile({ ...profileForm })
    ElMessage.success('画像创建成功')
    await loadAll()
  } finally {
    savingProfile.value = false
  }
}

async function handleAddSkill() {
  const name = newSkill.value.trim()
  if (!name) return
  await addSkill(profile.value.id, { name })
  newSkill.value = ''
  await loadAll()
}

async function handleDeleteSkill(s) {
  await deleteSkill(profile.value.id, s.id)
  await loadAll()
}

async function handleAddExp() {
  const [start, end] = expRangeValue.value || []
  await addExperience(profile.value.id, {
    ...expForm, start_date: start || null, end_date: end || null,
  })
  expDialogVisible.value = false
  expRangeValue.value = []
  Object.assign(expForm, { type: 'work', school_or_company: '', degree: '', major: '', title: '', description: '', start_date: null, end_date: null })
  ElMessage.success('经历已添加')
  await loadAll()
}

async function handleDeleteExp(e) {
  await deleteExperience(profile.value.id, e.id)
  await loadAll()
}

async function handleSavePref() {
  savingPref.value = true
  try {
    await savePreference({ ...pref })
    ElMessage.success('求职偏好已保存')
  } finally {
    savingPref.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.resume-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f2f5;
}
.resume-item:last-child {
  border-bottom: none;
}
.resume-info {
  flex: 1;
  min-width: 0;
}
.resume-name {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.resume-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 2px;
}
.skill-area {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.exp-item {
  font-size: 14px;
}
.exp-desc {
  color: #606266;
  font-size: 13px;
  margin-top: 4px;
}
</style>

