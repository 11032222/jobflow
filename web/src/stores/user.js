import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('jobflow_token') || '',
    user: JSON.parse(localStorage.getItem('jobflow_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    displayName: (state) => state.user?.real_name || state.user?.username || '未登录',
  },
  actions: {
    setAuth(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('jobflow_token', token)
      localStorage.setItem('jobflow_user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('jobflow_token')
      localStorage.removeItem('jobflow_user')
    },
  },
})
