<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" class="layout-aside">
      <div class="logo">
        <el-icon :size="26" color="#409eff"><Briefcase /></el-icon>
        <span>JobFlow</span>
      </div>
      <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#c0c4cc" active-text-color="#ffffff">
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon><span>工作台</span>
        </el-menu-item>
        <el-menu-item index="/resumes">
          <el-icon><Document /></el-icon><span>简历管理</span>
        </el-menu-item>
        <el-menu-item index="/jobs">
          <el-icon><Search /></el-icon><span>岗位库</span>
        </el-menu-item>
        <el-menu-item index="/recommendations">
          <el-icon><Star /></el-icon><span>智能推荐</span>
        </el-menu-item>
        <el-menu-item index="/applications">
          <el-icon><Promotion /></el-icon><span>投递看板</span>
        </el-menu-item>
        <el-menu-item index="/interviews">
          <el-icon><Calendar /></el-icon><span>面试管理</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Cpu /></el-icon><span>任务中心</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon><span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-title">{{ pageTitle }}</div>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-avatar :size="32" style="background: #409eff">{{ store.displayName[0] }}</el-avatar>
            <span class="user-name">{{ store.displayName }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="settings">个人设置</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  ArrowDown, Briefcase, Calendar, Cpu, DataBoard, Document,
  Promotion, Search, Setting, Star,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta.title || 'JobFlow')

async function handleCommand(command) {
  if (command === 'settings') {
    router.push('/settings')
  } else if (command === 'logout') {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    store.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-aside {
  background: #001529;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.layout-aside :deep(.el-menu) {
  border-right: none;
  flex: 1;
}
.layout-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 1;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.user-name {
  font-size: 14px;
  color: #303133;
}
.layout-main {
  overflow-y: auto;
  padding: 16px;
}
</style>
