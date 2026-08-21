<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark"><el-icon :size="20"><Briefcase /></el-icon></div>
        <div class="brand-text">
          <span class="brand-name">JobFlow</span>
          <span class="brand-sub">智能求职工作台</span>
        </div>
      </div>

      <nav class="nav">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item" :class="{ active: isActive(item.path) }">
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-user">
        <button class="user-trigger" type="button" @click="userMenuOpen = !userMenuOpen">
          <el-avatar :size="34" class="user-avatar">{{ store.displayName[0] }}</el-avatar>
          <div class="user-meta">
            <span class="user-name">{{ store.displayName }}</span>
            <span class="user-role">求职者</span>
          </div>
          <el-icon class="caret" :class="{ open: userMenuOpen }"><ArrowDown /></el-icon>
        </button>

        <div v-if="userMenuOpen" class="user-menu-backdrop" @click="userMenuOpen = false"></div>
        <Transition name="user-card">
          <div v-if="userMenuOpen" class="user-card" role="menu" aria-label="用户菜单">
            <div class="user-card-head">
              <el-avatar :size="30" class="user-avatar">{{ store.displayName[0] }}</el-avatar>
              <div class="user-meta">
                <span class="user-name">{{ store.displayName }}</span>
                <span class="user-role">求职者</span>
              </div>
            </div>
            <div class="user-card-items">
              <button class="user-card-item" type="button" role="menuitem" @click="openSettings">
                <el-icon :size="16"><Setting /></el-icon>
                <span>设置</span>
              </button>
              <button class="user-card-item danger" type="button" role="menuitem" @click="handleLogout">
                <el-icon :size="16"><SwitchButton /></el-icon>
                <span>退出登录</span>
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </aside>

    <section class="main">
      <header class="topbar">
        <div>
          <div class="page-title">{{ pageTitle }}</div>
          <div class="page-sub">{{ pageSub }}</div>
        </div>
        <div class="user-info">
          <el-avatar :size="32" class="user-avatar">{{ store.displayName[0] }}</el-avatar>
          <span class="user-name">{{ store.displayName }}</span>
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </section>

    <div v-if="settingsOpen" class="settings-overlay" tabindex="-1" @keydown.esc="settingsOpen = false" @click.self="settingsOpen = false">
      <div class="settings-popup" role="dialog" aria-modal="true" aria-label="设置">
        <header class="settings-popup-head">
          <div>
            <h2>设置</h2>
            <p>账号、模型与系统配置</p>
          </div>
          <button class="popup-close" type="button" @click="settingsOpen = false" aria-label="关闭设置">
            <el-icon :size="18"><Close /></el-icon>
          </button>
        </header>
        <div class="settings-popup-body">
          <SettingsPanel />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  ArrowDown, Briefcase, Calendar, Close, Cpu, Document, Odometer,
  Promotion, Search, Setting, Star, SwitchButton,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import SettingsPanel from '@/views/Settings.vue'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const userMenuOpen = ref(false)
const settingsOpen = ref(false)

const navItems = [
  { path: '/dashboard', label: '工作台', icon: Odometer },
  { path: '/resumes', label: '简历管理', icon: Document },
  { path: '/jobs', label: '岗位库', icon: Search },
  { path: '/recommendations', label: '智能推荐', icon: Star },
  { path: '/applications', label: '投递看板', icon: Promotion },
  { path: '/interviews', label: '面试管理', icon: Calendar },
  { path: '/tasks', label: '任务中心', icon: Cpu },
]

const pageSubs = {
  '/dashboard': '求职进展一览',
  '/resumes': '简历、求职画像与偏好',
  '/jobs': '多平台岗位采集与筛选',
  '/recommendations': '基于画像的智能匹配',
  '/applications': '投递状态跟踪',
  '/interviews': '面试日程与记录',
  '/tasks': 'Agent 任务执行情况',
  '/settings': '账号、模型与系统配置',
}

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta.title || 'JobFlow')
const pageSub = computed(() => pageSubs[route.path] || '智能求职辅助系统')

function isActive(path) {
  if (path === '/jobs') return activeMenu.value.startsWith('/jobs')
  return activeMenu.value === path
}

