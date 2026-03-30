<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { videoApi } from '../api/video'
import { modelsApi } from '../api/detection'

const animalTypes = ref<any[]>([])
const selectedAnimalType = ref<number | null>(null)
const sampleInterval = ref(5)
const uploadedFilePath = ref('')
const uploadedFileName = ref('')
const uploading = ref(false)
const taskId = ref('')
const taskStatus = ref('')
const taskProgress = ref(0)
const detecting = ref(false)
const detectResult = ref<any>(null)
const historyRecords = ref<any[]>([])
const historyLoading = ref(false)
const activeTab = ref('detect')
const tracksDialogVisible = ref(false)
const tracks = ref<any[]>([])
const tracksLoading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const res: any = await modelsApi.getAnimalTypes()
    animalTypes.value = res.animal_types || []
  } catch {}
})
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

function handleFileChange(uploadFile: any) {
  const file: File = uploadFile.raw
  if (!file) return
  uploadedFileName.value = file.name
  uploadedFilePath.value = ''
  detectResult.value = null
  taskStatus.value = ''
  doUpload(file)
}
async function doUpload(file: File) {
  uploading.value = true
  try {
    const res: any = await videoApi.upload(file)
    uploadedFilePath.value = res.file_path
    ElMessage.success('视频上传成功')
  } catch (e: any) {
    ElMessage.error(e || '上传失败')
  } finally { uploading.value = false }
}
async function handleDetect() {
  if (!uploadedFilePath.value) { ElMessage.warning('请先上传视频'); return }
  detecting.value = true
  taskStatus.value = 'pending'
  taskProgress.value = 0
  detectResult.value = null
  try {
    const res: any = await videoApi.detect(
      uploadedFilePath.value,
      selectedAnimalType.value ?? undefined,
      sampleInterval.value
    )
    taskId.value = res.task_id
    ElMessage.success('检测任务已提交，后台处理中...')
    startPolling()
  } catch (e: any) {
    ElMessage.error(e || '提交失败')
    detecting.value = false
  }
}
function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const res: any = await videoApi.getTaskProgress(taskId.value)
      taskStatus.value = res.status
      taskProgress.value = res.progress
      if (res.status === 'completed') {
        detecting.value = false
        detectResult.value = res.result
        clearInterval(pollTimer!)
        ElMessage.success('视频检测完成！')
        fetchHistory()
      } else if (res.status === 'failed') {
        detecting.value = false
        clearInterval(pollTimer!)
        ElMessage.error('检测失败: ' + res.error)
      }
    } catch {}
  }, 1500)
}
async function fetchHistory() {
  historyLoading.value = true
  try {
    const res: any = await videoApi.listRecords()
    historyRecords.value = res.records || []
  } catch {} finally { historyLoading.value = false }
}
async function viewTracks(recordId: number) {
  tracksLoading.value = true
  tracksDialogVisible.value = true
  tracks.value = []
  try {
    const res: any = await videoApi.getTracks(recordId)
    tracks.value = res.tracks || []
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
  } finally { tracksLoading.value = false }
}
function handleTabChange(tab: string) { if (tab === 'history') fetchHistory() }
function statusLabel(s: string) {
  return ({pending:'等待中',running:'检测中',completed:'已完成',failed:'失败'} as any)[s] || s
}
function statusType(s: string) {
  return ({pending:'info',running:'warning',completed:'success',failed:'danger'} as any)[s] || 'info'
}
function healthLabel(s: string) { return s==='normal'?'正常':s==='suspicious'?'可疑':'异常' }
function healthType(s: string) { return s==='normal'?'success':s==='suspicious'?'warning':'danger' }
</script>

