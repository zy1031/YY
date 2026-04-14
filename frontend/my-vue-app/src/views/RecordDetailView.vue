<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { detectionApi } from '../api/detection'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const record = ref<any>(null)
const results = ref<any[]>([])

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) {
    router.push('/records')
    return
  }

  loading.value = true
  try {
    const res: any = await detectionApi.getResults(id)
    record.value = res.record
    results.value = res.results
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
    router.push('/records')
  } finally {
    loading.value = false
  }
})

function healthTagType(s: string) {
  return s === 'normal' ? 'success' : s === 'suspicious' ? 'warning' : 'danger'
}

function healthLabel(s: string) {
  return s === 'normal' ? '正常' : s === 'suspicious' ? '可疑' : '异常'
}
</script>

<template>
  <div class="detail-page" v-loading="loading">
    <div class="page-header">
      <el-button link @click="router.push('/records')">← 返回列表</el-button>
      <h2 v-if="record">检测详情 #{{ record.id }}</h2>
    </div>

    <template v-if="record">
      <div class="summary-card">
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">检测类型</span>
            <span class="value">
              {{ record.detection_type === 'image' ? '图片行为识别' : record.detection_type === 'video' ? '视频检测' : '实时监控' }}
            </span>
          </div>
          <div class="summary-item"><span class="label">动物类型</span><span class="value">{{ record.animal_type || '-' }}</span></div>
          <div class="summary-item"><span class="label">状态</span><span class="value">{{ record.detection_status === 'completed' ? '已完成' : '失败' }}</span></div>
          <div class="summary-item"><span class="label">检测时间</span><span class="value">{{ record.created_at }}</span></div>
          <div class="summary-item"><span class="label">处理耗时</span><span class="value">{{ record.processing_time }}ms</span></div>
        </div>

        <div v-if="record.detection_type !== 'image'" class="stat-row">
          <div class="stat-box"><span class="sn">{{ record.total_targets }}</span><span class="sl">总目标</span></div>
          <div class="stat-box normal"><span class="sn">{{ record.normal_count }}</span><span class="sl">正常</span></div>
          <div class="stat-box suspicious"><span class="sn">{{ record.suspicious_count }}</span><span class="sl">可疑</span></div>
          <div class="stat-box abnormal"><span class="sn">{{ record.abnormal_count }}</span><span class="sl">异常</span></div>
        </div>

        <div v-else class="stat-row single">
          <div class="stat-box"><span class="sn">{{ record.total_targets }}</span><span class="sl">识别目标</span></div>
        </div>
      </div>

      <div class="results-card">
        <h3>{{ record.detection_type === 'image' ? '行为识别详情' : '检测目标详情' }}</h3>
        <el-empty v-if="results.length === 0" description="暂无检测目标" />
        <el-table v-else :data="results" border style="width: 100%">
          <el-table-column prop="target_index" label="序号" width="70" align="center">
            <template #default="{ row }">{{ row.target_index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="class_name" :label="record.detection_type === 'image' ? '行为类别' : '类别'" />
          <el-table-column v-if="record.detection_type !== 'image'" label="健康状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="healthTagType(row.health_status)">{{ healthLabel(row.health_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="100" align="center">
            <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
          </el-table-column>
          <el-table-column label="边界框" min-width="200">
            <template #default="{ row }">({{ row.bbox_x1 }}, {{ row.bbox_y1 }}) → ({{ row.bbox_x2 }}, {{ row.bbox_y2 }})</template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:16px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; }
.summary-card { background:#fff; border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.summary-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:16px; margin-bottom:20px; }
.summary-item { display:flex; flex-direction:column; gap:4px; }
.label { font-size:12px; color:#718096; }
.value { font-size:14px; font-weight:600; color:#2d3447; }
.stat-row { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.stat-row.single { grid-template-columns:minmax(180px, 240px); }
.stat-box { background:#f7f8fa; border-radius:10px; padding:16px; text-align:center; display:flex; flex-direction:column; gap:4px; }
.stat-box.normal { background:#f0fff4; }
.stat-box.suspicious { background:#fffbeb; }
.stat-box.abnormal { background:#fff5f5; }
.sn { font-size:28px; font-weight:700; color:#2d3447; line-height:1; }
.stat-box.normal .sn { color:#48bb78; }
.stat-box.suspicious .sn { color:#ed8936; }
.stat-box.abnormal .sn { color:#f56565; }
.sl { font-size:12px; color:#718096; }
.results-card { background:#fff; border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.results-card h3 { margin:0 0 16px; font-size:15px; font-weight:600; }
</style>
