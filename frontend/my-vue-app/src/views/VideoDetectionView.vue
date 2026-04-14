<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { cameraApi } from '../api/camera'
import { modelsApi } from '../api/detection'
import { useAuthStore } from '../stores/auth'

type HealthStatus = 'normal' | 'suspicious' | 'abnormal'
interface AnimalType { id: number; name: string }
interface CameraStats { frame_count: number; total_targets: number; normal_count: number; suspicious_count: number; abnormal_count: number }
interface DetectionItem { target_index: number; track_id: number; class_name: string; confidence: number; health_status: HealthStatus; bbox_x1: number; bbox_y1: number; bbox_x2: number; bbox_y2: number }
interface SessionInfo { session_id: string; is_mock: boolean; animal_type: string; model_name: string }
interface WsResultMessage { type: 'result'; detections?: DetectionItem[]; stats: CameraStats; is_mock?: boolean }
interface WsStatusMessage { type: 'status'; status: string }
interface WsErrorMessage { type: 'error'; message: string }
type WsMessage = WsResultMessage | WsStatusMessage | WsErrorMessage

const W = 640
const H = 480
const emptyStats = (): CameraStats => ({ frame_count: 0, total_targets: 0, normal_count: 0, suspicious_count: 0, abnormal_count: 0 })
const authStore = useAuthStore()
const canReadModelConfig = computed(() => authStore.isAdmin)
const animalTypes = ref<AnimalType[]>([])
const selectedAnimalType = ref<number | null>(null)
const uploadedFileName = ref('')
const localVideoUrl = ref('')
const sessionInfo = ref<SessionInfo | null>(null)
const sessionId = ref('')
const isConnecting = ref(false)
const isRunning = ref(false)
const isPaused = ref(false)
const isMock = ref(false)
const stats = ref<CameraStats>(emptyStats())
const lastDetections = ref<DetectionItem[]>([])
const currentConclusion = ref<HealthStatus>('normal')
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
let ws: WebSocket | null = null
let timer: ReturnType<typeof setInterval> | null = null
let objectUrl: string | null = null
let offscreen: HTMLCanvasElement | null = null

const isVideoReady = computed(() => !!localVideoUrl.value)
const hasAbnormalAlert = computed(() => currentConclusion.value === 'abnormal')
const hasSuspiciousAlert = computed(() => currentConclusion.value === 'suspicious')
const connectionLabel = computed(() => {
  if (isConnecting.value) return '连接中'
  return isRunning.value ? (isPaused.value ? '已暂停' : '检测中') : sessionInfo.value ? '已停止' : '待启动'
})

onMounted(async () => {
  try {
    const res: any = await modelsApi.getAnimalTypes()
    animalTypes.value = res.animal_types || []
  } catch {}
})

onUnmounted(() => cleanup(true))

function handleFileChange(uploadFile: any) {
  const file: File = uploadFile.raw
  if (!file) return
  cleanup(false)
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  objectUrl = URL.createObjectURL(file)
  localVideoUrl.value = objectUrl
  uploadedFileName.value = file.name
  stats.value = emptyStats()
  lastDetections.value = []
  currentConclusion.value = 'normal'
}

async function handleStart() {
  if (!localVideoUrl.value) return ElMessage.warning('请先上传视频')
  if (!videoRef.value) return ElMessage.warning('视频播放器未就绪')
  isConnecting.value = true
  try {
    const res: any = await cameraApi.createSession(selectedAnimalType.value ?? undefined)
    sessionId.value = res.session_id
    sessionInfo.value = res
    isMock.value = res.is_mock
    ws = new WebSocket(cameraApi.getWsUrl(sessionId.value))
    ws.onopen = async () => {
      isConnecting.value = false
      isRunning.value = true
      isPaused.value = false
      videoRef.value!.currentTime = 0
      await videoRef.value!.play()
      startLoop()
      ElMessage.success('视频实时检测已启动')
    }
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as WsMessage
      if (msg.type === 'result') {
        lastDetections.value = msg.detections || []
        stats.value = msg.stats
        if (msg.stats.abnormal_count > 0) currentConclusion.value = 'abnormal'
        else if (msg.stats.suspicious_count > 0) currentConclusion.value = 'suspicious'
        else currentConclusion.value = 'normal'
        draw(msg.detections || [])
      }
      if (msg.type === 'error') ElMessage.error(msg.message)
    }
    ws.onclose = () => { stopLoop(); isRunning.value = false; isConnecting.value = false }
    ws.onerror = () => { isConnecting.value = false; ElMessage.error('实时连接失败') }
  } catch (e: any) {
    isConnecting.value = false
    ElMessage.error(e || '启动失败')
  }
}

