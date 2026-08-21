/**
 * 面试模块枚举与中文映射。
 *
 * 后端一律存英文码（与 applications/profiles 等模块一致），中文只在这里做展示映射。
 * 提交给接口的必须是码——写回中文会被后端 schema 校验拦成 422。
 */

// 面试状态机（文档 8.4）
export const INTERVIEW_STATUS = {
  SCHEDULED: '已安排',
  IN_PROGRESS: '进行中',
  COMPLETED: '已完成',
  REVIEWED: '已复盘',
  CANCELLED: '已取消',
}

export const INTERVIEW_STATUS_TAG = {
  SCHEDULED: 'primary',
  IN_PROGRESS: 'warning',
  COMPLETED: 'success',
  REVIEWED: 'success',
  CANCELLED: 'info',
}

// 允许的状态流转，与后端 interview_service.TRANSITIONS 保持一致
export const INTERVIEW_TRANSITIONS = {
  SCHEDULED: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: ['REVIEWED', 'CANCELLED'],
  REVIEWED: [],
  CANCELLED: [],
}

// 面试方式
export const INTERVIEW_TYPE = {
  PHONE: '电话面试',
  VIDEO: '视频面试',
  ONSITE: '现场面试',
}

// 面试性质（轮次类型）
export const ROUND_TYPE = {
  TECHNICAL: '技术面',
  HR: 'HR 面',
  BOSS: '主管面',
  CROSS: '交叉面',
  WRITTEN: '笔试',
}

// 面试结果
export const INTERVIEW_RESULT = {
  PASS: '通过',
  FAIL: '未通过',
  PENDING: '待定',
}

export const INTERVIEW_RESULT_TAG = {
  PASS: 'success',
  FAIL: 'danger',
  PENDING: 'warning',
}

// 面试问题自评（文档 3.10）
export const SELF_RESULT = {
  MASTERED: '已掌握',
  PARTIAL: '回答不完整',
  FAILED: '完全不会',
}

export const SELF_RESULT_TAG = {
  MASTERED: 'success',
  PARTIAL: 'warning',
  FAILED: 'danger',
}

// 复盘状态：NONE 表示从未复盘
export const REVIEW_STATUS = {
  NONE: '未复盘',
  RUNNING: '复盘中',
  SUCCESS: '已复盘',
  FAILED: '复盘失败',
}

// 复盘结果来源
export const REVIEW_SOURCE = {
  LLM: '大模型分析',
  RULE: '规则引擎',
}

/** 取中文标签；未知码原样返回，避免历史脏数据显示成空白 */
export function label(map, code) {
  if (code === null || code === undefined || code === '') return '-'
  return map[code] || code
}

/** 下拉选项：[{ value, label }] */
export function options(map) {
  return Object.entries(map).map(([value, text]) => ({ value, label: text }))
}