<template>
  <div class="video-page">
    <div class="page-header">
      <h2>🎬 视频检测</h2>
      <p>上传视频，AI 逐帧分析 + BoT-SORT 目标跟踪</p>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" @tab-click="(t:any) => handleTabChange(t.paneName)">
      <el-tab-pane label="新建检测" name="detect">
        <div class="detect-layout">
          <div class="left-panel">
            <div class="card">
              <h3 class="card-title">检测配置</h3>
              <el-form label-width="90px">
                <el-form-item label="动物类型">
                  <el-select v-model="selectedAnimalType" placeholder="请选择" clearable style="width:100%">
                    <el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="采样间隔">
                  <el-input-number v-model="sampleInterval" :min="1" :max="30" style="width:100%" />
                  <span style="font-size:12px;color:#a0aec0">每隔 {{ sampleInterval }} 帧采样</span>
                </el-form-item>
              </el-form>
            </div>
            <div class="card">
              <h3 class="card-title">上传视频</h3>
              <el-upload :auto-upload="false" :show-file-list="false" accept="video/*"
                :on-change="handleFileChange" drag class="video-uploader">
                <div class="upload-placeholder">
                  <el-icon style="font-size:48px;color:#cbd5e0"><VideoPlay /></el-icon>
                  <p v-if="!uploadedFileName">拖拽视频或 <em>点击上传</em></p>
                  <p v-else style="color:#4fc3f7;font-weight:600">📹 {{ uploadedFileName }}</p>
                  <p style="font-size:12px;color:#a0aec0">MP4 / AVI / MKV</p>
                </div>
              </el-upload>
              <div v-if="uploading" style="margin-top:10px;font-size:13px;color:#718096">⏳ 上传中...</div>
              <div v-else-if="uploadedFilePath" style="margin-top:10px;font-size:13px;color:#48bb78">✅ 视频已就绪</div>
            </div>
            <el-button type="primary" size="large" :loading="detecting"
              :disabled="!uploadedFilePath || uploading" class="detect-btn" @click="handleDetect">
              {{ detecting ? '检测中...' : '开始检测' }}
            </el-button>
          </div>

          <div class="right-panel">
            <div v-if="!detecting && !taskStatus" class="result-placeholder">
              <span style="font-size:64px">🎬</span>
              <p>上传视频后点击「开始检测」</p>
            </div>
            <div v-if="detecting || (taskStatus && taskStatus !== 'completed' && taskStatus !== 'failed')" class="progress-box">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <span style="font-weight:600">检测进度</span>
                <el-tag :type="statusType(taskStatus)" size="small">{{ statusLabel(taskStatus) }}</el-tag>
              </div>
              <el-progress :percentage="taskProgress"
                :status="taskStatus==='completed'?'success':taskStatus==='failed'?'exception':undefined"
                :striped="taskStatus==='running'" :striped-flow="taskStatus==='running'"
                :stroke-width="20" />
              <p style="font-size:13px;color:#718096;margin-top:10px">正在逐帧分析，BoT-SORT 跟踪中...</p>
            </div>
            <div v-if="detectResult" class="result-box">
              <el-alert v-if="detectResult.is_mock" type="warning" show-icon
                title="演示模式" description="模型未配置，为模拟结果" style="margin-bottom:14px" />
              <div class="result-stats">
                <div class="stat-item"><span class="sn">{{ detectResult.track_count }}</span><span class="sl">跟踪目标</span></div>
                <div class="stat-item normal"><span class="sn">{{ detectResult.normal_count }}</span><span class="sl">正常</span></div>
                <div class="stat-item suspicious"><span class="sn">{{ detectResult.suspicious_count }}</span><span class="sl">可疑</span></div>
                <div class="stat-item abnormal"><span class="sn">{{ detectResult.abnormal_count }}</span><span class="sl">异常</span></div>
              </div>
              <div class="result-meta">耗时 {{ detectResult.processing_time }}s ｜ 记录ID: {{ detectResult.record_id }}</div>
              <el-button type="primary" style="margin-top:12px" @click="viewTracks(detectResult.record_id)">查看轨迹详情</el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="历史记录" name="history">
        <el-table :data="historyRecords" v-loading="historyLoading" border style="width:100%">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="状态" width="100">
            <template #default="{row}"><el-tag :type="statusType(row.detection_status)" size="small">{{ statusLabel(row.detection_status) }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="total_targets" label="跟踪目标" width="100" align="center" />
          <el-table-column label="异常" width="80" align="center">
            <template #default="{row}"><span :style="{color:row.abnormal_count>0?'#f56565':'inherit'}">{{ row.abnormal_count }}</span></template>
          </el-table-column>
          <el-table-column prop="created_at" label="检测时间" min-width="160" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{row}">
              <el-button type="primary" link size="small" @click="viewTracks(row.id)">轨迹</el-button>
              <el-button v-if="row.has_result_video" type="success" link size="small" @click="videoApi.downloadVideo(row.id)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="tracksDialogVisible" title="跟踪轨迹详情" width="680px">
      <el-table :data="tracks" v-loading="tracksLoading" border style="width:100%">
        <el-table-column prop="track_id" label="轨迹ID" width="80" align="center" />
        <el-table-column label="健康状态" width="100" align="center">
          <template #default="{row}"><el-tag :type="healthType(row.health_status_summary)" size="small">{{ healthLabel(row.health_status_summary) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="start_frame" label="起始帧" width="90" align="center" />
        <el-table-column prop="end_frame" label="结束帧" width="90" align="center" />
        <el-table-column prop="total_frames" label="出现帧数" width="90" align="center" />
        <el-table-column label="平均置信度" align="center">
          <template #default="{row}">{{ row.avg_confidence ? (row.avg_confidence*100).toFixed(1)+'%' : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.video-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; } .page-header p { margin:0; color:#718096; font-size:13px; }
.main-tabs { background:#fff; border-radius:12px; padding:0 20px 20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.detect-layout { display:grid; grid-template-columns:300px 1fr; gap:16px; align-items:start; margin-top:16px; }
.card { background:#f7f8fa; border-radius:10px; padding:16px; margin-bottom:14px; }
.card-title { margin:0 0 12px; font-size:14px; font-weight:600; color:#2d3447; }
.video-uploader { width:100%; :deep(.el-upload-dragger) { width:100%; height:160px; display:flex; align-items:center; justify-content:center; border-radius:8px; } }
.upload-placeholder { text-align:center; color:#718096; }
.detect-btn { width:100%; height:44px; font-size:15px; background:linear-gradient(135deg,#4fc3f7,#0288d1); border:none; border-radius:10px; }
.right-panel { background:#f7f8fa; border-radius:10px; padding:20px; min-height:360px; }
.result-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; height:300px; color:#a0aec0; gap:12px; }
.progress-box { background:#fff; border-radius:10px; padding:20px; margin-bottom:16px; }
.result-box { background:#fff; border-radius:10px; padding:20px; }
.result-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:14px; }
.stat-item { background:#f7f8fa; border-radius:8px; padding:12px; text-align:center; display:flex; flex-direction:column; gap:4px; }
.stat-item.normal { background:#f0fff4; } .stat-item.suspicious { background:#fffbeb; } .stat-item.abnormal { background:#fff5f5; }
.sn { font-size:24px; font-weight:700; color:#2d3447; line-height:1; }
.stat-item.normal .sn { color:#48bb78; } .stat-item.suspicious .sn { color:#ed8936; } .stat-item.abnormal .sn { color:#f56565; }
.sl { font-size:12px; color:#718096; }
.result-meta { font-size:12px; color:#a0aec0; }
</style>