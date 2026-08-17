<template>
  <div class="login-page">
    <el-card class="login-card">
      <div class="login-logo">
        <el-icon :size="40" color="#409eff"><Briefcase /></el-icon>
        <h1>JobFlow</h1>
        <p>智能求职辅助系统</p>
      </div>
      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" size="large" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="handleLogin">
              登录
            </el-button>
          </el-form>
          <el-alert type="info" :closable="false" style="margin-top: 12px" title="演示账号：admin / 123456" />
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名（至少3位）" size="large" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.password" type="password" placeholder="密码（至少6位）" size="large" :prefix-icon="Lock" show-password />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.real_name" placeholder="真实姓名（可选）" size="large" :prefix-icon="Postcard" />
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="handleRegister">
              注册并登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Briefcase, Lock, Postcard, User } from '@element-plus/icons-vue'
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
    ElMessage.success('登录成功')
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
    ElMessage.success('注册成功')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f3b73 0%, #409eff 100%);
}
.login-card {
  width: 420px;
  border-radius: 12px;
}
.login-logo {
  text-align: center;
  margin-bottom: 12px;
}
.login-logo h1 {
  font-size: 28px;
  color: #303133;
  margin-top: 4px;
}
.login-logo p {
  color: #909399;
  font-size: 14px;
  margin-top: 4px;
}
</style>