function startLoop() {
  stopLoop()
  timer = setInterval(() => {
    if (!isRunning.value || isPaused.value) return
    if (videoRef.value?.ended) return handleStop()
    sendFrame()
  }, 250)
}
function stopLoop() { if (timer) { clearInterval(timer); timer = null } }
function sendFrame() {
  if (!ws || ws.readyState !== WebSocket.OPEN || !videoRef.value || videoRef.value.readyState < 2) return
  if (!offscreen) { offscreen = document.createElement('canvas'); offscreen.width = W; offscreen.height = H }
  const ctx = offscreen.getContext('2d'); if (!ctx) return
  ctx.drawImage(videoRef.value, 0, 0, W, H)
  ws.send(JSON.stringify({ type: 'frame', data: offscreen.toDataURL('image/jpeg', 0.72).split(',')[1] || '' }))
}
function draw(detections: DetectionItem[]) {
  const canvas = canvasRef.value; if (!canvas) return
  canvas.width = canvas.clientWidth || W; canvas.height = canvas.clientHeight || H
  const ctx = canvas.getContext('2d'); if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  const sx = canvas.width / W, sy = canvas.height / H
  const colors: Record<HealthStatus, string> = { normal: '#34d399', suspicious: '#f59e0b', abnormal: '#f87171' }
  detections.forEach((d) => {
    const x = d.bbox_x1 * sx, y = d.bbox_y1 * sy, w = (d.bbox_x2 - d.bbox_x1) * sx, h = (d.bbox_y2 - d.bbox_y1) * sy
    ctx.strokeStyle = colors[d.health_status]; ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h)
  })
}
function handlePause() { if (!ws) return; isPaused.value = true; videoRef.value?.pause(); ws.send(JSON.stringify({ type: 'control', action: 'pause' })) }
function handleResume() { if (!ws) return; isPaused.value = false; videoRef.value?.play(); ws.send(JSON.stringify({ type: 'control', action: 'resume' })) }
function handleStop() { if (ws) { ws.send(JSON.stringify({ type: 'control', action: 'stop' })); ws.close() } if (sessionId.value) cameraApi.stopSession(sessionId.value).catch(() => {}); cleanup(false) }
function cleanup(resetVideo: boolean) { stopLoop(); if (ws) { ws.close(); ws = null } isConnecting.value = false; isRunning.value = false; isPaused.value = false; sessionId.value = ''; sessionInfo.value = null; if (resetVideo) { if (objectUrl) URL.revokeObjectURL(objectUrl); objectUrl = null; localVideoUrl.value = ''; uploadedFileName.value = '' } }
function healthLabel(s: HealthStatus) { return s === 'normal' ? '正常' : s === 'suspicious' ? '可疑' : '异常' }
function healthTagType(s: HealthStatus) { return s === 'normal' ? 'success' : s === 'suspicious' ? 'warning' : 'danger' }
</script>

