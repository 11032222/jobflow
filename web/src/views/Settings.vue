<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><span>👤 账号信息</span></template>
          <el-form :model="userForm" label-width="80px" style="max-width: 400px">
            <el-form-item label="用户名"><el-input :model-value="store.user?.username" disabled /></el-form-item>
            <el-form-item label="真实姓名"><el-input v-model="userForm.real_name" /></el-form-item>
            <el-form-item label="邮箱"><el-input v-model="userForm.email" /></el-form-item>
            <el-form-item label="手机号"><el-input v-model="userForm.phone" /></el-form-item>
            <el-button type="primary" :loading="saving" @click="handleSave">保存信息</el-button>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header><span>📮 投递演示设置</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="投递模式">
              <el-tag type="success" size="small">{{ mailModeText }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="SMTP 服务器">{{ smtpHost || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发件邮箱">{{ smtpUser || '-' }}</el-descriptions-item>
            <el-descriptions-item label="演示收件箱">
              <b>{{ demoInbox || '-' }}</b>
            </el-descriptions-item>
          </el-descriptions>
          <el-alert
            type="success"
            :closable="false"
            show-icon
            title="所有投递邮件将发送至演示收件箱。SMTP 配置在 api/.env 中维护，修改后需重启后端。"
            style="margin-top: 12px"
          />
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>🧠 模型服务（LLM）</span>
              <el-tag size="small" :type="modelStatus.ok ? 'success' : 'info'">
                {{ modelStatus.ok ? `已启用 ${modelForm.model || ''}` : '未配置' }}
              </el-tag>
            </div>
          </template>
          <el-form :model="modelForm" label-width="90px" size="default">
            <el-form-item label="服务预设">
              <el-select v-model="preset" style="width: 100%" @change="applyPreset">
                <el-option label="通义千问（DashScope）" value="qwen" />
                <el-option label="智谱 GLM" value="glm" />
                <el-option label="DeepSeek" value="deepseek" />
                <el-option label="OpenAI" value="openai" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
            <el-form-item label="协议">
              <el-select v-model="modelForm.protocol" style="width: 100%">
                <el-option label="OpenAI 兼容协议" value="openai-compatible" />
              </el-select>
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="modelForm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="modelForm.api_key" type="password" show-password :placeholder="modelForm.api_key_masked ? `已配置 ${modelForm.api_key_masked}，留空则保持不变` : 'sk-...'" />
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="modelForm.model" placeholder="qwen-plus" />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="modelForm.enabled" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingModel" @click="handleSaveModel">保存配置</el-button>
              <el-button :loading="testingModel" @click="handleTestModel">测试连接</el-button>
            </el-form-item>
            <el-alert
              v-if="modelTestResult"
              :type="modelTestResult.ok ? 'success' : 'error'"
              :closable="false"
              show-icon
              :title="modelTestResult.ok ? `连接成功（${modelTestResult.latency_ms}ms）：${modelTestResult.reply}` : `连接失败：${modelTestResult.error}`"
            />
          </el-form>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="配置后可解锁：简历解析（Resume Agent）、岗位匹配推荐理由（Matching Agent）、简历修改建议。未配置时自动使用规则引擎。"
            style="margin-top: 8px"
          />
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header><span>⚙️ 系统状态</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="数据库">
              <el-tag size="small" :type="status.database === 'mysql' ? 'success' : 'warning'">
                {{ status.database === 'mysql' ? 'MySQL' : 'SQLite（开发库）' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="LLM 引擎">
              <el-tag size="small" :type="status.llm_available ? 'success' : 'info'">
                {{ status.llm_available ? `已接入（${status.llm_model}）` : '未配置（规则引擎模式）' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="匹配/解析引擎">
              {{ status.llm_available ? 'LLM Agent + 规则引擎' : '规则引擎' }}
            </el-descriptions-item>
          </el-descriptions>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="在 .env 中配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL 后重启后端即可启用 LLM Agent（支持通义千问、GLM-4 等 OpenAI 兼容接口）。"
            style="margin-top: 12px"
          />
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header><span>ℹ️ 关于 JobFlow</span></template>
          <p style="color: #606266; line-height: 1.8; font-size: 14px">
            JobFlow 是一款面向求职者的桌面端智能求职辅助系统：上传简历建立求职画像 → 从平台发现岗位 → 匹配分析 → 邮箱投递简历 → 看板跟踪投递状态 → 面试管理，形成完整求职闭环。
          </p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getMe, getModelConfig, getSystemStatus, saveModelConfig, testModelConfig, updateUser } from '@/api'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const saving = ref(false)
const userForm = reactive({ real_name: '', email: '', phone: '' })
const status = ref({ database: '', llm_available: false, llm_model: null })

const modelForm = reactive({
  protocol: 'openai-compatible', api_key: '', api_key_masked: '',
  base_url: '', model: 'qwen-plus', enabled: true,
})
const preset = ref('qwen')
const savingModel = ref(false)
const testingModel = ref(false)
const modelTestResult = ref(null)

const PRESETS = {
  qwen: { base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  glm: { base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash' },
  deepseek: { base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  custom: { base_url: '', model: '' },
}

const modelStatus = computed(() => ({
  ok: status.value.llm_available,
}))

function applyPreset() {
  const p = PRESETS[preset.value]
  if (p) {
    modelForm.base_url = p.base_url
    modelForm.model = p.model
  }
}

const mailModeText = computed(() => ({ smtp: 'SMTP 真实邮箱', mailhog: 'MailHog 本地邮箱', mock: 'Mock 模拟' })[import.meta.env.VITE_MAIL_MODE || 'smtp'] || 'smtp')
const smtpHost = import.meta.env.VITE_SMTP_HOST || 'smtp.qq.com（api/.env）'
const smtpUser = import.meta.env.VITE_SMTP_USER || '2174935034@qq.com（api/.env）'
const demoInbox = import.meta.env.VITE_DEMO_INBOX || '2174935034@qq.com（api/.env）'

async function handleSaveModel() {
  savingModel.value = true
  try {
    const data = await saveModelConfig({
      protocol: modelForm.protocol,
      api_key: modelForm.api_key,
      base_url: modelForm.base_url,
      model: modelForm.model,
      enabled: modelForm.enabled,
    })
    Object.assign(modelForm, data)
    ElMessage.success('模型配置已保存')
    await load()
  } finally {
    savingModel.value = false
  }
}

async function handleTestModel() {
  if (!modelForm.base_url || (!modelForm.api_key && !modelForm.api_key_masked)) {
    ElMessage.warning('请填写 Base URL 与 API Key')
    return
  }
  testingModel.value = true
  try {
    modelTestResult.value = await testModelConfig({
      protocol: modelForm.protocol,
      api_key: modelForm.api_key || modelForm.api_key_masked,
      base_url: modelForm.base_url,
      model: modelForm.model,
      enabled: true,
    })
  } finally {
    testingModel.value = false
  }
}

async function load() {
  const me = await getMe()
  Object.assign(userForm, { real_name: me.real_name || '', email: me.email || '', phone: me.phone || '' })
  store.setAuth(store.token, { id: me.id, username: me.username, real_name: me.real_name })
  try {
    status.value = await getSystemStatus()
  } catch { /* 忽略 */ }
  try {
    const cfg = await getModelConfig()
    Object.assign(modelForm, cfg)
  } catch { /* 忽略 */ }
}

async function handleSave() {
  saving.value = true
  try {
    await updateUser({ ...userForm })
    ElMessage.success('账号信息已保存')
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
