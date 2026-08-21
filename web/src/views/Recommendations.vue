<template>
  <div>
    <section class="panel">
      <header class="panel-header">
        <span class="panel-title"><el-icon><TrendCharts /></el-icon>推荐岗位</span>
        <el-button type="primary" size="small" :icon="Refresh" :loading="refreshing" @click="load">重新计算</el-button>
      </header>

      <div v-if="items.length" class="rec-list">
        <div v-for="item in items" :key="item.id" class="rec-item hoverable" @click="$router.push(`/jobs/${item.id}`)">
          <div class="rec-rank">
            <div class="score-badge" :class="levelClass(item.match?.recommend_level)">{{ item.match?.match_score != null ? Math.round(Number(item.match.match_score)) : '-' }}</div>
            <el-tag :type="levelType(item.match?.recommend_level)" size="small" effect="plain" class="level-tag">{{ item.match?.recommend_level ?? '-' }}</el-tag>
          </div>
          <div class="rec-body">
            <div class="rec-title-row">
              <b class="rec-title">{{ item.title }}</b>
              <span class="rec-company">{{ item.company_name }}</span>
              <span class="rec-city"><el-icon><Location /></el-icon>{{ item.city }}</span>
              <span class="salary-text rec-salary">{{ item.salary_text }}</span>
            </div>
            <div class="rec-reason">
              <el-tag v-if="item.match?.hard_fail" type="danger" size="small" effect="plain" style="margin-right: 6px">硬性不符</el-tag>
              {{ item.match?.recommend_reason }}
            </div>
            <div class="rec-tags">
              <el-tag v-for="t in item.tags?.slice(0, 5)" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
            </div>
          </div>
          <div class="rec-actions">
            <el-tag v-if="item.is_applied" type="success" effect="plain" size="small">已投递</el-tag>
            <el-button v-else size="small" type="primary" @click.stop="$router.push(`/jobs/${item.id}`)">查看</el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无推荐结果，请先完善简历画像" :image-size="100" />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Location, Refresh, TrendCharts } from '@element-plus/icons-vue'
import { getRecommendations } from '@/api'

const items = ref([])
const refreshing = ref(false)

function levelType(level) {
  return { S: 'danger', A: 'warning', B: 'primary', C: 'info', D: 'info' }[level] || 'info'
}
function levelClass(level) {
  return { S: 'level-s', A: 'level-a', B: 'level-b', C: 'level-c', D: 'level-d' }[level] || 'level-d'
}

async function load() {
  refreshing.value = true
  try {
    items.value = (await getRecommendations({ limit: 50 })).items
  } finally {
    refreshing.value = false
  }
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
.rec-list { margin-top: 8px; }
.rec-item {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 12px;
  border-bottom: 1px solid var(--jf-border);
  border-radius: 10px;
}
.rec-item:last-child { border-bottom: none; }
.rec-rank { width: 60px; text-align: center; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.score-badge {
  width: 52px; height: 52px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 800; color: #fff;
}
.level-s { background: #dc2626; }
.level-a { background: #ea580c; }
.level-b { background: #0d9488; }
.level-c { background: #94a3b8; }
.level-d { background: #cbd5e1; }
.level-tag { margin: 0; }

.rec-body { flex: 1; min-width: 0; }
.rec-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rec-title { font-size: 16px; color: var(--jf-ink); }
.rec-company { color: var(--jf-ink-soft); font-size: 14px; }
.rec-city { color: var(--jf-muted); font-size: 13px; display: inline-flex; align-items: center; gap: 2px; }
.rec-salary { font-size: 14px; }
.rec-reason { color: var(--jf-ink-soft); font-size: 13px; margin-top: 6px; line-height: 1.7; }
.rec-tags { margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
.rec-actions { flex-shrink: 0; }
</style>