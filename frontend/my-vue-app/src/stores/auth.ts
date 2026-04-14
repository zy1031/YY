import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

interface AuthPayload {
  access_token: string
  user_id: number
  username: string
  role?: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const userId = ref<number | null>(Number(localStorage.getItem('userId')) || null)
  const username = ref<string | null>(localStorage.getItem('username'))
  const role = ref<string | null>(localStorage.getItem('role'))

  function setAuth(data: AuthPayload) {
    token.value = data.access_token
    userId.value = data.user_id
    username.value = data.username
    role.value = data.role || 'user'
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userId', String(data.user_id))
    localStorage.setItem('username', data.username)
    localStorage.setItem('role', role.value)
  }

  function setRole(nextRole: string | null) {
    role.value = nextRole
    if (nextRole) {
      localStorage.setItem('role', nextRole)
    } else {
      localStorage.removeItem('role')
    }
  }

  function logout() {
    token.value = null
    userId.value = null
    username.value = null
    role.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
  }

  const isLoggedIn = () => !!token.value
  const isAdmin = computed(() => role.value === 'admin')

  return { token, userId, username, role, setAuth, setRole, logout, isLoggedIn, isAdmin }
})
