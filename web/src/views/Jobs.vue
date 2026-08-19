<template>
  <div>
    <el-card>
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="职位 / 公司" clearable style="width: 180px" @keyup.enter="load" @clear="load" />
        </el-form-item>
        <el-form-item label="城市">
          <el-select v-model="filters.city" placeholder="全部" clearable filterable style="width: 110px" @change="load">
            <el-option v-for="c in CITIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="学历">
          <el-select v-model="filters.education" placeholder="全部" clearable style="width: 100px" @change="load">
            <el-option v-for="e in ['博士', '硕士', '本科', '大专']" :key="e" :label="e" :value="e" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filters.job_type" placeholder="全部" clearable style="width: 100px" @change="load">
            <el-option label="全职" value="全职" />
            <el-option label="实习" value="实习" />
            <el-option label="校招" value="校招" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="filters.source" placeholder="全部" clearable style="width: 120px" @change="load">
            <el-option label="智联招聘" value="zhaopin" />
            <el-option label="BOSS直聘" value="zhipin" />
            <el-option label="模拟数据" value="mock" />
          </el-select>
        </el-form-item>
        <el-form-item label="经验">
          <el-select v-model="filters.experience" placeholder="全部" clearable style="width: 110px" @change="load">
            <el-option label="经验不限" value="不限" />
            <el-option label="1-3年" value="1-3" />
            <el-option label="3-5年" value="3-5" />
            <el-option label="5年以上" value="5-10" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" plain :loading="importing" style="margin-left: 8px" @click="openImport">
            从平台导入岗位
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 16px">
      <el-table :data="jobs" size="default" @row-click="(row) => $router.push(`/jobs/${row.id}`)" style="cursor: pointer">
        <el-table-column label="职位" min-width="200">
          <template #default="{ row }">
            <div class="job-title">{{ row.title }}</div>
            <div class="job-tags">
              <el-tag v-for="t in row.tags?.slice(0, 3)" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="公司" width="130">
          <template #default="{ row }">{{ row.company_name }}</template>
        </el-table-column>
        <el-table-column label="城市" width="80">
          <template #default="{ row }">{{ row.city }}</template>
        </el-table-column>
        <el-table-column label="薪资" width="120">
          <template #default="{ row }"><span class="salary">{{ row.salary_text }}</span></template>
        </el-table-column>
        <el-table-column label="学历/经验" width="120">
          <template #default="{ row }">
            <div>{{ row.education }} · {{ row.experience }}</div>
            <el-tag v-if="row.job_type === '实习'" size="small" type="warning" effect="plain">实习</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="110">
          <template #default="{ row }">
            <el-tag :type="sourceType(row.source)" size="small" effect="plain">{{ sourceText(row.source) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="匹配" width="110">
          <template #default="{ row }">
            <template v-if="row.match">
              <el-tag :type="levelType(row.match.recommend_level)" size="small">
                {{ row.match.match_score }}分 {{ row.match.recommend_level }}
              </el-tag>
            </template>
            <el-button v-else link type="primary" size="small" @click.stop="handleMatch(row)">分析</el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.is_favorite" link type="warning" @click.stop="toggleFavorite(row)">收藏</el-button>
            <el-button v-else link type="warning" @click.stop="toggleFavorite(row)">取消收藏</el-button>
            <el-button v-if="row.is_applied" link disabled>已投递</el-button>
            <el-button v-else link type="primary" @click.stop="$router.push(`/jobs/${row.id}`)">投递</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="load"
      />
    </el-card>

    <el-dialog v-model="importVisible" title="多平台导入岗位" width="560px" destroy-on-close>
      <el-form label-width="108px">
        <el-form-item label="采集平台">
          <el-checkbox-group v-model="importForm.platforms">
            <el-checkbox value="zhaopin">智联招聘</el-checkbox>
            <el-checkbox value="zhipin">BOSS直聘</el-checkbox>
            <el-checkbox value="mock">模拟数据</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-alert
          v-if="importForm.platforms.includes('zhipin')"
          :title="zhipinHint"
          :type="zhipinReady ? 'success' : 'warning'"
          show-icon
          :closable="false"
          style="margin-bottom: 12px"
        />
        <el-form-item v-if="importForm.platforms.includes('zhipin')" label="调试浏览器">
          <el-button :loading="launchingChrome" @click="launchChrome">启动调试 Chrome</el-button>
          <span class="hint">{{ zhipinReady ? '已连接，请确认已登录 BOSS' : '会弹出独立窗口，登录一次即可' }}</span>
        </el-form-item>
        <el-form-item label="智能补全">
          <el-switch v-model="importForm.use_profile" />
          <span class="hint">根据简历画像与求职偏好自动填充空项</span>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="importForm.keyword" placeholder="留空则用画像职位 / 偏好目标职位" />
        </el-form-item>
        <el-form-item label="工作城市">
          <el-select v-model="importForm.city" placeholder="留空则用偏好城市 / 画像城市" filterable allow-create clearable style="width: 100%">
            <el-option v-for="c in CITIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="薪资范围">
          <el-input-number v-model="importForm.salary_min" :min="0" :step="1000" controls-position="right" placeholder="最低" style="width: 140px" />
          <span style="margin: 0 8px">~</span>
          <el-input-number v-model="importForm.salary_max" :min="0" :step="1000" controls-position="right" placeholder="最高" style="width: 140px" />
          <span class="hint">元/月</span>
        </el-form-item>
        <el-form-item label="采集页数">
          <el-input-number v-model="importForm.pages" :min="1" :max="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importForm.platforms.length" @click="submitImport">
          开始采集
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  addFavorite,
  getCollectors,
  getCurrentProfile,
  launchZhipinChrome,
  getJobs,
  getJobSources,
  getPreference,
  importJobs,
  matchJob,
  removeFavorite,
} from '@/api'

const CITIES = ['北京', '上海', '深圳', '杭州', '广州', '成都', '南京', '武汉', '西安', '苏州', '长沙', '郑州']

const jobs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const importing = ref(false)
const importVisible = ref(false)
const launchingChrome = ref(false)
const collectors = ref([])

const filters = reactive({
  keyword: '', city: '', education: '', job_type: '', experience: '', source: '',
})

const importForm = reactive({
  platforms: ['zhaopin', 'zhipin'],
  keyword: '',
  city: '',
  salary_min: null,
  salary_max: null,
  pages: 1,
  use_profile: true,
})

const zhipinReady = computed(() => collectors.value.find((c) => c.id === 'zhipin')?.ready)
const zhipinHint = computed(() => {
  if (zhipinReady.value) return '已检测到调试 Chrome，BOSS 直聘可以采集。'
  return '还没检测到调试 Chrome。点下面按钮启动，并在弹出窗口登录 BOSS 直聘。'
})

function levelType(level) {
  return { S: 'danger', A: 'warning', B: 'primary', C: 'info', D: 'info' }[level] || 'info'
}

function sourceText(s) {
  return { zhaopin: '智联招聘', zhipin: 'BOSS直聘', mock: '模拟数据', liepin: '猎聘', ncss: '24365' }[s] || s || '-'
}
function sourceType(s) {
  return { zhaopin: 'success', zhipin: 'danger', mock: 'info' }[s] || 'info'
}

async function load() {
  const res = await getJobs({ ...filters, page: page.value, page_size: pageSize })
  jobs.value = res.items
  total.value = res.total
}

function resetFilters() {
  Object.assign(filters, { keyword: '', city: '', education: '', job_type: '', experience: '', source: '' })
  page.value = 1
  load()
}

async function toggleFavorite(row) {
  if (row.is_favorite) {
    await removeFavorite(row.id)
  } else {
    await addFavorite(row.id)
  }
  ElMessage.success(row.is_favorite ? '已取消收藏' : '收藏成功')
  load()
}

async function handleMatch(row) {
  ElMessage.info(`正在分析「${row.title}」...`)
  await matchJob(row.id)
  ElMessage.success('匹配分析完成')
  load()
}

async function refreshCollectors() {
  try {
    const res = await getCollectors()
    collectors.value = res.items || []
  } catch {
    collectors.value = []
  }
}

async function launchChrome() {
  launchingChrome.value = true
  try {
    const res = await launchZhipinChrome()
    ElMessage.success(res.message || '已请求启动 Chrome')
    for (let i = 0; i < 12; i++) {
      await new Promise((r) => setTimeout(r, 1000))
      await refreshCollectors()
      if (zhipinReady.value) {
        ElMessage.success('已连上调试 Chrome，请在弹出窗口登录 BOSS 后再采集')
        return
      }
    }
    ElMessage.warning('窗口应已弹出。若没有，请双击 auto-zhipin/start_chrome.bat')
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || err.message || '启动失败')
  } finally {
    launchingChrome.value = false
  }
}

