<template>
  <div class="login-page">
    <div class="login-shell">
      <aside class="brand-panel">
        <div class="brand">
          <div class="brand-mark"><el-icon :size="26"><Briefcase /></el-icon></div>
          <div class="brand-text">
            <span class="brand-name">JobFlow</span>
            <span class="brand-sub">智能求职辅助系统</span>
          </div>
        </div>
        <h2 class="slogan">让求职变得<br>更聪明、更高效</h2>
        <p class="intro">从简历到 Offer 的一站式求职工作台</p>
        <ul class="features">
          <li><span class="feat-icon"><el-icon><Document /></el-icon></span><div><b>智能简历解析</b><small>LLM 提取画像，自动生成求职档案</small></div></li>
          <li><span class="feat-icon"><el-icon><DataAnalysis /></el-icon></span><div><b>多维岗位匹配</b><small>技能 / 经历 / 学历 / 偏好综合评分</small></div></li>
          <li><span class="feat-icon"><el-icon><Promotion /></el-icon></span><div><b>投递全流程跟踪</b><small>邮件投递、看板状态、面试管理</small></div></li>
        </ul>
      </aside>

      <section class="form-panel">
        <div class="tabs">
          <button class="tab-btn" :class="{ active: tab === 'login' }" @click="tab = 'login'">登录</button>
          <button class="tab-btn" :class="{ active: tab === 'register' }" @click="tab = 'register'">注册</button>
        </div>

        <el-form v-if="tab === 'login'" :model="loginForm" @submit.prevent="handleLogin" class="auth-form">
          <el-form-item>
            <el-input v-model="loginForm.username" placeholder="用户名" size="large" :prefix-icon="User" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
          </el-form-item>
          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
          <div class="demo-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>演示账号：admin / 123456</span>
          </div>
        </el-form>

        <el-form v-else :model="regForm" @submit.prevent="handleRegister" class="auth-form">
          <el-form-item>
            <el-input v-model="regForm.username" placeholder="用户名（至少 3 位）" size="large" :prefix-icon="User" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="regForm.password" type="password" placeholder="密码（至少 6 位）" size="large" :prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item>
            <el-input v-model="regForm.real_name" placeholder="真实姓名（可选）" size="large" :prefix-icon="Postcard" />
          </el-form-item>
          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleRegister">
            注册并登录
          </el-button>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Briefcase, DataAnalysis, Document, InfoFilled, Lock, Postcard, Promotion, User } from '@element-plus/icons-vue'
import { login, register } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const store = useUserStore()

const tab = ref('login')
const loading = ref(false)
const loginForm = reactive({ username: 'admin', password: '123456' })
const regForm = reactive({ username: '', password: '', real_name: '' })

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await login(loginForm)
    store.setAuth(data.access_token, { id: data.user_id, username: data.username })
    ElMessage.success('登录成功，欢迎回来！')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!regForm.username || !regForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await register(regForm)
    store.setAuth(data.access_token, { id: data.user_id, username: data.username })
    ElMessage.success('注册成功，开始使用 JobFlow！')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--jf-bg);
  padding: 24px;
}
.login-shell {
  width: 880px;
  max-width: 100%;
  min-height: 560px;
  display: flex;
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: 18px;
  overflow: hidden;
}
.brand-panel {
  width: 46%;
  background: var(--jf-primary-darker);
  color: #fff;
  padding: 36px 32px;
  display: flex;
  flex-direction: column;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark {
  width: 44px; height: 44px; border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  display: flex; align-items: center; justify-content: center;
}
.brand-text { display: flex; flex-direction: column; line-height: 1.2; }
.brand-name { font-size: 20px; font-weight: 800; }
.brand-sub { font-size: 12px; opacity: 0.75; margin-top: 2px; }
.slogan { font-size: 26px; font-weight: 800; line-height: 1.35; margin-top: 44px; }
.intro { font-size: 13px; opacity: 0.75; margin-top: 12px; }
.features { list-style: none; margin-top: 36px; display: flex; flex-direction: column; gap: 18px; }
.features li { display: flex; gap: 12px; align-items: flex-start; }
.feat-icon {
  width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
  background: rgba(255, 255, 255, 0.14);
  display: flex; align-items: center; justify-content: center;
}
.features b { font-size: 14px; display: block; }
.features small { font-size: 12px; opacity: 0.72; line-height: 1.5; display: block; margin-top: 2px; }

.form-panel { flex: 1; padding: 40px 44px; display: flex; flex-direction: column; justify-content: center; }
.tabs {
  display: inline-flex;
  background: var(--jf-primary-softer);
  border: 1px solid var(--jf-border);
  border-radius: 10px;
  padding: 4px;
  align-self: flex-start;
  margin-bottom: 28px;
}
.tab-btn {
  border: none;
  background: transparent;
  padding: 8px 26px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--jf-ink-soft);
  cursor: pointer;
  transition: all 0.18s ease;
}
.tab-btn.active { background: var(--jf-surface); color: var(--jf-primary-dark); box-shadow: 0 1px 2px rgba(15, 118, 110, 0.12); }
.auth-form :deep(.el-form-item) { margin-bottom: 18px; }
.submit-btn { width: 100%; margin-top: 6px; font-weight: 600; letter-spacing: 4px; }
.demo-hint {
  margin-top: 16px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--jf-primary-softer);
  border: 1px solid var(--jf-border);
  color: var(--jf-ink-soft);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.demo-hint .el-icon { color: var(--jf-primary); }
</style>