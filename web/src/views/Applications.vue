<template>
  <div>
    <section class="panel summary-panel">
      <div class="summary-chips">
        <div v-for="(label, key) in statusMap" :key="key" class="chip" :class="`chip-${key.toLowerCase()}`" @click="statusFilter = key === statusFilter ? '' : key">
          <span class="chip-label">{{ label }}</span>
          <b>{{ countByStatus(key) }}</b>
        </div>
        <div class="chip chip-all" :class="{ active: !statusFilter }" @click="statusFilter = ''">
          <span class="chip-label">全部</span>
          <b>{{ apps.length }}</b>
        </div>
      </div>
    </section>

    <section class="panel list-panel">
      <header class="panel-header">
        <span class="panel-title"><el-icon><Promotion /></el-icon>投递记录</span>
        <el-select v-model="statusFilter" placeholder="按状态筛选" clearable style="width: 150px" @change="statusFilter = $event || ''">
          <el-option v-for="(label, key) in statusMap" :key="key" :label="label" :value="key" />
        </el-select>
      </header>
      <el-table :data="filteredApps" @row-click="openDetail">
        <el-table-column label="职位" min-width="200">
          <template #default="{ row }">
            <div class="job-title">{{ row.job_title }}</div>
            <div class="company">{{ row.company_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small" effect="plain">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="投递渠道" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" type="info">{{ row.channel === 'EMAIL' ? '邮箱投递' : row.channel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="收件邮箱" min-width="180">
          <template #default="{ row }">{{ row.email_to || '-' }}</template>
        </el-table-column>
        <el-table-column label="投递时间" width="150">
          <template #default="{ row }">{{ (row.sent_at || row.created_at || '').slice(0, 16).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="最近更新" width="150">
          <template #default="{ row }">{{ row.updated_at.slice(0, 16).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!filteredApps.length" description="暂无投递记录" :image-size="80" />
    </section>

    <!-- 投递详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`投递详情 - ${detail?.job_title || ''}`" size="480px">
      <template v-if="detail">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="公司">{{ detail.company_name }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="statusTag(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="投递渠道">{{ detail.channel === 'EMAIL' ? '邮箱投递（演示）' : detail.channel }}</el-descriptions-item>
          <el-descriptions-item label="收件邮箱">{{ detail.email_to || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮件 Message-ID">{{ detail.email_message_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="投递备注">{{ detail.note || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">状态流转</el-divider>
        <div class="transition-btns">
          <el-button
            v-for="s in allowedTransitions"
            :key="s"
            size="small"
            :type="s === 'OFFER' ? 'success' : s === 'REJECTED' || s === 'CLOSED' ? 'danger' : 'primary'"
            @click="handleTransition(s)"
          >
            {{ statusText(s) }}
          </el-button>
          <div v-if="!allowedTransitions.length" class="text-muted end-tip">当前状态为终态，无更多流转</div>
        </div>

        <el-divider content-position="left">状态时间线</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="e in detail.events"
            :key="e.id"
            :timestamp="e.created_at.slice(0, 16).replace('T', ' ')"
            :type="e.operator === 'SYSTEM' ? 'primary' : 'success'"
          >
            <div class="event-item">
              <b>{{ statusText(e.to_status) }}</b>
              <el-tag size="small" class="event-tag">{{ e.operator === 'SYSTEM' ? '系统' : '用户' }}</el-tag>
              <div class="text-muted event-comment">{{ e.comment }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import { getApplications, getApplication, updateApplicationStatus } from '@/api'

const apps = ref([])
const drawerVisible = ref(false)
const detail = ref(null)
const statusFilter = ref('')

const statusMap = {
  PENDING: '待投递', SUBMITTING: '投递中', SUBMITTED: '已投递', FAILED: '投递失败',
  WAITING: '待反馈', TEST: '笔试', INTERVIEW: '面试', OFFER: 'Offer',
  REJECTED: '未通过', CLOSED: '已关闭',
}

const TRANSITIONS = {
  PENDING: ['SUBMITTING', 'CLOSED'],
  SUBMITTING: ['SUBMITTED', 'FAILED', 'CLOSED'],
  SUBMITTED: ['WAITING', 'TEST', 'INTERVIEW', 'OFFER', 'REJECTED', 'CLOSED'],
  WAITING: ['TEST', 'INTERVIEW', 'OFFER', 'REJECTED', 'CLOSED'],
  TEST: ['INTERVIEW', 'OFFER', 'REJECTED', 'CLOSED'],
  INTERVIEW: ['OFFER', 'REJECTED', 'CLOSED'],
  OFFER: ['CLOSED'],
  REJECTED: ['CLOSED'],
  FAILED: ['SUBMITTING', 'CLOSED'],
  CLOSED: [],
}

const filteredApps = computed(() =>
  statusFilter.value ? apps.value.filter((a) => a.status === statusFilter.value) : apps.value,
)
const allowedTransitions = computed(() => TRANSITIONS[detail.value?.status] || [])

function statusText(s) {
  return statusMap[s] || s
}
function statusTag(s) {
  return { INTERVIEW: 'warning', TEST: 'warning', OFFER: 'success', REJECTED: 'danger', CLOSED: 'info', SUBMITTED: 'success', WAITING: 'primary', FAILED: 'danger' }[s] || 'info'
}
function countByStatus(key) {
  return apps.value.filter((a) => a.status === key).length
}

async function load() {
  apps.value = await getApplications()
}

async function openDetail(row) {
  detail.value = await getApplication(row.id)
  drawerVisible.value = true
}

async function handleTransition(target) {
  await updateApplicationStatus(detail.value.id, { status: target, comment: `用户手动更新为${statusText(target)}` })
  ElMessage.success(`已更新为「${statusText(target)}」`)
  drawerVisible.value = false
  await load()
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
.summary-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--jf-border);
  border-radius: 10px;
  background: var(--jf-surface);
  cursor: pointer;
  transition: all 0.18s ease;
}
.chip:hover { border-color: var(--jf-primary); }
.chip.active { border-color: var(--jf-primary); background: var(--jf-primary-softer); }
.chip b { font-size: 16px; color: var(--jf-ink); }
.chip-label { font-size: 13px; color: var(--jf-ink-soft); }
.list-panel { margin-top: 16px; }
.job-title { font-weight: 600; color: var(--jf-ink); }
.company { color: var(--jf-muted); font-size: 12px; margin-top: 2px; }
.transition-btns { display: flex; flex-wrap: wrap; gap: 8px; }
.end-tip { font-size: 13px; }
.event-item { font-size: 13px; }
.event-tag { margin-left: 8px; }
.event-comment { font-size: 12px; margin-top: 4px; }
</style>