<template>
  <div class="video-page">
    <div class="page-header">
      <div>
        <h2>视频实时分析</h2>
        <p>上传本地视频后，直接在前端边播放边检测。</p>
      </div>
      <div class="header-tags">
        <el-tag type="info" effect="dark">{{ connectionLabel }}</el-tag>
        <el-tag type="primary">{{ canReadModelConfig ? '优先使用所选动物模型' : '自动按动物类型匹配模型' }}</el-tag>
        <el-tag v-if="isMock" type="warning">Mock 演示模式</el-tag>
      </div>
    </div>
    <div class="layout">
      <div class="main-card">
        <div class="toolbar">
          <el-upload :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="handleFileChange"><el-button>上传视频</el-button></el-upload>
          <el-button type="primary" :disabled="!isVideoReady || isRunning || isConnecting" @click="handleStart">{{ isConnecting ? '连接中...' : '开始检测' }}</el-button>
          <el-button v-if="isRunning && !isPaused" type="warning" @click="handlePause">暂停</el-button>
          <el-button v-if="isRunning && isPaused" type="success" @click="handleResume">继续</el-button>
          <el-button v-if="isRunning" type="danger" @click="handleStop">停止</el-button>
        </div>
        <div class="video-box">
          <video ref="videoRef" class="video" :src="localVideoUrl" controls muted playsinline />
          <canvas ref="canvasRef" class="overlay" />
          <div v-if="!localVideoUrl" class="placeholder">上传本地视频后开始检测</div>
          <div v-if="hasAbnormalAlert" class="alert-pill abnormal">检测到异常目标</div>
          <div v-else-if="hasSuspiciousAlert" class="alert-pill suspicious">检测到可疑目标</div>
        </div>
      </div>
      <div class="side-card">
        <el-form label-width="72px">
          <el-form-item label="文件"><div>{{ uploadedFileName || '未选择' }}</div></el-form-item>
          <el-form-item label="动物"><el-select v-model="selectedAnimalType" clearable style="width:100%"><el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" /></el-select></el-form-item>
        </el-form>
        <div class="stats">
          <div class="stat-line">结论：<el-tag :type="healthTagType(currentConclusion)">{{ healthLabel(currentConclusion) }}</el-tag></div>
          <div class="stat-grid">
            <div class="stat-item"><span class="num">{{ stats.frame_count }}</span><span class="label">检测帧</span></div>
            <div class="stat-item"><span class="num">{{ stats.total_targets }}</span><span class="label">累计目标</span></div>
            <div class="stat-item normal"><span class="num">{{ stats.normal_count }}</span><span class="label">正常</span></div>
            <div class="stat-item suspicious"><span class="num">{{ stats.suspicious_count }}</span><span class="label">可疑</span></div>
            <div class="stat-item abnormal"><span class="num">{{ stats.abnormal_count }}</span><span class="label">异常</span></div>
          </div>
        </div>
        <div class="targets">
          <div class="title">当前帧目标 ({{ lastDetections.length }})</div>
          <div v-if="lastDetections.length === 0" class="empty">等待检测结果...</div>
          <div v-for="det in lastDetections" :key="`${det.track_id}-${det.target_index}`" class="target-item" :class="det.health_status">
            <div class="target-top"><span>#{{ det.track_id }}</span><el-tag :type="healthTagType(det.health_status)" size="small">{{ healthLabel(det.health_status) }}</el-tag></div>
            <div class="target-meta">{{ det.class_name }} · {{ (det.confidence * 100).toFixed(0) }}%</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.video-page{display:flex;flex-direction:column;gap:16px}.page-header,.main-card,.side-card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 6px 18px rgba(15,23,42,.08)}.page-header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;background:linear-gradient(135deg,#0b1320,#17304d);color:#fff}.page-header p{margin:6px 0 0;color:#bfd0e4}.header-tags{display:flex;gap:8px;flex-wrap:wrap}.layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:16px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}.video-box{position:relative;aspect-ratio:16/9;background:#000;border-radius:14px;overflow:hidden}.video,.overlay{position:absolute;inset:0;width:100%;height:100%}.video{object-fit:contain}.overlay{pointer-events:none}.placeholder{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#cbd5e1;background:rgba(2,6,23,.58)}.alert-pill{position:absolute;top:12px;left:12px;padding:8px 12px;border-radius:999px;color:#fff;font-size:12px;font-weight:700}.alert-pill.abnormal{background:#ef4444}.alert-pill.suspicious{background:#f59e0b}.stats,.targets{display:flex;flex-direction:column;gap:12px;margin-top:14px}.stat-line{display:flex;align-items:center;gap:8px}.stat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.stat-item{background:#f8fafc;border-radius:10px;padding:10px;text-align:center;display:flex;flex-direction:column}.stat-item.normal{background:#ecfdf5}.stat-item.suspicious{background:#fffbeb}.stat-item.abnormal{background:#fef2f2}.num{font-size:22px;font-weight:800}.label{font-size:11px;color:#64748b}.title{font-weight:700}.empty{font-size:13px;color:#94a3b8}.target-item{padding:10px;border-radius:10px;background:#f8fafc}.target-item.normal{background:#f0fdf4}.target-item.suspicious{background:#fffbeb}.target-item.abnormal{background:#fef2f2}.target-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}.target-meta{font-size:12px;color:#475569}
</style>
