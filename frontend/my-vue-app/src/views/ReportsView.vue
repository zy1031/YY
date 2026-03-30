<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reportsApi } from '../api/reports'
import { detectionApi } from '../api/detection'

const router = useRouter()
const loading = ref(false)
const reports = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const genDialogVisible = ref(false)
const genRecordId = ref<number | null>(null)
const recentRecords = ref<any[]>([])
const generating = ref(false)
const genTaskId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => { fetchReports(); fetchRecentRecords() })

async function fetchReports() {
  loading.value = true
  try {
    const res: any = await reportsApi.list(page.value, pageSize.value)
    reports.value = res.reports || []
    total.value = res.total || 0
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
  } finally { loading.value = false }
}

async function fetchRecentRecords() {
  try {
    const res: any = await detectionApi.getHistory({ page: 1, page_size: 20 })
    recentRecords.value = (res.history || []).filter((r: any) => r.detection_status === 'completed')
  } catch {}
}

async function handleGenerate() {
  if (!genRecordId.value) { ElMessage.warning('请选择检测记录'); return }
  generating.value = true
  try {
    const res: any = await reportsApi.generate(genRecordId.value)
    genTaskId.value = res.task_id
    ElMessage.success('报告生成任务已提交')
    startPoll()
  } catch (e: any) {
    ElMessage.error(e || '提交失败')
    generating.value = false
  }
}

function startPoll() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const res: any = await reportsApi.getTask(genTaskId.value)
      if (res.status === 'completed') {
        clearInterval(pollTimer!)
        generating.value = false
        genDialogVisible.value = false
        ElMessage.success('报告生成成功！')
        fetchReports()
      } else if (res.status === 'failed') {
        clearInterval(pollTimer!)
        generating.value = false
        ElMessage.error('报告生成失败: ' + res.error)
      }
    } catch {}
  }, 1500)
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确定删除该报告？', '提示', { type: 'warning' })
  try {
    await reportsApi.delete(id)
    ElMessage.success('删除成功')
    fetchReports()
  } catch (e: any) {
    ElMessage.error(e || '删除失败')
  }
}

function handlePageChange(p: number) { page.value = p; fetchReports() }
function statusLabel(s: string) {
  return ({pending:'等待中',generating:'生成中',completed:'已完成',failed:'失败'} as any)[s] || s
}
function statusType(s: string) {
  return ({pending:'info',generating:'warning',completed:'success',failed:'danger'} as any)[s] || 'info'
}
function healthType(s: string) {
  return s === '正常' ? 'success' : s === '需关注' ? 'warning' : s === '警告' ? 'danger' : 'info'
}
function typeLabel(t: string) {
  return t === 'image' ? '图片' : t === 'video' ? '视频' : '摄像头'
}
function recordLabel(r: any) {
  return `#${r.id} - ${typeLabel(r.detection_type)} - ${r.created_at?.slice(0,10)}`
}
</script>

<template>
  <div class="reports-page">
    <div class="page-header">
      <h2>📄 检测报告</h2>
      <p>AI 自动生成的动物健康分析报告</p>
      <el-button type="primary" @click="genDialogVisible = true">+ 生成新报告</el-button>
    </div>

    <div class="table-card">
      <el-table :data="reports" v-loading="loading" border style="width:100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="标题" min-width="180">
          <template #default="{row}"><span style="font-weight:500">{{ row.report_title || '未命名报告' }}</span></template>
        </el-table-column>
        <el-table-column label="类型" width="90" align="center">
          <template #default="{row}"><el-tag size="small">{{ typeLabel(row.report_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{row}">
            <el-tag :type="statusType(row.generation_status)" size="small">{{ statusLabel(row.generation_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="健康评级" width="100" align="center">
          <template #default="{row}">
            <el-tag v-if="row.health_assessment" :type="healthType(row.health_assessment)" size="small">{{ row.health_assessment }}</el-tag>
            <span v-else style="color:#a0aec0">-</span>
          </template>
        </el-table-column>
        <el-table-column label="摘要" min-width="180">
          <template #default="{row}"><span style="font-size:12px;color:#718096">{{ row.summary ? row.summary.slice(0,60)+'...' : '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="160" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{row}">
            <el-button type="primary" link size="small"
              :disabled="row.generation_status !== 'completed'"
              @click="router.push('/reports/' + row.id)">查看</el-button>
            <el-button type="success" link size="small"
              :disabled="row.generation_status !== 'completed'"
              @click="reportsApi.download(row.id)">下载MD</el-button>
            <el-button type="warning" link size="small"
              :disabled="row.generation_status !== 'completed'"
              @click="reportsApi.downloadPdf(row.id)">下载PDF</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" style="margin-top:16px;justify-content:flex-end"
        @current-change="handlePageChange" />
    </div>

    <!-- 生成报告弹窗 -->
    <el-dialog v-model="genDialogVisible" title="生成检测报告" width="480px">
      <p style="color:#718096;font-size:13px;margin-bottom:16px">
        选择已完成的检测记录，AI 将自动分析并生成健康报告
      </p>
      <el-select v-model="genRecordId" placeholder="请选择检测记录" style="width:100%" filterable>
        <el-option v-for="r in recentRecords" :key="r.id" :label="recordLabel(r)" :value="r.id">
          <span>{{ recordLabel(r) }}</span>
          <span style="float:right;font-size:12px;color:#a0aec0">{{ r.total_targets }}目标/{{ r.abnormal_count }}异常</span>
        </el-option>
      </el-select>
      <div v-if="generating" style="margin-top:16px;display:flex;align-items:center;gap:10px;color:#718096;font-size:13px">
        <el-icon class="is-loading"><Loading /></el-icon> AI 正在生成报告，请稍候...
      </div>
      <template #footer>
        <el-button @click="genDialogVisible = false" :disabled="generating">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">{{ generating ? '生成中...' : '开始生成' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.reports-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; } .page-header p { margin:0; color:#718096; font-size:13px; flex:1; }
.table-card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
</style>