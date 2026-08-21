import request from './request'

// ===== 认证 =====
export const register = (data) => request.post('/auth/register', data)
export const login = (data) => request.post('/auth/login', data)
export const getMe = () => request.get('/auth/me')

// ===== 用户 =====
export const updateUser = (data) => request.put('/users/me', data)

// ===== 简历 =====
export const uploadResume = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/resumes', form)
}
export const getResumes = () => request.get('/resumes')
export const parseResume = (id) => request.post(`/resumes/${id}/parse`)
export const deleteResume = (id) => request.delete(`/resumes/${id}`)

// ===== 求职画像 =====
export const getProfiles = () => request.get('/profiles')
export const getCurrentProfile = () => request.get('/profiles/current')
export const createProfile = (data) => request.post('/profiles', data)
export const updateProfile = (id, data) => request.put(`/profiles/${id}`, data)
export const setCurrentProfile = (id) => request.post(`/profiles/${id}/set-current`)
export const addExperience = (profileId, data) =>
  request.post(`/profiles/${profileId}/experiences`, data)
export const updateExperience = (profileId, expId, data) =>
  request.put(`/profiles/${profileId}/experiences/${expId}`, data)
export const deleteExperience = (profileId, expId) =>
  request.delete(`/profiles/${profileId}/experiences/${expId}`)
export const addSkill = (profileId, data) =>
  request.post(`/profiles/${profileId}/skills`, data)
export const deleteSkill = (profileId, skillId) =>
  request.delete(`/profiles/${profileId}/skills/${skillId}`)

// ===== 求职偏好 =====
export const getPreference = () => request.get('/preferences')
export const savePreference = (data) => request.put('/preferences', data)

// ===== 岗位 =====
export const getJobs = (params) => request.get('/jobs', { params })
export const getJob = (id) => request.get(`/jobs/${id}`)
export const addFavorite = (id) => request.post(`/jobs/${id}/favorite`)
export const removeFavorite = (id) => request.delete(`/jobs/${id}/favorite`)
export const importJobs = (data) => request.post('/jobs/import', data)
export const getJobSources = () => request.get('/jobs/sources')
export const getCollectors = () => request.get('/jobs/collectors')
export const launchZhipinChrome = () => request.post('/jobs/collectors/zhipin/launch')

// ===== 公司 =====
export const getCompany = (id) => request.get(`/companies/${id}`)
export const researchCompany = (id) => request.post(`/companies/${id}/research`)

// ===== 推荐 =====
export const getRecommendations = (params) => request.get('/recommendations', { params })
export const matchJob = (jobId) => request.post(`/recommendations/jobs/${jobId}/match`)

// ===== 投递 =====
export const createApplication = (data) => request.post('/applications', data)
export const getApplications = (params) => request.get('/applications', { params })
export const getApplication = (id) => request.get(`/applications/${id}`)
export const submitApplication = (id) => request.post(`/applications/${id}/submit`)
export const updateApplicationStatus = (id, data) =>
  request.post(`/applications/${id}/status`, data)

// ===== 面试 =====
export const getInterviews = () => request.get('/interviews')
export const createInterview = (data) => request.post('/interviews', data)
export const updateInterview = (id, data) => request.put(`/interviews/${id}`, data)
export const deleteInterview = (id) => request.delete(`/interviews/${id}`)
export const getInterview = (id) => request.get(`/interviews/${id}`)
export const updateInterviewStatus = (id, data) =>
  request.post(`/interviews/${id}/status`, data)

// ===== 面试问题记录 =====
export const getInterviewQuestions = (id) => request.get(`/interviews/${id}/questions`)
export const createInterviewQuestion = (id, data) =>
  request.post(`/interviews/${id}/questions`, data)
export const updateInterviewQuestion = (id, qid, data) =>
  request.put(`/interviews/${id}/questions/${qid}`, data)
export const deleteInterviewQuestion = (id, qid) =>
  request.delete(`/interviews/${id}/questions/${qid}`)

// ===== 面试复盘 =====
export const triggerInterviewReview = (id) => request.post(`/interviews/${id}/review`)
export const getInterviewReview = (id) => request.get(`/interviews/${id}/review`)

// ===== 面试知识库（跨面试聚合能力画像）=====
export const getInterviewKnowledge = () => request.get('/interviews/knowledge')

// ===== 面试会话 / 知识库 =====
export const getInterviewSessions = () => request.get('/interview-sessions')
export const createInterviewSession = (data) => request.post('/interview-sessions', data)
export const getInterviewSession = (id) => request.get(`/interview-sessions/${id}`)
export const updateInterviewSession = (id, data) => request.put(`/interview-sessions/${id}`, data)
export const deleteInterviewSession = (id) => request.delete(`/interview-sessions/${id}`)
export const createSessionQuestion = (sessionId, data) =>
  request.post(`/interview-sessions/${sessionId}/questions`, data)
export const updateSessionQuestion = (sessionId, questionId, data) =>
  request.put(`/interview-sessions/${sessionId}/questions/${questionId}`, data)
export const deleteSessionQuestion = (sessionId, questionId) =>
  request.delete(`/interview-sessions/${sessionId}/questions/${questionId}`)
export const getSessionReview = (sessionId) => request.get(`/interview-sessions/${sessionId}/review`)
export const generateSessionReview = (sessionId) =>
  request.post(`/interview-sessions/${sessionId}/review`)
export const transcribeSession = (file, meta = {}) => {
  const form = new FormData()
  form.append('file', file)
  if (meta.title) form.append('title', meta.title)
  if (meta.company_name) form.append('company_name', meta.company_name)
  if (meta.job_title) form.append('job_title', meta.job_title)
  if (meta.interview_id) form.append('interview_id', meta.interview_id)
  if (meta.source) form.append('source', meta.source)
  return request.post('/interview-sessions/transcribe', form)
}

// ===== Agent 任务 =====
export const getTasks = (params) => request.get('/tasks', { params })
export const getTask = (id) => request.get(`/tasks/${id}`)

// ===== 系统状态 =====
export const getSystemStatus = () => request.get('/system/status')

// ===== 模型服务配置 =====
export const getModelConfig = () => request.get('/settings/model')
export const saveModelConfig = (data) => request.put('/settings/model', data)
export const testModelConfig = (data) => request.post('/settings/model/test', data)

export const listModelConfigs = () => request.get('/settings/models')
export const createModelConfig = (data) => request.post('/settings/models', data)
export const updateModelConfig = (id, data) => request.put(`/settings/models/${id}`, data)
export const deleteModelConfig = (id) => request.delete(`/settings/models/${id}`)
export const activateModelConfig = (id) => request.post(`/settings/models/${id}/activate`)
export const testModelConfigById = (id) => request.post(`/settings/models/${id}/test`)

// ===== 简历修改建议 =====
export const getProfileSuggestions = (profileId) => request.post(`/profiles/${profileId}/suggestions`)
