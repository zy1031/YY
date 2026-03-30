<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { detectionApi } from '../api/detection'
import { statisticsApi } from '../api/animals'

const router = useRouter()
const authStore = useAuthStore()

const stats = ref({
  totalDetections: 0,
  todayDetections: 0,
  abnormalCount: 0,
  reportCount: 0,
})

const recentRecords = ref([])
const loading = ref(false)
const statsLoading = ref(false)

const quickActions = [
  { title: '图片检测', icon: '🖼️', desc: '上传图片进行健康检测', route: '/detection/image', color: '#4fc3f7' },
  { title: '视频检测', icon: '🎬', desc: '上传视频逐帧分析', route: '/detection/video', color: '#81c784' },
  { title: '实时检测', icon: '📷', desc: '摄像头实时检测跟踪', route: '/detection/camera', color: '#ffb74d' },
  { title: '查看记录', icon: '📋', desc: '查看所有历史检测记录', route: '/records', color: '#f06292' },
]

onMounted(async () => {
  loading.value = true
  statsLoading.value = true
  try {
    const [overviewRes, historyRes, reportsRes]: any[] = await Promise.all([
      statisticsApi.getOverview(),
      detectionApi.getHistory({ page: 1, page_size: 5 }),
      import('../api/reports').then(m => m.reportsApi.list(1, 1)),
    ])
    stats.value.totalDetections = overviewRes.total_detections || 0
    stats.value.todayDetections = overviewRes.today_detections || 0
    stats.value.abnormalCount = overviewRes.total_abnormal || 0
    stats.value.reportCount = reportsRes.total || 0
    recentRecords.value = historyRes.history || []
  } catch {}
  finally { loading.value = false; statsLoading.value = false }
})
</script>

<template>
  <div class="home-page">
    <!-- 欢迎区域 -->
    <div class="welcome-banner anim-fade-in">
      <div class="welcome-text">
        <h2>欢迎回来，{{ authStore.username }} 👋</h2>
        <p>动物健康检测系统 — 基于深度学习的智能养殖辅助平台</p>
      </div>
      <div class="welcome-icon">🐄🐖🐑</div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <template v-if="statsLoading">
        <div class="stat-card" v-for="i in 4" :key="i">
          <el-skeleton :rows="2" animated />
        </div>
      </template>
      <template v-else>
        <div class="stat-card anim-fade-in anim-delay-1">
          <div class="stat-icon" style="background: #e3f2fd">🔍</div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.totalDetections }}</span>
            <span class="stat-label">累计检测次数</span>
          </div>
        </div>
        <div class="stat-card anim-fade-in anim-delay-2">
          <div class="stat-icon" style="background: #e8f5e9">📅</div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.todayDetections }}</span>
            <span class="stat-label">今日检测次数</span>
          </div>
        </div>
        <div class="stat-card anim-fade-in anim-delay-3">
          <div class="stat-icon" style="background: #fff3e0">⚠️</div>
          <div class="stat-info">
            <span class="stat-value" style="color: #f57c00">{{ stats.abnormalCount }}</span>
            <span class="stat-label">异常动物数</span>
          </div>
        </div>
        <div class="stat-card anim-fade-in anim-delay-4">
          <div class="stat-icon" style="background: #fce4ec">📄</div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.reportCount }}</span>
            <span class="stat-label">生成报告数</span>
          </div>
        </div>
      </template>
    </div>

    <!-- 快捷入口 -->
    <div class="section">
      <h3 class="section-title">快捷功能</h3>
      <div class="actions-grid">
        <div
          v-for="action in quickActions"
          :key="action.route"
          class="action-card"
          @click="router.push(action.route)"
        >
          <div class="action-icon">{{ action.icon }}</div>
          <div class="action-info">
            <span class="action-title">{{ action.title }}</span>
            <span class="action-desc">{{ action.desc }}</span>
          </div>
          <el-icon class="action-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 最近检测记录 -->
    <div class="section">
      <h3 class="section-title">最近检测记录</h3>
      <el-table :data="recentRecords" v-loading="loading" style="width: 100%" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="detection_type" label="检测类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.detection_type === 'image' ? 'primary' : row.detection_type === 'video' ? 'success' : 'warning'">
              {{ row.detection_type === 'image' ? '图片' : row.detection_type === 'video' ? '视频' : '摄像头' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detection_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.detection_status === 'completed' ? 'success' : row.detection_status === 'failed' ? 'danger' : 'info'">
              {{ row.detection_status === 'completed' ? '已完成' : row.detection_status === 'failed' ? '失败' : '处理中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_targets" label="检测目标数" width="110" />
        <el-table-column prop="abnormal_count" label="异常数" width="90">
          <template #default="{ row }">
            <span :style="{ color: row.abnormal_count > 0 ? '#f57c00' : 'inherit' }">{{ row.abnormal_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="检测时间" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="router.push('/records/' + row.id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="view-more">
        <el-button link type="primary" @click="router.push('/records')">查看全部记录 →</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page { display: flex; flex-direction: column; gap: 20px; }

.welcome-banner {
  background: linear-gradient(135deg, #1a2a3a, #0d2137);
  border-radius: 12px;
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #e2e8f0;
}
.welcome-banner h2 { margin: 0 0 6px; font-size: 20px; }
.welcome-banner p { margin: 0; color: #718096; font-size: 13px; }
.welcome-icon { font-size: 36px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: all 0.22s ease;
  cursor: default;
  border: 1px solid transparent;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.10);
  border-color: #e8f4fd;
}
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.stat-info { display: flex; flex-direction: column; gap: 2px; }
.stat-value { font-size: 28px; font-weight: 700; color: #2d3447; line-height: 1; }
.stat-label { font-size: 12px; color: #718096; }

.section { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section-title { margin: 0 0 16px; font-size: 15px; font-weight: 600; color: #2d3447; }

.actions-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.action-card {
  display: flex; align-items: center; gap: 14px;
  padding: 16px; border-radius: 10px;
  border: 1px solid #e8eaed; cursor: pointer;
  transition: all 0.22s cubic-bezier(.4,0,.2,1);
  background: #fff;
}
.action-card:hover {
  border-color: #4fc3f7;
  background: linear-gradient(135deg, #f0f9ff, #e8f5fe);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(79,195,247,0.15);
}
.action-card:hover .action-arrow { color: #4fc3f7; transform: translateX(3px); }
.action-icon { font-size: 28px; }
.action-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.action-title { font-size: 14px; font-weight: 600; color: #2d3447; }
.action-desc { font-size: 12px; color: #718096; }
.action-arrow { color: #a0aec0; transition: all 0.22s ease; }

.view-more { text-align: right; margin-top: 12px; }
</style>
