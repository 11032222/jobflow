import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'resumes', name: 'Resumes', component: () => import('@/views/Resumes.vue'), meta: { title: '简历管理' } },
      { path: 'jobs', name: 'Jobs', component: () => import('@/views/Jobs.vue'), meta: { title: '岗位库' } },
      { path: 'jobs/:id', name: 'JobDetail', component: () => import('@/views/JobDetail.vue'), meta: { title: '岗位详情' } },
      { path: 'recommendations', name: 'Recommendations', component: () => import('@/views/Recommendations.vue'), meta: { title: '智能推荐' } },
      { path: 'applications', name: 'Applications', component: () => import('@/views/Applications.vue'), meta: { title: '投递看板' } },
      { path: 'interviews', name: 'Interviews', component: () => import('@/views/Interviews.vue'), meta: { title: '面试管理' } },
      { path: 'tasks', name: 'Tasks', component: () => import('@/views/Tasks.vue'), meta: { title: '任务中心' } },
      { path: 'settings', name: 'Settings', component: () => import('@/views/Settings.vue'), meta: { title: '设置' } },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('jobflow_token')
  if (!token && to.name !== 'Login') {
    return { name: 'Login' }
  }
  if (token && to.name === 'Login') {
    return { name: 'Dashboard' }
  }
  return true
})

export default router
