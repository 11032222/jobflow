<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📅 面试日程</span>
          <el-button type="primary" @click="openDialog()">+ 添加面试</el-button>
        </div>
      </template>

      <el-table :data="interviews">
        <el-table-column label="公司 / 职位" min-width="200">
          <template #default="{ row }">
            <div class="job-title">{{ row.job_title || '-' }}</div>
            <div class="company">{{ row.company_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型 / 轮次" width="120">
          <template #default="{ row }">{{ row.interview_type }} · 第{{ row.round_no }}轮</template>
        </el-table-column>
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ (row.scheduled_at || '').slice(0, 16).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="ivType(row.status)" size="small">{{ ivText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.notes || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑面试' : '添加面试'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="岗位">
          <el-select v-model="form.job_id" placeholder="关联岗位（选填）" clearable filterable style="width: 100%">
            <el-option v-for="j in appliedJobs" :key="j.job_id" :label="`${j.job_title}（${j.company_name}）`" :value="j.job_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="面试类型">
          <el-select v-model="form.interview_type" style="width: 100%">
            <el-option label="电话面试" value="电话面试" />
            <el-option label="视频面试" value="视频面试" />
            <el-option label="现场面试" value="现场面试" />
            <el-option label="笔试" value="笔试" />
          </el-select>
        </el-form-item>
        <el-form-item label="轮次">
          <el-input-number v-model="form.round_no" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker v-model="form.scheduled_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="已安排" value="SCHEDULED" />
            <el-option label="进行中" value="PENDING" />
            <el-option label="已完成" value="DONE" />
            <el-option label="已取消" value="CANCELLED" />
          </el-select>
        </el-form-item>
        <el-form-item label="会议链接"><el-input v-model="form.meeting_url" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.contact_phone" /></el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="反馈">
          <el-input v-model="form.feedback" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createInterview, deleteInterview, getApplications, getInterviews, updateInterview } from '@/api'

const interviews = ref([])
const appliedJobs = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const saving = ref(false)

const emptyForm = {
  id: null, application_id: null, company_id: null, job_id: null,
  interview_type: '视频面试', round_no: 1, scheduled_at: null,
  status: 'SCHEDULED', contact_person: '', contact_phone: '',
  address: '', meeting_url: '', notes: '', feedback: '',
}
const form = reactive({ ...emptyForm })

function ivText(s) {
  return { SCHEDULED: '已安排', PENDING: '进行中', DONE: '已完成', CANCELLED: '已取消' }[s] || s
}
function ivType(s) {
  return { SCHEDULED: 'primary', PENDING: 'warning', DONE: 'success', CANCELLED: 'info' }[s] || 'info'
}

async function load() {
  interviews.value = await getInterviews()
  appliedJobs.value = await getApplications()
}

function openDialog(row) {
  editing.value = !!row
  if (row) {
    Object.assign(form, emptyForm, {
      id: row.id, application_id: row.application_id, company_id: row.company_id,
      job_id: row.job_id, interview_type: row.interview_type, round_no: row.round_no,
      scheduled_at: row.scheduled_at, status: row.status, contact_person: row.contact_person,
      contact_phone: row.contact_phone, address: row.address, meeting_url: row.meeting_url,
      notes: row.notes, feedback: row.feedback,
    })
  } else {
    Object.assign(form, emptyForm)
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form }
    delete payload.id
    const app = appliedJobs.value.find((a) => a.job_id === form.job_id)
    if (app) {
      payload.application_id = app.id
      payload.company_id = app.company_id
    }
    if (editing.value) {
      await updateInterview(form.id, payload)
    } else {
      await createInterview(payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除这条面试记录吗？', '提示', { type: 'warning' })
  await deleteInterview(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.job-title {
  font-weight: 600;
}
.company {
  color: #909399;
  font-size: 12px;
}
</style>

