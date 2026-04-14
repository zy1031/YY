<script setup lang="ts">
import { RouterView, useRouter, useRoute } from 'vue-router'
import { ref, computed, watch } from 'vue'
import { useAuthStore } from './stores/auth'

interface MenuItem {
  index: string
  icon: string
  title: string
  adminOnly?: boolean
}

interface MenuGroup {
  label: string
  items: MenuItem[]
}

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const isCollapse = ref(false)
const pageLoading = ref(false)
let loadingTimer: ReturnType<typeof setTimeout> | null = null

const isAuthPage = computed(() => route.name === 'login' || route.name === 'register')
const showPageTransition = computed(() => !isAuthPage.value)

watch(
  () => route.fullPath,
  () => {
    if (isAuthPage.value) {
      pageLoading.value = false
      if (loadingTimer) {
        clearTimeout(loadingTimer)
        loadingTimer = null
      }
      return
    }

    pageLoading.value = true
    if (loadingTimer) clearTimeout(loadingTimer)
    loadingTimer = setTimeout(() => {
      pageLoading.value = false
      loadingTimer = null
    }, 160)
  },
  { immediate: true },
)

const menuGroups: MenuGroup[] = [
  {
    label: '检测',
    items: [
      { index: '/', icon: 'House', title: '系统首页' },
      { index: '/detection/image', icon: 'Picture', title: '图片检测' },
      { index: '/detection/video', icon: 'VideoPlay', title: '视频检测' },
      { index: '/detection/camera', icon: 'Camera', title: '实时检测' },
    ],
  },
  {
    label: '数据',
    items: [
      { index: '/records', icon: 'List', title: '检测记录' },
      { index: '/statistics', icon: 'TrendCharts', title: '统计分析' },
      { index: '/reports', icon: 'Document', title: '检测报告' },
    ],
  },
  {
    label: '管理',
    items: [
      { index: '/models', icon: 'Cpu', title: '模型管理', adminOnly: true },
      { index: '/settings', icon: 'Setting', title: '系统配置', adminOnly: true },
    ],
  },
]

const visibleMenuGroups = computed(() => {
  return menuGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.adminOnly || authStore.isAdmin),
    }))
    .filter((group) => group.items.length > 0)
})

// 当前激活菜单项
const activeIndex = computed(() => route.path)

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    authStore.logout()
    pageLoading.value = false
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/users/profile')
  }
}
</script>

<template>
  <div class="app-container">
    <RouterView v-if="isAuthPage" />

    <el-container v-else class="main-layout">
      <!-- 侧边栏 -->
      <el-aside :width="isCollapse ? '64px' : '210px'" class="sidebar">
        <!-- Logo -->
        <div class="logo" :class="{ collapsed: isCollapse }">
          <div class="logo-icon-wrap">
            <span class="logo-emoji">🐾</span>
          </div>
          <transition name="fade">
            <div v-if="!isCollapse" class="logo-texts">
              <span class="logo-title">动物健康检测</span>
              <span class="logo-ver">AI Detection v1.0</span>
            </div>
          </transition>
        </div>

        <!-- 菜单 -->
        <div class="menu-scroll">
          <div v-for="group in visibleMenuGroups" :key="group.label" class="menu-group">
            <div v-if="!isCollapse" class="menu-group-label">{{ group.label }}</div>
            <div
              v-for="item in group.items"
              :key="item.index"
              class="menu-item"
              :class="{ active: activeIndex === item.index || (item.index !== '/' && activeIndex.startsWith(item.index)) }"
              @click="router.push(item.index)"
              :title="isCollapse ? item.title : ''"
            >
              <el-icon class="menu-icon"><component :is="item.icon" /></el-icon>
              <transition name="slide-fade">
                <span v-if="!isCollapse" class="menu-text">{{ item.title }}</span>
              </transition>
              <transition name="fade">
                <span v-if="!isCollapse && (activeIndex === item.index || (item.index !== '/' && activeIndex.startsWith(item.index)))" class="active-dot"></span>
              </transition>
            </div>
          </div>
        </div>

        <!-- 折叠按钮 -->
        <div class="collapse-btn" @click="isCollapse = !isCollapse">
          <el-icon class="collapse-icon">
            <ArrowLeft v-if="!isCollapse" />
            <ArrowRight v-else />
          </el-icon>
          <transition name="fade">
            <span v-if="!isCollapse" class="collapse-text">收起侧栏</span>
          </transition>
        </div>
      </el-aside>

      <!-- 右侧主体 -->
      <el-container class="content-wrapper">
        <!-- 顶部导航 -->
        <el-header class="header">
          <div class="header-left">
            <div class="page-badge">
              <span class="page-title">{{ route.meta.title || '动物健康检测系统' }}</span>
            </div>
          </div>
          <div class="header-right">
            <!-- 系统状态指示 -->
            <div class="status-dot" title="系统运行正常">
              <span class="dot-pulse"></span>
              <span class="status-text">系统运行中</span>
            </div>

            <el-divider direction="vertical" />

            <el-dropdown @command="handleCommand" trigger="click">
              <div class="user-info">
                <el-avatar :size="34" class="avatar">
                  {{ authStore.username?.charAt(0)?.toUpperCase() }}
                </el-avatar>
                <div class="user-texts">
                  <span class="username">{{ authStore.username }}</span>
                </div>
                <el-icon class="arrow-icon"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">
                    <el-icon><Right /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <!-- 主内容区 -->
        <el-main class="main-content">
          <div v-if="pageLoading" class="page-loading">
            <div class="loading-bar"></div>
          </div>
          <RouterView v-slot="{ Component }">
            <template v-if="showPageTransition">
              <transition name="page" mode="out-in">
                <component :is="Component" />
              </transition>
            </template>
            <component :is="Component" v-else />
          </RouterView>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
