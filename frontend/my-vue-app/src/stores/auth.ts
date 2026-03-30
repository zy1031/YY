import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const userId = ref<number | null>(Number(localStorage.getItem('userId')) || null)
  const username = ref<string | null>(localStorage.getItem('username'))

  function setAuth(data: { access_token: string; user_id: number; username: string }) {
    token.value = data.access_token
    userId.value = data.user_id
    username.value = data.username
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userId', String(data.user_id))
    localStorage.setItem('username', data.username)
  }

  function logout() {
    token.value = null
    userId.value = null
    username.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    localStorage.removeItem('username')
  }

  const isLoggedIn = () => !!token.value

  return { token, userId, username, setAuth, logout, isLoggedIn }
})
