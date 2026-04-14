import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '登录', requiresAuth: false },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { title: '注册', requiresAuth: false },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { title: '系统首页', requiresAuth: true },
    },
    {
      path: '/detection/image',
      name: 'image-detection',
      component: () => import('../views/ImageDetectionView.vue'),
      meta: { title: '图片检测', requiresAuth: true },
    },
    {
      path: '/detection/video',
      name: 'video-detection',
      component: () => import('../views/VideoDetectionView.vue'),
      meta: { title: '视频检测', requiresAuth: true },
    },
    {
      path: '/detection/camera',
      name: 'camera-detection',
      component: () => import('../views/CameraDetectionView.vue'),
      meta: { title: '实时检测', requiresAuth: true },
    },
    {
      path: '/statistics',
      name: 'statistics',
      component: () => import('../views/StatisticsView.vue'),
      meta: { title: '统计分析', requiresAuth: true },
    },
    {
      path: '/records',
      name: 'records',
      component: () => import('../views/RecordsView.vue'),
      meta: { title: '检测记录', requiresAuth: true },
    },
    {
      path: '/records/:id',
      name: 'record-detail',
      component: () => import('../views/RecordDetailView.vue'),
      meta: { title: '检测详情', requiresAuth: true },
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('../views/ReportsView.vue'),
      meta: { title: '检测报告', requiresAuth: true },
    },
    {
      path: '/reports/:id',
      name: 'report-detail',
      component: () => import('../views/ReportDetailView.vue'),
      meta: { title: '报告详情', requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      meta: { title: '系统配置', requiresAuth: true, adminOnly: true },
    },
    {
      path: '/models',
      name: 'models',
      component: () => import('../views/ModelsView.vue'),
      meta: { title: '模型管理', requiresAuth: true, adminOnly: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    return { name: 'login' }
  }

  if ((to.name === 'login' || to.name === 'register') && token) {
    return { name: 'home' }
  }

  if (!token) return

  if (!authStore.role) {
    try {
      const profile = await fetch('http://localhost:8000/api/users/profile', {
        headers: { Authorization: `Bearer ${token}` },
      }).then((res) => (res.ok ? res.json() : null))

      authStore.setRole(profile?.role || 'user')
    } catch {
      authStore.setRole('user')
    }
  }

  if (to.meta.adminOnly && !authStore.isAdmin) {
    return { name: 'home' }
  }
})

export default router
