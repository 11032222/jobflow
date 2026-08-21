<template>
  <div class="apps-page">
    <section class="filter-bar">
      <button
        class="filter-chip"
        :class="{ active: !statusFilter }"
        type="button"
        @click="statusFilter = ''"
      >
        <span class="chip-label">全部</span>
        <b>{{ apps.length }}</b>
      </button>
      <button
        v-for="(label, key) in statusMap"
        :key="key"
        class="filter-chip"
        :class="{ active: statusFilter === key }"
        type="button"
        @click="statusFilter = statusFilter === key ? '' : key"
      >
        <span class="status-dot" :style="{ background: dotColor(key) }"></span>
        <span class="chip-label">{{ label }}</span>
        <b>{{ countByStatus(key) }}</b>
      </button>
    </section>

    <section v-for="group in groups" :key="group.key" class="status-group">
      <header class="group-head">
        <span class="status-dot" :style="{ background: dotColor(group.key) }"></span>
        <span class="group-title">{{ group.label }}</span>
        <span class="group-count">{{ group.items.length }}</span>
      </header>

      <div v-if="group.items.length" class="card-list">
        <button
          v-for="a in group.items"
          :key="a.id"
          class="app-card"
          type="button"
          @click="openDetail(a)"
        >
          <div class="card-main">
            <div class="card-title">{{ a.job_title }}</div>
            <div class="card-company">{{ a.company_name }}</div>
          </div>
          <div class="card-side">
            <span class="meta-chip">{{ channelText(a.channel) }}</span>
            <span class="meta-time">{{ timeText(a.sent_at || a.created_at) }}</span>
            <el-tag :type="statusTag(a.status)" size="small" effect="plain">
              {{ statusText(a.status) }}
            </el-tag>
          </div>
        </button>
      </div>
      <div v-else class="group-empty">暂无记录</div>
    </section>

    <el-drawer
      v-model="drawerVisible"
      :title="`投递详情 - ${detail?.job_title || ''}`"
      size="480px"
    >
      <template v-if="detail">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="公司">{{ detail.company_name }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="statusTag(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="投递渠道">
            {{ channelText(detail.channel) }}
          </el-descriptions-item>
          <el-descriptions-item label="收件邮箱">{{ detail.email_to || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮件 Message-ID">
            {{ detail.email_message_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="投递备注">{{ detail.note || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">状态流转</el-divider>
        <div class="transition-btns">
          <el-button
            v-for="s in allowedTransitions"
            :key="s"
            size="small"
            :type="btnType(s)"
            @click="handleTransition(s)"
          >
            {{ statusText(s) }}
          </el-button>
          <div v-if="!allowedTransitions.length" class="end-tip">当前状态为终态，无更多流转</div>
        </div>

        <el-divider content-position="left">状态时间线</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="e in detail.events"
            :key="e.id"
            :timestamp="timeText(e.created_at)"
            :type="e.operator === 'SYSTEM' ? 'primary' : 'success'"
          >
            <div class="event-item">
              <b>{{ statusText(e.to_status) }}</b>
              <el-tag size="small" class="event-tag">
                {{ e.operator === 'SYSTEM' ? '系统' : '用户' }}
              </el-tag>
              <div class="event-comment">{{ e.comment }}</div>
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

const groups = computed(() => {
  const keys = statusFilter.value ? [statusFilter.value] : Object.keys(statusMap)
  return keys
    .map((key) => ({
      key,
      label: statusMap[key],
      items: apps.value.filter((a) => a.status === key),
    }))
    .filter((g) => (statusFilter.value ? true : g.items.length > 0))
})

const allowedTransitions = computed(() => TRANSITIONS[detail.value?.status] || [])

function statusText(s) {
  return statusMap[s] || s
}
function statusTag(s) {
  return {
    INTERVIEW: 'warning', TEST: 'warning', OFFER: 'success', REJECTED: 'danger',
    CLOSED: 'info', SUBMITTED: 'success', WAITING: 'primary', FAILED: 'danger',
  }[s] || 'info'
}
function btnType(s) {
  return s === 'OFFER' ? 'success' : s === 'REJECTED' || s === 'CLOSED' ? 'danger' : 'primary'
}
function dotColor(s) {
  return {
    PENDING: '#909399', SUBMITTING: '#409eff', SUBMITTED: '#67c23a', FAILED: '#f56c6c',
    WAITING: '#409eff', TEST: '#e6a23c', INTERVIEW: '#e6a23c', OFFER: '#67c23a',
    REJECTED: '#f56c6c', CLOSED: '#909399',
  }[s] || '#909399'
}
function channelText(c) {
  return c === 'EMAIL' ? '邮箱投递' : c || '-'
}
function timeText(t) {
  return t ? String(t).slice(0, 16).replace('T', ' ') : '-'
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
  await updateApplicationStatus(detail.value.id, {
    status: target,
    comment: `用户手动更新为${statusText(target)}`,
  })
  ElMessage.success(`已更新为「${statusText(target)}」`)
  drawerVisible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.apps-page { display: flex; flex-direction: column; gap: 16px; }
.filter-bar {
  display: flex; flex-wrap: wrap; gap: 8px;
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 12px 16px;
}
.filter-chip {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 7px 12px;
  border: 1px solid var(--jf-border);
  border-radius: 999px;
  background: var(--jf-surface);
  color: var(--jf-ink);
  cursor: pointer;
  font: inherit;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.filter-chip:hover { border-color: var(--jf-primary); }
.filter-chip.active {
  border-color: var(--jf-primary);
  background: var(--jf-primary-softer, #eef4ff);
}
.filter-chip b { font-size: 14px; color: var(--jf-ink); }
.chip-label { font-size: 13px; color: var(--jf-ink-soft, #606266); }
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }
.status-group {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  overflow: hidden;
}
.group-head {
  display: flex; align-items: center; gap: 9px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--jf-border);
  background: var(--jf-bg, #f7f8fa);
}
.group-title { font-weight: 600; font-size: 14px; color: var(--jf-ink); }
.group-count {
  font-size: 12px; color: var(--jf-muted);
  background: var(--jf-surface); border-radius: 999px; padding: 1px 9px;
}
.card-list { padding: 10px 16px; display: flex; flex-direction: column; }
.app-card {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  width: 100%; text-align: left;
  padding: 12px 14px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--jf-border);
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.app-card:last-child { border-bottom: none; }
.app-card:hover { background: var(--jf-bg, #f7f8fa); }
.card-main { min-width: 0; }
.card-title { font-weight: 600; font-size: 14px; color: var(--jf-ink); }
.card-company { color: var(--jf-muted); font-size: 12px; margin-top: 3px; }
.card-side { display: flex; align-items: center; gap: 12px; flex: 0 0 auto; }
.meta-chip {
  font-size: 12px; color: var(--jf-primary);
  background: var(--jf-primary-softer, #eef4ff);
  border-radius: 6px; padding: 2px 8px;
}
.meta-time { font-size: 12px; color: var(--jf-muted); }
.group-empty { padding: 22px 16px; text-align: center; color: var(--jf-muted); font-size: 13px; }
.transition-btns { display: flex; flex-wrap: wrap; gap: 8px; }
.end-tip { font-size: 13px; color: var(--jf-muted); }
.event-item { font-size: 13px; }
.event-tag { margin-left: 8px; }
.event-comment { font-size: 12px; color: var(--jf-muted); margin-top: 4px; }
</style>
