<template>
  <div>
    <el-card>
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="职位 / 公司" clearable style="width: 180px" @keyup.enter="load" @clear="load" />
        </el-form-item>
        <el-form-item label="城市">
          <el-select v-model="filters.city" placeholder="全部" clearable style="width: 110px" @change="load">
            <el-option v-for="c in ['北京', '上海', '深圳', '杭州']" :key="c" :label="c" :value="c" />
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
          <el-select v-model="filters.source" placeholder="全部" clearable style="width: 110px" @change="load">
            <el-option label="智联招聘" value="zhaopin" />
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
          <el-dropdown style="margin-left: 8px" @command="handleImport">
            <el-button type="success" plain :loading="importing">
              🚀 从平台导入岗位<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="zhaopin">智联招聘</el-dropdown-item>
                <el-dropdown-item command="mock">模拟数据</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
        <el-table-column label="来源" width="100">
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { addFavorite, getJobs, getJobSources, importJobs, matchJob, removeFavorite } from '@/api'

const jobs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const importing = ref(false)

const filters = reactive({
  keyword: '', city: '', education: '', job_type: '', experience: '', source: '',
})

function levelType(level) {
  return { S: 'danger', A: 'warning', B: 'primary', C: 'info', D: 'info' }[level] || 'info'
}

function sourceText(s) {
  return { zhaopin: '智联招聘', mock: '模拟数据', liepin: '猎聘', ncss: '24365' }[s] || s || '-'
}
function sourceType(s) {
  return { zhaopin: 'success', mock: 'info' }[s] || 'info'
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

async function handleImport(platform) {
  importing.value = true
  try {
    const res = await importJobs({
      platform,
      keyword: filters.keyword || 'Java',
      city: filters.city || '北京',
      pages: 1,
    })
    ElMessage.info(res.message)
    // 轮询采集结果
    for (let i = 0; i < 8; i++) {
      await new Promise((r) => setTimeout(r, 2000))
      const sources = await getJobSources()
      const latest = sources.find((s) => s.platform === platform)
      if (latest && latest.status !== 'QUEUED' && latest.status !== 'RUNNING') {
        if (latest.status === 'SUCCESS') {
          ElNotification({
            title: '采集完成',
            message: `${sourceText(platform)}导入 ${latest.imported_count} 条岗位（共发现 ${latest.total_found} 条）`,
            type: 'success',
          })
        } else {
          ElNotification({ title: '采集失败', message: latest.status, type: 'error' })
        }
        await load()
        return
      }
    }
    ElMessage.warning('采集任务仍在进行，请稍后手动刷新查看')
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
</style>

