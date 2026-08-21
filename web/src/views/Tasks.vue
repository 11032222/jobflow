<template>
  <div>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="Agent 任务状态：CREATED → QUEUED → RUNNING → SUCCESS / FAILED / RETRYING / WAITING_USER（等待人工接管）"
      style="margin-bottom: 16px"
    />

    <section class="panel">
      <header class="panel-header">
        <span class="panel-title"><el-icon><Cpu /></el-icon>Agent 任务</span>
        <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
      </header>

      <el-table :data="tasks">
        <el-table-column label="任务类型" width="160">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ taskTypeText(row.task_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="taskStatusTag(row.status)" size="small" effect="plain">{{ taskStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="8" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="165">
          <template #default="{ row }">{{ row.created_at.slice(0, 16).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="提示 / 错误" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.user_message || row.error_message || '-' }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!tasks.length" description="暂无任务记录" :image-size="80" />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Cpu, Refresh } from '@element-plus/icons-vue'
import { getTasks } from '@/api'

const tasks = ref([])

function taskTypeText(t) {
  return { RESUME_PARSE: '简历解析', JOB_SEARCH: '岗位搜索', JOB_MATCH: '岗位匹配', COMPANY_ANALYZE: '公司分析', JOB_APPLY: '岗位投递' }[t] || t
}
function taskStatusText(s) {
  return { CREATED: '已创建', QUEUED: '排队中', RUNNING: '执行中', SUCCESS: '成功', FAILED: '失败', RETRYING: '重试中', WAITING_USER: '等待人工' }[s] || s
}
function taskStatusTag(s) {
  return { SUCCESS: 'success', FAILED: 'danger', WAITING_USER: 'warning', RETRYING: 'warning', RUNNING: 'primary' }[s] || 'info'
}

async function load() {
  tasks.value = await getTasks()
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
</style>