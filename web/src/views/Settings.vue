<template>
  <div class="codex-settings">
    <!-- 左侧分类导航 -->
    <aside class="settings-nav">
      <div class="search-box">
        <el-icon class="search-icon"><Search /></el-icon>
        <input v-model="searchQuery" class="search-input" placeholder="搜索设置" />
      </div>
      <div class="nav-list">
        <button
          v-for="cat in filteredCategories"
          :key="cat.id"
          class="nav-item"
          :class="{ active: section === cat.id }"
          @click="section = cat.id"
        >
          <el-icon :size="16"><component :is="cat.icon" /></el-icon>
          <span>{{ cat.label }}</span>
        </button>
      </div>
      <div v-if="!filteredCategories.length" class="nav-empty">无匹配分类</div>
    </aside>

    <!-- 右侧设置面板 -->
    <section class="settings-content">
      <!-- ===== 常规 ===== -->
      <template v-if="section === 'general'">
        <header class="content-head">
          <h2>常规</h2>
          <p>账号信息与投递演示设置</p>
        </header>

        <div class="settings-block">
          <h3 class="block-title">账号信息</h3>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">用户名</span><span class="row-desc">登录账号，不可修改</span></div>
            <el-input :model-value="store.user?.username" disabled class="row-control" />
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">真实姓名</span><span class="row-desc">用于简历与投递邮件署名</span></div>
            <el-input v-model="userForm.real_name" class="row-control" placeholder="请输入真实姓名" />
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">邮箱</span><span class="row-desc">接收投递相关通知</span></div>
            <el-input v-model="userForm.email" class="row-control" placeholder="you@example.com" />
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">手机号</span><span class="row-desc">招聘方联系方式</span></div>
            <el-input v-model="userForm.phone" class="row-control" placeholder="请输入手机号" />
          </div>
          <div class="setting-row actions-row">
            <div class="row-info"><span class="row-label">保存</span><span class="row-desc">保存以上账号修改</span></div>
            <el-button type="primary" :loading="saving" @click="handleSave">保存信息</el-button>
          </div>
        </div>

        <div class="settings-block">
          <h3 class="block-title">投递演示</h3>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">投递模式</span><span class="row-desc">邮件发送方式</span></div>
            <el-tag type="success" size="default">{{ mailModeText }}</el-tag>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">SMTP 服务器</span><span class="row-desc">api/.env 中配置</span></div>
            <span class="row-value">{{ smtpHost || '-' }}</span>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">发件邮箱</span><span class="row-desc">投递邮件发件人</span></div>
            <span class="row-value">{{ smtpUser || '-' }}</span>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">演示收件箱</span><span class="row-desc">所有投递邮件将发送到此邮箱</span></div>
            <b class="row-value">{{ demoInbox || '-' }}</b>
          </div>
          <el-alert
            type="success"
            :closable="false"
            show-icon
            title="所有投递邮件将发送至演示收件箱。SMTP 配置在 api/.env 中维护，修改后需重启后端。"
          />
        </div>
      </template>

                  <!-- ===== 模型服务 ===== -->
      <template v-else-if="section === 'model'">
        <header class="content-head">
          <div class="head-row">
            <div>
              <h2>模型服务</h2>
              <p>配置大模型，解锁简历解析与智能匹配</p>
            </div>
            <div class="status-pill" :class="modelStatus.ok ? 'online' : 'offline'">
              <span class="status-dot"></span>
              <span>{{ modelStatus.ok ? `已启用 ${modelForm.model || ''}` : '未配置 · 规则引擎' }}</span>
            </div>
          </div>
        </header>

        <div class="model-panel">
          <div class="panel-head">
            <div>
              <h3>我的模型配置</h3>
              <p>可保存多套，随时切换当前使用</p>
            </div>
            <el-button size="small" type="primary" plain :icon="Plus" @click="resetForm">新建配置</el-button>
          </div>

          <div v-if="configs.length" class="model-configs">
            <div
              v-for="cfg in configs"
              :key="cfg.id"
              class="model-config"
              :class="{ active: cfg.is_active, editing: editingId === cfg.id }"
              @click="editConfig(cfg)"
            >
              <span class="cfg-badge" :style="{ background: providerColor(cfg) }">{{ providerShort(cfg) }}</span>
              <div class="cfg-info">
                <div class="cfg-title">
                  <span class="cfg-name">{{ cfg.name || '模型配置' }}</span>
                  <span v-if="cfg.is_active" class="cfg-active-badge">
                    <el-icon :size="12"><CircleCheckFilled /></el-icon>
                    使用中
                  </span>
                </div>
                <div class="cfg-sub">
                  <span>{{ providerLabel(cfg) }}</span>
                  <span class="cfg-dot"></span>
                  <span class="cfg-model">{{ cfg.model }}</span>
                </div>
              </div>
              <div class="cfg-actions" @click.stop>
                <el-button v-if="!cfg.is_active" size="small" text type="primary" @click="handleActivate(cfg.id)">设为当前</el-button>
                <el-button size="small" text :loading="testingConfigId === cfg.id" @click="handleTestConfig(cfg)">测试</el-button>
                <el-tooltip content="编辑" placement="top">
                  <el-button size="small" text circle :icon="EditPen" @click="editConfig(cfg)" aria-label="编辑配置" />
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button size="small" text circle type="danger" :icon="Delete" @click="handleDeleteConfig(cfg)" aria-label="删除配置" />
                </el-tooltip>
              </div>
            </div>
          </div>
          <div v-else class="config-empty">
            <el-icon :size="30"><DataAnalysis /></el-icon>
            <p>还没有模型配置，点击右上角「新建配置」开始</p>
          </div>
        </div>

        <div class="model-panel">
          <div class="panel-head">
            <div>
              <h3>{{ editingId ? '配置详情' : '新建配置' }}</h3>
              <p>{{ editingId ? '修改后保存即可生效' : '选择服务商并填写连接信息' }}</p>
            </div>
            <el-tag v-if="editingId && isEditingActive" type="success" effect="plain" size="small">当前使用</el-tag>
          </div>

          <div class="panel-body">
            <div>
              <h4 class="sub-title">服务商</h4>
              <div class="provider-grid">
                <button
                  v-for="p in providerList"
                  :key="p.id"
                  type="button"
                  class="provider-card"
                  :class="{ active: preset === p.id }"
                  @click="selectProvider(p.id)"
                >
                  <span class="provider-badge" :style="{ background: p.color }">{{ p.short }}</span>
                  <span class="provider-name">{{ p.label }}</span>
                  <span class="provider-proto">{{ p.protocolLabel }}</span>
                  <span class="provider-note">{{ p.note }}</span>
                  <el-icon v-if="preset === p.id" class="provider-check"><CircleCheckFilled /></el-icon>
                </button>
              </div>
            </div>

            <div>
              <h4 class="sub-title">连接参数</h4>
              <div class="form-grid">
                <div class="field">
                  <label>配置名称</label>
                  <el-input v-model="configName" placeholder="例如：日常-通义、深度-Claude" />
                  <span class="field-hint">方便区分多套模型</span>
                </div>
                <div class="field">
                  <label>模型名称</label>
                  <el-select
                    v-model="modelForm.model"
                    filterable
                    allow-create
                    default-first-option
                    placeholder="选择或输入模型名称"
                  >
                    <el-option v-for="m in currentModels" :key="m" :label="m" :value="m" />
                  </el-select>
                  <span class="field-hint">可选用常用模型或自定义输入</span>
                </div>
                <div class="field span-2">
                  <label>API Key</label>
                  <el-input
                    v-model="modelForm.api_key"
                    type="password"
                    show-password
                    :placeholder="modelForm.api_key_masked ? `已配置 ${modelForm.api_key_masked}，留空保持不变` : 'sk-...'"
                  />
                  <span class="field-hint">{{ modelForm.api_key_masked ? '已配置，留空保持不变' : '填入服务商提供的密钥' }}</span>
                </div>
                <div class="field span-2">
                  <label>Base URL</label>
                  <el-input v-model="modelForm.base_url" :placeholder="currentPreset.base_url || 'https://api.example.com/v1'" />
                </div>
                <div class="field">
                  <label>启用模型服务</label>
                  <el-switch v-model="modelForm.enabled" />
                  <span class="field-hint">关闭后自动使用规则引擎</span>
                </div>
              </div>
            </div>

            <div class="advanced-block">
              <el-collapse class="advanced-collapse">
                <el-collapse-item title="接口协议（默认 OpenAI 兼容协议）" name="protocol">
                  <div class="setting-row">
                    <div class="row-info"><span class="row-label">协议</span><span class="row-desc">按服务商选择对应协议，普通用户无需修改</span></div>
                    <el-select v-model="modelForm.protocol" class="row-control">
                      <el-option v-for="proto in PROTOCOLS" :key="proto.value" :label="proto.label" :value="proto.value" />
                    </el-select>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>

            <div class="editor-actions">
              <el-button type="primary" :loading="savingModel" @click="handleSaveModel">{{ editingId ? '保存修改' : '添加配置' }}</el-button>
              <el-button :loading="testingModel" @click="handleTestModel">测试连接</el-button>
              <el-button v-if="editingId && !isEditingActive" @click="handleSaveAndActivate">保存并设为当前</el-button>
            </div>
            <el-alert
              v-if="modelTestResult"
              :type="modelTestResult.ok ? 'success' : 'error'"
              :closable="false"
              show-icon
              :title="modelTestResult.ok ? `连接成功（${modelTestResult.latency_ms}ms）：${modelTestResult.reply}` : `连接失败：${modelTestResult.error}`"
            />
          </div>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="配置后可解锁：简历解析（Resume Agent）、岗位匹配推荐理由（Matching Agent）、简历修改建议。未配置时自动使用规则引擎。"
        />
      </template>

      <!-- ===== 系统 ===== --><!-- ===== 系统 ===== -->
      <template v-else-if="section === 'system'">
        <header class="content-head">
          <h2>系统</h2>
          <p>运行状态与环境信息</p>
        </header>

        <div class="settings-block">
          <div class="setting-row">
            <div class="row-info"><span class="row-label">数据库</span><span class="row-desc">当前数据存储引擎</span></div>
            <el-tag size="default" :type="status.database === 'mysql' ? 'success' : 'warning'">
              {{ status.database === 'mysql' ? 'MySQL' : 'SQLite（开发库）' }}
            </el-tag>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">LLM 引擎</span><span class="row-desc">大模型接入状态</span></div>
            <el-tag size="default" :type="status.llm_available ? 'success' : 'info'">
              {{ status.llm_available ? `已接入（${status.llm_model}）` : '未配置（规则引擎模式）' }}
            </el-tag>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">匹配 / 解析引擎</span><span class="row-desc">智能能力组合</span></div>
            <span class="row-value">{{ status.llm_available ? 'LLM Agent + 规则引擎' : '规则引擎' }}</span>
          </div>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="在 .env 中配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL 后重启后端即可启用 LLM Agent（支持通义千问、GLM-4 等 OpenAI 兼容接口）。"
          />
        </div>
      </template>

      <!-- ===== 关于 ===== -->
      <template v-else>
        <header class="content-head">
          <h2>关于</h2>
          <p>JobFlow 版本与简介</p>
        </header>

        <div class="settings-block">
          <div class="about-hero">
            <div class="about-logo"><el-icon :size="26"><Briefcase /></el-icon></div>
            <div>
              <div class="about-name">JobFlow <el-tag size="small" effect="plain">v1.1.0</el-tag></div>
              <div class="about-sub">智能求职辅助系统</div>
            </div>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">简介</span></div>
            <p class="about-text">
              上传简历建立求职画像 → 从平台发现岗位 → 匹配分析 → 邮箱投递简历 → 看板跟踪投递状态 → 面试管理，形成完整求职闭环。
            </p>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">技术栈</span><span class="row-desc">前端 / 后端 / 桌面容器</span></div>
            <span class="row-value">Vue3 · Element Plus · FastAPI · Electron</span>
          </div>
          <div class="setting-row">
            <div class="row-info"><span class="row-label">数据来源</span><span class="row-desc">平台岗位采集适配器</span></div>
            <span class="row-value">智联招聘 · BOSS直聘 · 模拟数据</span>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Briefcase, CircleCheckFilled, DataAnalysis, Delete, EditPen, InfoFilled, Monitor, Plus, Search, Setting, User } from '@element-plus/icons-vue'
