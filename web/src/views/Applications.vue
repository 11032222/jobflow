<template>
  <div>
    <el-card>
      <div class="kanban-summary">
        <el-tag v-for="(label, key) in statusMap" :key="key" :type="statusTag(key)" effect="plain" size="large" style="margin: 2px">
          {{ label }} {{ countByStatus(key) }}
        </el-tag>
      </div>
    </el-card>

    <el-card style="margin-top: 16px">
      <el-table :data="filteredApps" @row-click="openDetail" style="cursor: pointer">
        <el-table-column label="职位" min-width="200">
          <template #default="{ row }">
            <div class="job-title">{{ row.job_title }}</div>
            <div class="company">{{ row.company_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
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
    </el-card>

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
            → {{ statusText(s) }}
          </el-button>
          <div v-if="!allowedTransitions.length" style="color: #909399; font-size: 13px">当前状态为终态，无更多流转</div>
        </div>

        <el-divider content-position="left">状态时间线</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="e in detail.events"
            :key="e.id"
            :timestamp="e.created_at.slice(0, 16).replace('T', ' ')"
            :type="e.operator === 'SYSTEM' ? 'primary' : 'success'"
          >
            <div>
              <b>{{ statusText(e.to_status) }}</b>
              <el-tag size="small" style="margin-left: 8px">{{ e.operator === 'SYSTEM' ? '系统' : '用户' }}</el-tag>
              <div style="color: #909399; font-size: 12px; margin-top: 4px">{{ e.comment }}</div>
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

const filteredApps = computed(() => apps.value)
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
.kanban-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.job-title {
  font-weight: 600;
}
.company {
  color: #909399;
  font-size: 12px;
}
.transition-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>