/* ===== 基础布局 ===== */
.app-container {
  height: 100vh;
  overflow: hidden;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.main-layout { height: 100vh; }

/* ===== 侧边栏 ===== */
.sidebar {
  background: #111827;
  display: flex;
  flex-direction: column;
  transition: width 0.28s cubic-bezier(.4,0,.2,1);
  overflow: hidden;
  border-right: 1px solid rgba(255,255,255,0.04);
  box-shadow: 2px 0 12px rgba(0,0,0,0.25);
}

/* Logo */
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  overflow: hidden;
  flex-shrink: 0;
}
.logo.collapsed { justify-content: center; padding: 0; }
.logo-icon-wrap {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #4fc3f7, #0288d1);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(79,195,247,0.35);
}
.logo-emoji { font-size: 18px; }
.logo-texts { display: flex; flex-direction: column; gap: 1px; overflow: hidden; }
.logo-title { font-size: 13px; font-weight: 700; color: #e2e8f0; white-space: nowrap; letter-spacing: 0.5px; }
.logo-ver { font-size: 10px; color: #4a6080; white-space: nowrap; }

/* 菜单滚动区 */
.menu-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0;
  scrollbar-width: none;
}
.menu-scroll::-webkit-scrollbar { display: none; }

/* 菜单分组 */
.menu-group { margin-bottom: 4px; }
.menu-group-label {
  font-size: 10px;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 10px 18px 4px;
  user-select: none;
}

/* 菜单项 */
.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  height: 42px;
  cursor: pointer;
  border-radius: 8px;
  margin: 2px 8px;
  color: #6b7280;
  transition: all 0.18s ease;
  position: relative;
  overflow: hidden;
}
.menu-item:hover {
  background: rgba(79,195,247,0.08);
  color: #94a3b8;
}
.menu-item.active {
  background: rgba(79,195,247,0.12);
  color: #4fc3f7;
}
.menu-item.active .menu-icon {
  color: #4fc3f7;
  filter: drop-shadow(0 0 6px rgba(79,195,247,0.5));
}
.menu-icon { font-size: 17px; flex-shrink: 0; transition: all 0.18s; }
.menu-text { font-size: 13px; font-weight: 500; white-space: nowrap; flex: 1; }
.active-dot {
  width: 5px; height: 5px;
  background: #4fc3f7;
  border-radius: 50%;
  box-shadow: 0 0 6px #4fc3f7;
  flex-shrink: 0;
}

/* 折叠按钮 */
.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  cursor: pointer;
  padding: 0 18px;
  color: #374151;
  border-top: 1px solid rgba(255,255,255,0.05);
  transition: all 0.18s;
  flex-shrink: 0;
}
.collapse-btn:hover { color: #4fc3f7; background: rgba(79,195,247,0.06); }
.collapse-icon { font-size: 14px; }
.collapse-text { font-size: 12px; white-space: nowrap; }

/* ===== 顶部导航 ===== */
.header {
  background: #fff;
  border-bottom: 1px solid #f1f3f5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  box-shadow: 0 1px 8px rgba(0,0,0,0.05);
  flex-shrink: 0;
  z-index: 10;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.page-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a202c;
  letter-spacing: 0.3px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 系统状态 */
.status-dot {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: default;
}
.dot-pulse {
  width: 8px; height: 8px;
  background: #48bb78;
  border-radius: 50%;
  position: relative;
  flex-shrink: 0;
}
.dot-pulse::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 1.5px solid #48bb78;
  animation: pulse 2s ease-out infinite;
}
@keyframes pulse {
  0% { opacity: 0.8; transform: scale(1); }
  100% { opacity: 0; transform: scale(2); }
}
.status-text { font-size: 12px; color: #48bb78; font-weight: 500; white-space: nowrap; }

/* 用户信息 */
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background 0.18s;
}
.user-info:hover { background: #f8fafc; }
.avatar {
  background: linear-gradient(135deg, #4fc3f7, #0288d1);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}
.user-texts { display: flex; flex-direction: column; }
.username { font-size: 13px; font-weight: 600; color: #2d3447; }
.arrow-icon { font-size: 12px; color: #a0aec0; }

/* ===== 主内容区 ===== */
.content-wrapper { flex-direction: column; overflow: hidden; }
.main-content {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
  position: relative;
}

/* 页面 loading 条 */
.page-loading {
  position: absolute;
  inset: 0 0 auto 0;
  z-index: 100;
  overflow: hidden;
  height: 2px;
  pointer-events: none;
}
.loading-bar {
  height: 2px;
  background: linear-gradient(90deg, transparent, #4fc3f7, #0288d1, transparent);
  animation: loadbar 0.45s ease-in-out;
}
@keyframes loadbar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* ===== 过渡动画 ===== */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
.page-enter-to,
.page-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-fade-enter-active { transition: all 0.2s ease; }
.slide-fade-leave-active { transition: all 0.15s ease; }
.slide-fade-enter-from { opacity: 0; transform: translateX(-8px); }
.slide-fade-leave-to { opacity: 0; transform: translateX(-4px); }
</style>