import { activateModelConfig, createModelConfig, deleteModelConfig, getMe, getSystemStatus, listModelConfigs, testModelConfig, testModelConfigById, updateModelConfig, updateUser } from '@/api'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const section = ref('general')
const searchQuery = ref('')

const categories = [
  { id: 'general', label: '常规', icon: User },
  { id: 'model', label: '模型服务', icon: DataAnalysis },
  { id: 'system', label: '系统', icon: Monitor },
  { id: 'about', label: '关于', icon: InfoFilled },
]

const filteredCategories = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return categories
  return categories.filter((c) => c.label.toLowerCase().includes(q))
})

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
const configs = ref([])
const editingId = ref(null)
const testingConfigId = ref(null)
const configName = ref('模型配置')

const PROTOCOLS = [
  { value: 'openai-compatible', label: 'OpenAI 兼容协议', desc: 'Chat Completions，绝大多数服务商都支持' },
  { value: 'anthropic', label: 'Anthropic Messages 协议', desc: 'Claude 官方 /v1/messages 接口' },
  { value: 'gemini', label: 'Google Gemini 协议', desc: 'Gemini generateContent 接口' },
]

const PRESETS = {
  qwen: { protocol: 'openai-compatible', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  glm: { protocol: 'openai-compatible', base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4.6' },
  deepseek: { protocol: 'openai-compatible', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-v4-flash' },
  openai: { protocol: 'openai-compatible', base_url: 'https://api.openai.com/v1', model: 'gpt-5.4' },
  claude: { protocol: 'anthropic', base_url: 'https://api.anthropic.com', model: 'claude-sonnet-5' },
  gemini: { protocol: 'gemini', base_url: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-3-flash' },
  kimi: { protocol: 'openai-compatible', base_url: 'https://api.moonshot.cn/v1', model: 'kimi-k3' },
  grok: { protocol: 'openai-compatible', base_url: 'https://api.x.ai/v1', model: 'grok-4' },
  mistral: { protocol: 'openai-compatible', base_url: 'https://api.mistral.ai/v1', model: 'mistral-large-latest' },
  ollama: { protocol: 'openai-compatible', base_url: 'http://localhost:11434/v1', model: 'qwen3:8b' },
  openrouter: { protocol: 'openai-compatible', base_url: 'https://openrouter.ai/api/v1', model: 'anthropic/claude-sonnet-5' },
  custom: { protocol: 'openai-compatible', base_url: '', model: '' },
}

const MODEL_OPTIONS = {
  qwen: ['qwen-plus', 'qwen-turbo', 'qwen-max', 'qwen3-max', 'qwen3-235b-a22b'],
  glm: ['glm-4.6', 'glm-4.6-flash', 'glm-4.6-long', 'glm-4.5-air', 'glm-4-flash', 'glm-4-air', 'glm-4-plus'],
  deepseek: ['deepseek-v4-flash', 'deepseek-v4-pro', 'deepseek-chat', 'deepseek-reasoner'],
  openai: ['gpt-5.4', 'gpt-5.2', 'gpt-5-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini'],
  claude: ['claude-opus-5', 'claude-sonnet-5', 'claude-haiku-4-5', 'claude-fable-5'],
  gemini: ['gemini-3-pro', 'gemini-3-flash', 'gemini-2.5-pro', 'gemini-2.5-flash'],
  kimi: ['kimi-k3', 'kimi-k2.6', 'kimi-k2.7-code'],
  grok: ['grok-4', 'grok-4-fast', 'grok-4-heavy'],
  mistral: ['mistral-large-latest', 'mistral-medium-latest', 'mistral-small-latest'],
  ollama: ['qwen3:8b', 'llama3.3:70b', 'deepseek-r1:14b', 'mistral:latest'],
  openrouter: ['anthropic/claude-sonnet-5', 'openai/gpt-5.4', 'google/gemini-3-flash', 'deepseek/deepseek-v4-flash', 'meta-llama/llama-3.3-70b-instruct'],
  custom: [],
}

const providerList = [
  { id: 'qwen', label: '通义千问', short: '通', color: 'linear-gradient(135deg,#1677ff,#0ea5e9)', note: '阿里云 DashScope', protocolLabel: 'OpenAI 兼容' },
  { id: 'glm', label: '智谱 GLM', short: 'GLM', color: 'linear-gradient(135deg,#6d28d9,#a855f7)', note: 'BigModel 开放平台', protocolLabel: 'OpenAI 兼容' },
  { id: 'deepseek', label: 'DeepSeek', short: 'DS', color: 'linear-gradient(135deg,#0f766e,#14b8a6)', note: 'DeepSeek 官方 API', protocolLabel: 'OpenAI 兼容' },
  { id: 'openai', label: 'OpenAI', short: 'OA', color: 'linear-gradient(135deg,#111827,#4b5563)', note: 'OpenAI 官方 API', protocolLabel: 'OpenAI 兼容' },
  { id: 'claude', label: 'Claude', short: 'CL', color: 'linear-gradient(135deg,#c2410c,#ea580c)', note: 'Anthropic 官方 API', protocolLabel: 'Anthropic' },
  { id: 'gemini', label: 'Gemini', short: 'GE', color: 'linear-gradient(135deg,#2563eb,#06b6d4)', note: 'Google AI Studio', protocolLabel: 'Gemini' },
  { id: 'kimi', label: 'Kimi', short: 'K2', color: 'linear-gradient(135deg,#111827,#334155)', note: 'Moonshot 月之暗面', protocolLabel: 'OpenAI 兼容' },
  { id: 'grok', label: 'Grok', short: 'X', color: 'linear-gradient(135deg,#1f2937,#6b7280)', note: 'xAI 官方 API', protocolLabel: 'OpenAI 兼容' },
  { id: 'mistral', label: 'Mistral', short: 'MI', color: 'linear-gradient(135deg,#b45309,#f59e0b)', note: 'Mistral AI', protocolLabel: 'OpenAI 兼容' },
  { id: 'ollama', label: 'Ollama', short: 'OL', color: 'linear-gradient(135deg,#047857,#10b981)', note: '本地模型，无需 Key', protocolLabel: 'OpenAI 兼容' },
  { id: 'openrouter', label: 'OpenRouter', short: 'OR', color: 'linear-gradient(135deg,#7c3aed,#a78bfa)', note: '聚合多家模型', protocolLabel: 'OpenAI 兼容' },
  { id: 'custom', label: '自定义', short: '自', color: 'linear-gradient(135deg,#ea580c,#f59e0b)', note: '任意兼容端点', protocolLabel: '自定义' },
]

const currentPreset = computed(() => PRESETS[preset.value] || PRESETS.custom)
const currentModels = computed(() => MODEL_OPTIONS[preset.value] || [])

const modelStatus = computed(() => ({
  ok: status.value.llm_available,
}))
const isEditingActive = computed(() => {
  const c = configs.value.find((x) => x.id === editingId.value)
  return c ? c.is_active : false
})

function selectProvider(id) {
  preset.value = id
  const p = PRESETS[id]
  if (p) {
    modelForm.protocol = p.protocol
    modelForm.base_url = p.base_url
    modelForm.model = p.model
  }
  modelTestResult.value = null
}

function detectPreset(cfg) {
  if (cfg.provider && PRESETS[cfg.provider]) return cfg.provider
  const url = (cfg.base_url || '').trim().replace(/\/+$/, '')
  for (const [id, p] of Object.entries(PRESETS)) {
    if (p.base_url && url === p.base_url.replace(/\/+$/, '')) return id
  }
  return 'custom'
}

function providerMeta(cfg) {
  const p = providerList.find((x) => x.id === cfg.provider)
  if (p) return p
  const detected = detectPreset(cfg)
  return providerList.find((x) => x.id === detected) || { color: 'linear-gradient(135deg,#94a3b8,#cbd5e1)', short: '自', label: '自定义' }
}
function providerColor(cfg) { return providerMeta(cfg).color }
function providerShort(cfg) { return providerMeta(cfg).short }
function providerLabel(cfg) { return providerMeta(cfg).label }

function resetForm() {
  editingId.value = null
  configName.value = '模型配置'
  modelForm.api_key = ''
  modelForm.api_key_masked = ''
  modelForm.enabled = true
  modelTestResult.value = null
  selectProvider('qwen')
}

function editConfig(cfg) {
  editingId.value = cfg.id
  configName.value = cfg.name || '模型配置'
  Object.assign(modelForm, {
    protocol: cfg.protocol || 'openai-compatible',
    api_key: '',
    api_key_masked: cfg.api_key_masked || '',
    base_url: cfg.base_url || '',
    model: cfg.model || '',
    enabled: cfg.enabled !== false,
  })
  preset.value = detectPreset(cfg)
  modelTestResult.value = null
}

async function refreshConfigs() {
  try {
    configs.value = await listModelConfigs()
  } catch { /* 忽略 */ }
}

async function handleActivate(id) {
  await activateModelConfig(id)
  await refreshConfigs()
  const active = configs.value.find((c) => c.is_active)
  if (active) editConfig(active)
  ElMessage.success('已切换当前模型')
}

async function handleDeleteConfig(cfg) {
  try {
    await ElMessageBox.confirm(`确定删除「${cfg.name || '模型配置'}」吗？`, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await deleteModelConfig(cfg.id)
    if (cfg.id === editingId.value) resetForm()
    await refreshConfigs()
    ElMessage.success('模型配置已删除')
  } catch { /* 用户取消 */ }
}

const mailModeText = computed(() => ({ smtp: 'SMTP 真实邮箱', mailhog: 'MailHog 本地邮箱', mock: 'Mock 模拟' })[import.meta.env.VITE_MAIL_MODE || 'smtp'] || 'smtp')
const smtpHost = import.meta.env.VITE_SMTP_HOST || 'smtp.qq.com（api/.env）'
const smtpUser = import.meta.env.VITE_SMTP_USER || '2174935034@qq.com（api/.env）'
const demoInbox = import.meta.env.VITE_DEMO_INBOX || '2174935034@qq.com（api/.env）'

async function handleTestConfig(cfg) {
  testingConfigId.value = cfg.id
  try {
    const res = await testModelConfigById(cfg.id)
    if (res.ok) {
      ElMessage.success(`连接成功（${res.latency_ms}ms）：${res.reply}`)
    } else {
      ElMessage.error(`连接失败：${res.error}`)
    }
  } catch {
    ElMessage.error('测试请求失败，请稍后重试')
  } finally {
    testingConfigId.value = null
  }
}

async function handleSaveModel() {
  savingModel.value = true
  try {
    const isEdit = !!editingId.value
    const payload = {
      name: configName.value || '模型配置',
      provider: preset.value === 'custom' ? '' : preset.value,
      protocol: modelForm.protocol,
      api_key: modelForm.api_key,
      base_url: modelForm.base_url,
      model: modelForm.model,
      enabled: modelForm.enabled,
    }
    const data = isEdit ? await updateModelConfig(editingId.value, payload) : await createModelConfig(payload)
    editingId.value = data.id
    modelForm.api_key = ''
    Object.assign(modelForm, {
      protocol: data.protocol,
      api_key_masked: data.api_key_masked,
      base_url: data.base_url,
      model: data.model,
      enabled: data.enabled,
    })
    preset.value = detectPreset(data)
    ElMessage.success(isEdit ? '模型配置已保存' : '模型配置已添加')
    await refreshConfigs()
    try { status.value = await getSystemStatus() } catch { /* 忽略 */ }
  } finally {
    savingModel.value = false
  }
}

async function handleSaveAndActivate() {
  await handleSaveModel()
  if (editingId.value) {
    await handleActivate(editingId.value)
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
    const list = await listModelConfigs()
    configs.value = list
    const active = list.find((c) => c.is_active) || list[0]
    if (active) editConfig(active)
    else resetForm()
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

<style scoped>
.codex-settings {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
@media (max-width: 900px) {
  .codex-settings { grid-template-columns: 1fr; }
}

/* 左侧分类导航 */
.settings-nav {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 12px;
  position: sticky;
  top: 0;
}
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--jf-border-strong);
  border-radius: 8px;
  margin-bottom: 10px;
  background: var(--jf-primary-softer);
  transition: border-color 0.18s ease;
}
.search-box:focus-within { border-color: var(--jf-primary); }
.search-icon { color: var(--jf-muted); flex-shrink: 0; }
.search-input {
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  font-family: inherit;
  color: var(--jf-ink);
  width: 100%;
}
.nav-list { display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: var(--jf-ink-soft);
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
  font-family: inherit;
}
.nav-item:hover { background: var(--jf-primary-softer); color: var(--jf-primary-dark); }
.nav-item.active { background: var(--jf-primary-soft); color: var(--jf-primary-darker); font-weight: 600; }
.nav-empty { padding: 12px; color: var(--jf-muted); font-size: 13px; text-align: center; }

/* 右侧面板 */
.settings-content {
  background: var(--jf-surface);
  border: 1px solid var(--jf-border);
  border-radius: var(--jf-radius);
  padding: 24px 28px;
  min-height: 520px;
}
.content-head { margin-bottom: 18px; }
.content-head h2 { font-size: 18px; font-weight: 700; color: var(--jf-ink); }
.content-head p { font-size: 13px; color: var(--jf-muted); margin-top: 4px; }
.content-head .el-tag { margin-top: 8px; }

.settings-block + .settings-block { margin-top: 26px; }
.block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--jf-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 4px;
}
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 0;
  border-bottom: 1px solid var(--jf-border-lighter, #eef8f5);
}
.setting-row:last-child { border-bottom: none; }
.row-info { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.row-label { font-size: 14px; font-weight: 600; color: var(--jf-ink); }
.row-desc { font-size: 12px; color: var(--jf-muted); }
.row-control { width: 320px; max-width: 55%; }
.row-value { font-size: 14px; color: var(--jf-ink-soft); text-align: right; }
.row-actions { display: flex; gap: 10px; }
.actions-row { border-bottom: none; }

.about-hero { display: flex; align-items: center; gap: 14px; padding: 6px 0 16px; }
.about-logo {
  width: 52px; height: 52px; border-radius: 14px;
  background: var(--jf-primary); color: #fff;
  display: flex; align-items: center; justify-content: center;
}
.about-name { font-size: 18px; font-weight: 800; color: var(--jf-ink); display: flex; align-items: center; gap: 8px; }
.about-sub { font-size: 12px; color: var(--jf-muted); margin-top: 2px; }
.about-text { color: var(--jf-ink-soft); line-height: 1.8; font-size: 13px; max-width: 560px; }

/* 模型服务 */
.head-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.status-pill { display: inline-flex; align-items: center; gap: 7px; padding: 5px 12px; border-radius: 999px; font-size: 12px; font-weight: 500; border: 1px solid var(--jf-border); background: var(--jf-surface); color: var(--jf-ink-soft); }
.status-pill .status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.status-pill.online { color: #0f766e; border-color: #a7f3d0; background: #ecfdf5; }
.status-pill.online .status-dot { background: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15); }
.status-pill.offline { color: #64748b; }
.status-pill.offline .status-dot { background: #94a3b8; }

.provider-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 0; }
@media (max-width: 1100px) { .provider-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 700px) { .provider-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.provider-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--jf-border);
  border-radius: 12px;
  background: var(--jf-surface);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: all 0.18s ease;
}
.provider-card:hover { border-color: var(--jf-primary); background: var(--jf-primary-softer); }
.provider-card.active { border-color: var(--jf-primary); background: var(--jf-primary-soft); box-shadow: inset 0 0 0 1px var(--jf-primary); }
.provider-badge { width: 34px; height: 34px; border-radius: 10px; color: #fff; font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center; }
.provider-name { font-size: 13px; font-weight: 600; color: var(--jf-ink); }
.provider-proto { font-size: 10px; color: var(--jf-primary-darker); background: var(--jf-primary-soft); padding: 1px 7px; border-radius: 999px; margin-top: 2px; }
.provider-note { font-size: 11px; color: var(--jf-muted); }
.provider-check { position: absolute; top: 10px; right: 10px; color: var(--jf-primary); }

.advanced-collapse { border: 1px solid var(--jf-border); border-radius: var(--jf-radius); background: var(--jf-surface); }
.advanced-collapse :deep(.el-collapse-item__header) { font-size: 13px; font-weight: 600; color: var(--jf-ink-soft); background: transparent; padding: 0 14px; }
.advanced-collapse :deep(.el-collapse-item__wrap) { background: transparent; }
.advanced-collapse :deep(.el-collapse-item__content) { padding: 0 14px 16px; }

/* 模型配置卡片 + 编辑面板 */
.model-panel { background: var(--jf-surface); border: 1px solid var(--jf-border); border-radius: 14px; padding: 18px; margin-bottom: 18px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.panel-head h3 { font-size: 15px; font-weight: 700; color: var(--jf-ink); }
.panel-head p { font-size: 12px; color: var(--jf-muted); margin-top: 2px; }
.model-configs { display: flex; flex-direction: column; gap: 8px; }
.model-config { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid var(--jf-border); border-radius: 12px; background: var(--jf-surface); cursor: pointer; transition: all 0.18s ease; }
.model-config:hover { border-color: var(--jf-primary); box-shadow: 0 2px 12px rgba(13, 148, 136, 0.08); }
.model-config.editing { border-color: var(--jf-primary); }
.model-config.active { border-color: var(--jf-primary); background: var(--jf-primary-soft); }
.cfg-badge { width: 36px; height: 36px; border-radius: 10px; color: #fff; font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.cfg-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.cfg-title { display: flex; align-items: center; gap: 8px; min-width: 0; }
.cfg-name { font-size: 13px; font-weight: 600; color: var(--jf-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cfg-active-badge { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: #0f766e; background: #d1fae5; border-radius: 999px; padding: 1px 8px; font-weight: 600; }
.cfg-sub { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--jf-muted); min-width: 0; }
.cfg-sub > span:first-child { color: var(--jf-ink-soft); }
.cfg-dot { width: 3px; height: 3px; border-radius: 50%; background: var(--jf-border-strong); flex-shrink: 0; }
.cfg-model { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; color: var(--jf-ink-soft); }
.cfg-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.config-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 24px 0; color: var(--jf-muted); font-size: 13px; }
.panel-body { display: flex; flex-direction: column; gap: 18px; }
.sub-title { font-size: 12px; font-weight: 600; color: var(--jf-muted); text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 10px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field.span-2 { grid-column: span 2; }
.field label { font-size: 13px; font-weight: 600; color: var(--jf-ink); }
.field-hint { font-size: 11px; color: var(--jf-muted); }
.editor-actions { display: flex; align-items: center; gap: 10px; padding-top: 2px; flex-wrap: wrap; }
.advanced-block { margin-top: 2px; }
</style>