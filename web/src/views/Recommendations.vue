<template>
  <div>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="推荐基于求职画像与偏好，通过匹配引擎计算得出。完善画像可获得更精准的推荐。"
      style="margin-bottom: 16px"
    />

    <el-card>
      <template #header>
        <div class="card-header">
          <span>💡 推荐岗位</span>
          <el-button type="primary" size="small" :loading="refreshing" @click="load">重新计算</el-button>
        </div>
      </template>

      <div v-for="item in items" :key="item.id" class="rec-item" @click="$router.push(`/jobs/${item.id}`)">
        <div class="rec-rank">
          <div class="rec-score">{{ item.match?.match_score ?? '-' }}</div>
          <el-tag :type="levelType(item.match?.recommend_level)" size="small">{{ item.match?.recommend_level ?? '-' }}</el-tag>
        </div>
        <div class="rec-body">
          <div class="rec-title-row">
            <b class="rec-title">{{ item.title }}</b>
            <span class="rec-company">{{ item.company_name }}</span>
            <span class="rec-city">{{ item.city }}</span>
            <span class="rec-salary">{{ item.salary_text }}</span>
          </div>
          <div class="rec-reason">{{ item.match?.recommend_reason }}</div>
          <div class="rec-tags">
            <el-tag v-for="t in item.tags?.slice(0, 5)" :key="t" size="small" type="info" effect="plain">{{ t }}</el-tag>
          </div>
        </div>
        <div class="rec-actions">
          <el-tag v-if="item.is_applied" type="success" effect="plain" size="small">已投递</el-tag>
          <el-button v-else size="small" type="primary" @click.stop="$router.push(`/jobs/${item.id}`)">查看</el-button>
        </div>
      </div>

      <el-empty v-if="!items.length" description="暂无推荐结果" :image-size="100" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getRecommendations } from '@/api'

const items = ref([])
const refreshing = ref(false)

function levelType(level) {
  return { S: 'danger', A: 'warning', B: 'primary', C: 'info', D: 'info' }[level] || 'info'
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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.rec-item {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 8px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: background 0.2s;
}
.rec-item:hover {
  background: #f7fafc;
}
.rec-rank {
  width: 64px;
  text-align: center;
  flex-shrink: 0;
}
.rec-score {
  font-size: 28px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.2;
}
.rec-body {
  flex: 1;
  min-width: 0;
}
.rec-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.rec-title {
  font-size: 16px;
  color: #303133;
}
.rec-company {
  color: #606266;
  font-size: 14px;
}
.rec-city {
  color: #909399;
  font-size: 13px;
}
.rec-salary {
  color: #f56c6c;
  font-weight: 600;
}
.rec-reason {
  color: #606266;
  font-size: 13px;
  margin-top: 6px;
  line-height: 1.6;
}
.rec-tags {
  margin-top: 6px;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.rec-actions {
  flex-shrink: 0;
}
</style>