async function openImport() {
  importVisible.value = true
  await refreshCollectors()
  if (!importForm.use_profile) return
  try {
    const pref = await getPreference()
    if (!importForm.keyword && pref.target_positions?.[0]) importForm.keyword = pref.target_positions[0]
    if (!importForm.city && pref.cities?.[0]) importForm.city = pref.cities[0]
    if (importForm.salary_min == null && pref.salary_min != null) importForm.salary_min = pref.salary_min
    if (importForm.salary_max == null && pref.salary_max != null) importForm.salary_max = pref.salary_max
  } catch { /* 无偏好 */ }
  try {
    const profile = await getCurrentProfile()
    if (!importForm.keyword && profile.title) importForm.keyword = profile.title
    if (!importForm.city && profile.city) importForm.city = profile.city
  } catch { /* 无画像 */ }
}

async function submitImport() {
  if (!importForm.platforms.length) {
    ElMessage.warning('请至少选择一个平台')
    return
  }
  importing.value = true
  try {
    const res = await importJobs({
      platforms: importForm.platforms,
      keyword: importForm.keyword || undefined,
      city: importForm.city || undefined,
      salary_min: importForm.salary_min,
      salary_max: importForm.salary_max,
      pages: importForm.pages,
      use_profile: importForm.use_profile,
    })
    importVisible.value = false
    ElMessage.info(res.message)
    const ids = new Set((res.tasks || []).map((t) => t.job_source_id))
    const needLongWait = importForm.platforms.includes('zhipin')
    const rounds = needLongWait ? 40 : 12
    const interval = needLongWait ? 3000 : 2000
    for (let i = 0; i < rounds; i++) {
      await new Promise((r) => setTimeout(r, interval))
      const sources = await getJobSources()
      const related = sources.filter((s) => ids.has(s.id))
      if (related.length && related.every((s) => s.status !== 'QUEUED' && s.status !== 'RUNNING')) {
        const ok = related.filter((s) => s.status === 'SUCCESS')
        const fail = related.filter((s) => s.status === 'FAILED')
        const imported = ok.reduce((sum, s) => sum + (s.imported_count || 0), 0)
        const found = ok.reduce((sum, s) => sum + (s.total_found || 0), 0)
        if (ok.length) {
          ElNotification({
            title: '采集完成',
            message: `${ok.map((s) => sourceText(s.platform)).join('、')} 新导入 ${imported} 条（发现 ${found} 条，重复已跳过）`,
            type: 'success',
          })
        }
        fail.forEach((s) => {
          ElNotification({
            title: `${sourceText(s.platform)} 采集失败`,
            message: s.error_message || s.status,
            type: 'error',
          })
        })
        await load()
        return
      }
    }
    ElMessage.warning('采集仍在进行，请稍后刷新岗位库')
    await load()
  } finally {
    importing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.job-title {
  font-weight: 600;
}
.job-tags {
  margin-top: 4px;
  display: flex;
  gap: 4px;
}
.salary {
  color: #f56c6c;
  font-weight: 600;
}
.hint {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