function openSettings() {
  userMenuOpen.value = false
  settingsOpen.value = true
}

async function handleLogout() {
  userMenuOpen.value = false
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '退出确认', { type: 'warning', confirmButtonText: '退出', cancelButtonText: '取消' })
    store.logout()
    router.push('/login')
  } catch {
    /* 用户取消 */
  }
}
</script>

<style scoped>
.shell {
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 236px;
  flex-shrink: 0;
  background: var(--jf-surface);
  border-right: 1px solid var(--jf-border);
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 18px 16px;
}
.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--jf-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-text { display: flex; flex-direction: column; line-height: 1.2; }
.brand-name { font-size: 18px; font-weight: 800; color: var(--jf-ink); letter-spacing: 0.2px; }
.brand-sub { font-size: 11px; color: var(--jf-muted); margin-top: 2px; }

.nav {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 9px;
  color: var(--jf-ink-soft);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.18s ease;
  position: relative;
}
.nav-item:hover { background: var(--jf-primary-softer); color: var(--jf-primary-dark); }
.nav-item.active {
  background: var(--jf-primary-soft);
  color: var(--jf-primary-darker);
  font-weight: 600;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--jf-primary);
}

.sidebar-user {
  position: relative;
  margin: 12px;
  padding: 6px;
  border: 1px solid var(--jf-border);
  border-radius: 12px;
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 4px;
  border: none;
  border-radius: 9px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: background 0.18s ease;
}
.user-trigger:hover { background: var(--jf-primary-softer); }
.user-avatar { background: var(--jf-primary); color: #fff; font-weight: 600; flex-shrink: 0; }
.user-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: 1.25; }
.user-name { font-size: 13px; font-weight: 600; color: var(--jf-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-role { font-size: 11px; color: var(--jf-muted); }
.caret { color: var(--jf-muted); font-size: 12px; transition: transform 0.2s ease; }
.caret.open { transform: rotate(180deg); }

.user-menu-backdrop { position: fixed; inset: 0; z-index: 2400; }
.user-card {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 2401;
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.16);
  padding: 8px;
}
.user-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 10px;
  border-bottom: 1px solid var(--jf-border);
  margin-bottom: 6px;
}
.user-card-items { display: flex; flex-direction: column; gap: 2px; }
.user-card-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--jf-ink-soft);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
  font-family: inherit;
}
.user-card-item:hover { background: var(--jf-primary-softer); color: var(--jf-primary-darker); }
.user-card-item.danger:hover { background: #fff1f0; color: var(--jf-danger, #ef4444); }

.user-card-enter-active,
.user-card-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.user-card-enter-from,
.user-card-leave-to { opacity: 0; transform: translateY(6px); }

.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }

.topbar {
  height: 64px;
  flex-shrink: 0;
  background: var(--jf-surface);
  border-bottom: 1px solid var(--jf-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.topbar .page-title { font-size: 17px; }
.user-info { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 10px; }
.user-info .user-name { font-size: 14px; font-weight: 600; color: var(--jf-ink); }

.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.settings-overlay {
  position: fixed;
  inset: 0;
  z-index: 1500;
  background: rgba(15, 23, 42, 0.36);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.settings-popup {
  width: min(980px, calc(100vw - 24px));
  height: min(680px, calc(100vh - 128px));
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: settings-popup-in 0.22s ease;
}
@keyframes settings-popup-in {
  from { opacity: 0; transform: translateY(10px) scale(0.99); }
  to { opacity: 1; transform: none; }
}
.settings-popup-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--jf-border);
  background: var(--jf-surface);
}
.settings-popup-head h2 { font-size: 16px; font-weight: 700; color: var(--jf-ink); }
.settings-popup-head p { font-size: 12px; color: var(--jf-muted); margin-top: 2px; }
.popup-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--jf-border);
  border-radius: 8px;
  background: var(--jf-surface);
  color: var(--jf-muted);
  cursor: pointer;
  transition: all 0.18s ease;
}
.popup-close:hover { border-color: var(--jf-primary); color: var(--jf-primary-darker); background: var(--jf-primary-softer); }

.settings-popup-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
}
</style>