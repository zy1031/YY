<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { cameraApi } from '../api/camera'
import { modelsApi } from '../api/detection'
import { useAuthStore } from '../stores/auth'

type HealthStatus = 'normal' | 'suspicious' | 'abnormal'

interface AnimalType {
  id: number
  name: string
}

interface CameraOption {
  id: string
  label: string
}

interface SessionInfo {
  session_id: string
  is_mock: boolean
  animal_type: string
  model_name: string
}

interface CameraStats {
  frame_count: number
  total_targets: number
  normal_count: number
  suspicious_count: number
  abnormal_count: number
}

interface DetectionItem {
  target_index: number
  track_id: number
  class_name: string
  confidence: number
  health_status: HealthStatus
  bbox_x1: number
  bbox_y1: number
  bbox_x2: number
  bbox_y2: number
}

interface WsResultMessage {
  type: 'result'
  detections?: DetectionItem[]
  stats: CameraStats
  is_mock?: boolean
}

interface WsStatusMessage {
  type: 'status'
  status: string
}

interface WsScreenshotMessage {
  type: 'screenshot'
  filename: string
}

interface WsErrorMessage {
  type: 'error'
  message: string
}

type WsMessage = WsResultMessage | WsStatusMessage | WsScreenshotMessage | WsErrorMessage

const emptyStats = (): CameraStats => ({
  frame_count: 0,
  total_targets: 0,
  normal_count: 0,
  suspicious_count: 0,
  abnormal_count: 0,
})

const authStore = useAuthStore()
const canReadModelConfig = computed(() => authStore.isAdmin)
const animalTypes = ref<AnimalType[]>([])
const selectedAnimalType = ref<number | null>(null)
const selectedCamera = ref('default')
const availableCameras = ref<CameraOption[]>([{ id: 'default', label: '默认摄像头' }])

const sessionId = ref('')
const sessionInfo = ref<SessionInfo | null>(null)
const isConnected = ref(false)
const isRunning = ref(false)
const isPaused = ref(false)
const isMock = ref(false)
const connectionStatus = ref<'idle' | 'connecting' | 'running' | 'paused' | 'stopped' | 'error'>('idle')
const currentConclusion = ref<HealthStatus>('normal')

const stats = ref<CameraStats>(emptyStats())
const lastDetections = ref<DetectionItem[]>([])
const screenshotList = ref<string[]>([])

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const offscreenCanvas = ref<HTMLCanvasElement | null>(null)

let ws: WebSocket | null = null
let mediaStream: MediaStream | null = null
let frameTimer: ReturnType<typeof setInterval> | null = null
const FRAME_INTERVAL = 250
const BASE_FRAME_WIDTH = 640
const BASE_FRAME_HEIGHT = 480

const hasAbnormalAlert = computed(() => currentConclusion.value === 'abnormal')
const hasSuspiciousAlert = computed(() => currentConclusion.value === 'suspicious')

onMounted(async () => {
  try {
    const [animalRes, cameraDevices] = await Promise.all([
      modelsApi.getAnimalTypes().catch(() => ({ animal_types: [] })),
      loadCameraOptions(),
    ])
    animalTypes.value = (animalRes as any).animal_types || []
    availableCameras.value = cameraDevices
  } catch {
    animalTypes.value = []
  }
  drawIdleState()
})

onUnmounted(() => {
  cleanup()
})

async function loadCameraOptions(): Promise<CameraOption[]> {
  if (!navigator.mediaDevices?.enumerateDevices) {
    return [{ id: 'default', label: '默认摄像头' }]
  }

  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    const cameras = devices
      .filter((d) => d.kind === 'videoinput')
      .map((d, index) => ({
        id: d.deviceId || `camera-${index}`,
        label: d.label || `摄像头 ${index + 1}`,
      }))
    return cameras.length ? [{ id: 'default', label: '默认摄像头' }, ...cameras] : [{ id: 'default', label: '默认摄像头' }]
  } catch {
    return [{ id: 'default', label: '默认摄像头' }]
  }
}

function updateConclusionFromStats(nextStats: CameraStats) {
  if (nextStats.abnormal_count > 0) currentConclusion.value = 'abnormal'
  else if (nextStats.suspicious_count > 0) currentConclusion.value = 'suspicious'
  else currentConclusion.value = 'normal'
}

function drawIdleState(message = '点击“开始检测”启动实时分析') {
  const canvas = canvasRef.value
  if (!canvas) return
  const width = canvas.clientWidth || BASE_FRAME_WIDTH
  const height = canvas.clientHeight || BASE_FRAME_HEIGHT
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  ctx.fillStyle = '#07111f'
  ctx.fillRect(0, 0, width, height)
  ctx.strokeStyle = 'rgba(120, 168, 255, 0.22)'
  for (let i = 0; i < width; i += 32) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i, height)
    ctx.stroke()
  }
  for (let i = 0; i < height; i += 32) {
    ctx.beginPath()
    ctx.moveTo(0, i)
    ctx.lineTo(width, i)
    ctx.stroke()
  }
  ctx.fillStyle = '#d7e3ff'
  ctx.font = '600 22px Microsoft YaHei'
  ctx.textAlign = 'center'
  ctx.fillText('LIVE ANALYSIS STANDBY', width / 2, height / 2 - 14)
  ctx.fillStyle = '#93a4c3'
  ctx.font = '14px Microsoft YaHei'
  ctx.fillText(message, width / 2, height / 2 + 18)
}

async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: selectedCamera.value !== 'default' ? { deviceId: { exact: selectedCamera.value } } : true,
      audio: false,
    })

    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      await videoRef.value.play()
    }

    offscreenCanvas.value = document.createElement('canvas')
    offscreenCanvas.value.width = BASE_FRAME_WIDTH
    offscreenCanvas.value.height = BASE_FRAME_HEIGHT
    ElMessage.success('摄像头已连接')
    return true
  } catch {
    ElMessage.warning('无法访问摄像头，将使用模拟模式持续演示')
    return false
  }
}

async function handleStart() {
  connectionStatus.value = 'connecting'
  try {
    const res: any = await cameraApi.createSession(selectedAnimalType.value ?? undefined)
    sessionId.value = res.session_id
    sessionInfo.value = res
    isMock.value = res.is_mock
  } catch (e: unknown) {
    connectionStatus.value = 'error'
    ElMessage.error((e as string) || '创建会话失败')
    return
  }

  await startCamera()
  connectWs()
}

function connectWs() {
  const url = cameraApi.getWsUrl(sessionId.value)
  ws = new WebSocket(url)

  ws.onopen = () => {
    isConnected.value = true
    isRunning.value = true
    isPaused.value = false
    connectionStatus.value = 'running'
    ElMessage.success('实时检测已启动')
    startFrameCapture()
  }

  ws.onmessage = (event: MessageEvent<string>) => {
    const msg = JSON.parse(event.data) as WsMessage

    if (msg.type === 'result') {
      lastDetections.value = msg.detections || []
      stats.value = msg.stats
      isMock.value = !!msg.is_mock || isMock.value
      updateConclusionFromStats(msg.stats)
      drawDetections(msg.detections || [])
      return
    }

    if (msg.type === 'status') {
      if (msg.status === 'paused') connectionStatus.value = 'paused'
      else if (msg.status === 'running') connectionStatus.value = 'running'
      else if (msg.status === 'stopped') connectionStatus.value = 'stopped'
      return
    }

    if (msg.type === 'screenshot') {
      screenshotList.value.unshift(msg.filename)
      ElMessage.success('截图已保存: ' + msg.filename)
      return
    }

    if (msg.type === 'error') {
      connectionStatus.value = 'error'
      ElMessage.error(msg.message)
    }
  }

  ws.onclose = () => {
    isConnected.value = false
    isRunning.value = false
    connectionStatus.value = connectionStatus.value === 'error' ? 'error' : 'stopped'
    stopFrameCapture()
  }

  ws.onerror = () => {
    connectionStatus.value = 'error'
    ElMessage.error('实时连接异常')
  }
}

function startFrameCapture() {
  if (frameTimer) clearInterval(frameTimer)
  frameTimer = setInterval(() => {
    if (!isRunning.value || isPaused.value) return
    sendFrame()
  }, FRAME_INTERVAL)
}

function stopFrameCapture() {
  if (frameTimer) {
    clearInterval(frameTimer)
    frameTimer = null
  }
}

function sendFrame() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return

  const oc = offscreenCanvas.value
  const video = videoRef.value

  if (oc && video && video.readyState >= 2) {
    const ctx = oc.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, oc.width, oc.height)
    const base64 = oc.toDataURL('image/jpeg', 0.72).split(',')[1] || ''
    ws.send(JSON.stringify({ type: 'frame', data: base64 }))
    return
  }

  ws.send(JSON.stringify({ type: 'frame', data: '' }))
}

function drawDetections(detections: DetectionItem[]) {
  const canvas = canvasRef.value
  if (!canvas) return

  const width = canvas.clientWidth || BASE_FRAME_WIDTH
  const height = canvas.clientHeight || BASE_FRAME_HEIGHT
  canvas.width = width
  canvas.height = height

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, width, height)

  if (!videoRef.value || videoRef.value.readyState < 2) {
    ctx.fillStyle = 'rgba(5, 10, 18, 0.6)'
    ctx.fillRect(0, 0, width, height)
    ctx.fillStyle = '#a0aec0'
    ctx.font = '18px Microsoft YaHei'
    ctx.textAlign = 'center'
    ctx.fillText('模拟模式实时检测中', width / 2, height / 2)
  }

  const colorMap: Record<HealthStatus, string> = {
    normal: '#34d399',
    suspicious: '#f59e0b',
    abnormal: '#f87171',
  }
  const labelMap: Record<HealthStatus, string> = {
    normal: '正常',
    suspicious: '可疑',
    abnormal: '异常',
  }

  const scaleX = width / BASE_FRAME_WIDTH
  const scaleY = height / BASE_FRAME_HEIGHT

  for (const det of detections) {
    const color = colorMap[det.health_status]
    const x1 = det.bbox_x1 * scaleX
    const y1 = det.bbox_y1 * scaleY
    const x2 = det.bbox_x2 * scaleX
    const y2 = det.bbox_y2 * scaleY
    const label = `#${det.track_id} ${det.class_name} ${(det.confidence * 100).toFixed(0)}% · ${labelMap[det.health_status]}`

    ctx.strokeStyle = color
    ctx.lineWidth = 2.5
    ctx.setLineDash([])
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    ctx.fillStyle = color
    ctx.font = '12px Microsoft YaHei'
    const textWidth = ctx.measureText(label).width
    const textY = Math.max(y1 - 8, 20)
    ctx.fillRect(x1, textY - 18, textWidth + 12, 22)
    ctx.fillStyle = '#ffffff'
    ctx.fillText(label, x1 + 6, textY - 2)
  }
}

function handlePause() {
  if (!ws) return
  isPaused.value = true
  connectionStatus.value = 'paused'
  ws.send(JSON.stringify({ type: 'control', action: 'pause' }))
}

function handleResume() {
  if (!ws) return
  isPaused.value = false
  connectionStatus.value = 'running'
  ws.send(JSON.stringify({ type: 'control', action: 'resume' }))
}

function handleStop() {
  if (ws) {
    ws.send(JSON.stringify({ type: 'control', action: 'stop' }))
    ws.close()
  }
  cameraApi.stopSession(sessionId.value).catch(() => {})
  cleanup()
  ElMessage.info('实时检测已停止')
}

function handleScreenshot() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return

  const oc = offscreenCanvas.value
  const video = videoRef.value
  let frameData = ''

  if (oc && video && video.readyState >= 2) {
    const ctx = oc.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, oc.width, oc.height)
    frameData = oc.toDataURL('image/jpeg', 0.9).split(',')[1] || ''
  }

  ws.send(JSON.stringify({ type: 'control', action: 'screenshot', frame_data: frameData }))
}

function cleanup() {
  stopFrameCapture()
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop())
    mediaStream = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  isRunning.value = false
  isPaused.value = false
  isConnected.value = false
  sessionId.value = ''
  sessionInfo.value = null
  connectionStatus.value = 'idle'
  drawIdleState()
}

function handleReset() {
  stats.value = emptyStats()
  lastDetections.value = []
  screenshotList.value = []
  currentConclusion.value = 'normal'
  handleStop()
}

function healthTagType(s: HealthStatus) {
  return s === 'normal' ? 'success' : s === 'suspicious' ? 'warning' : 'danger'
}

function healthLabel(s: HealthStatus) {
  return s === 'normal' ? '正常' : s === 'suspicious' ? '可疑' : '异常'
}

function connectionLabel() {
  return ({ idle: '待启动', connecting: '连接中', running: '检测中', paused: '已暂停', stopped: '已停止', error: '异常' } as const)[connectionStatus.value]
}

function connectionTagType() {
  return ({ idle: 'info', connecting: 'warning', running: 'success', paused: 'warning', stopped: 'info', error: 'danger' } as const)[connectionStatus.value]
}
</script>

<template>
  <div class="camera-page">
    <div class="page-header">
      <h2>📷 摄像头实时检测</h2>
      <p>实时视频流 + AI 检测 + BoT-SORT 目标跟踪</p>
      <el-tag type="primary" effect="dark">本次优先使用所选动物类型对应模型</el-tag>
      <el-tag v-if="isMock" type="warning">Mock 演示模式</el-tag>
      <el-tag v-else type="success">真实检测模式</el-tag>
    </div>

    <div class="main-layout">
      <!-- 左侧：视频+Canvas -->
      <div class="video-area">
        <div class="video-container">
          <video ref="videoRef" class="video-feed" autoplay muted playsinline />
          <canvas ref="canvasRef" class="canvas-overlay" />
          <div v-if="!isRunning" class="video-placeholder">
            <span style="font-size:56px">📷</span>
            <p>点击「开始检测」启动摄像头</p>
          </div>
        </div>

        <!-- 控制栏 -->
        <div class="control-bar">
          <!-- 未运行：开始按钮 -->
          <el-button v-if="!isRunning && !sessionId" type="primary" size="large" @click="handleStart">▶ 开始检测</el-button>

          <!-- 运行中：暂停/继续 + 截图 -->
          <template v-if="isRunning">
            <el-button v-if="!isPaused" type="warning" @click="handlePause">⏸ 暂停</el-button>
            <el-button v-else type="success" @click="handleResume">▶ 继续</el-button>
            <el-button @click="handleScreenshot">📸 截图</el-button>
          </template>

          <!-- 有会话时始终显示停止按钮 -->
          <el-button v-if="sessionId || isRunning" type="danger" @click="handleStop">⏹ 停止检测</el-button>

          <!-- 已停止但无会话：重新开始 -->
          <el-button v-if="!isRunning && !sessionId && stats.frame_count > 0" @click="handleReset">🔄 重置</el-button>
        </div>
      </div>

      <!-- 右侧：配置+统计+结果 -->
      <div class="side-panel">
        <!-- 配置 -->
        <div class="card" v-if="!isRunning">
          <h3 class="card-title">检测配置</h3>
          <el-form label-width="80px">
            <el-form-item label="摄像头">
              <el-select v-model="selectedCamera" style="width:100%">
                <el-option v-for="c in availableCameras" :key="c.id" :label="c.label" :value="c.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="动物类型">
              <el-select v-model="selectedAnimalType" placeholder="请选择" clearable style="width:100%">
                <el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
              <div class="form-hint">本次会优先使用所选动物类型对应模型；未匹配到时才回退到当前激活模型或 backend/models/best.pt。</div>
            </el-form-item>
          </el-form>
        </div>

        <!-- 实时统计 -->
        <div class="card" v-if="sessionInfo && !isRunning">
          <h3 class="card-title">会话信息</h3>
          <div class="session-meta">
            <div><span class="meta-label">动物类型</span><span class="meta-value">{{ sessionInfo.animal_type }}</span></div>
            <div><span class="meta-label">实际模型</span><span class="meta-value">{{ sessionInfo.model_name }}</span></div>
          </div>
        </div>

        <!-- 实时统计 -->
        <div class="card">
          <h3 class="card-title">实时统计</h3>
          <div class="stats-grid">
            <div class="stat-item"><span class="sn">{{ stats.frame_count }}</span><span class="sl">检测帧</span></div>
            <div class="stat-item"><span class="sn">{{ stats.total_targets }}</span><span class="sl">累计目标</span></div>
            <div class="stat-item normal"><span class="sn">{{ stats.normal_count }}</span><span class="sl">正常</span></div>
            <div class="stat-item suspicious"><span class="sn">{{ stats.suspicious_count }}</span><span class="sl">可疑</span></div>
            <div class="stat-item abnormal"><span class="sn">{{ stats.abnormal_count }}</span><span class="sl">异常</span></div>
          </div>
        </div>

        <!-- 当前帧检测结果 -->
        <div class="card">
          <h3 class="card-title">当前帧目标 ({{ lastDetections.length }})</h3>
          <div v-if="lastDetections.length === 0" style="color:#a0aec0;font-size:13px;text-align:center;padding:12px">
            {{ isRunning ? '当前帧无目标' : '等待检测...' }}
          </div>
          <div v-for="det in lastDetections" :key="det.target_index"
            class="det-item" :class="det.health_status">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <span style="font-weight:600;font-size:13px">ID: {{ det.track_id }}</span>
              <el-tag :type="healthTagType(det.health_status)" size="small">{{ healthLabel(det.health_status) }}</el-tag>
            </div>
            <div style="font-size:12px;color:#4a5568">{{ det.class_name }} · {{ (det.confidence*100).toFixed(0) }}%</div>
          </div>
        </div>

        <!-- 截图列表 -->
        <div class="card" v-if="screenshotList.length > 0">
          <h3 class="card-title">截图记录 ({{ screenshotList.length }})</h3>
          <div v-for="s in screenshotList" :key="s" style="font-size:12px;color:#718096;padding:2px 0">📸 {{ s }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.camera-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; } .page-header p { margin:0; color:#718096; font-size:13px; flex:1; }
.main-layout { display:grid; grid-template-columns:1fr 300px; gap:16px; align-items:start; }
.video-area { display:flex; flex-direction:column; gap:12px; }
.video-container { position:relative; background:#0f1923; border-radius:12px; overflow:hidden; aspect-ratio:4/3; }
.video-feed { width:100%; height:100%; object-fit:cover; display:block; }
.canvas-overlay { position:absolute; top:0; left:0; width:100%; height:100%; }
.video-placeholder { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#a0aec0; gap:12px; }
.control-bar { display:flex; gap:10px; justify-content:center; background:#fff; border-radius:10px; padding:14px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.side-panel { display:flex; flex-direction:column; gap:12px; }
.card { background:#fff; border-radius:12px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.card-title { margin:0 0 12px; font-size:14px; font-weight:600; color:#2d3447; }
.form-hint { margin-top: 6px; font-size: 12px; line-height: 1.6; color: #718096; }
.session-meta { display: flex; flex-direction: column; gap: 10px; }
.session-meta > div { display: flex; flex-direction: column; gap: 3px; }
.meta-label { font-size: 12px; color: #718096; }
.meta-value { font-size: 13px; font-weight: 600; color: #2d3447; word-break: break-all; }
.stats-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:8px; }
.stat-item { background:#f7f8fa; border-radius:8px; padding:10px; text-align:center; display:flex; flex-direction:column; gap:2px; }
.stat-item.normal { background:#f0fff4; } .stat-item.suspicious { background:#fffbeb; } .stat-item.abnormal { background:#fff5f5; }
.sn { font-size:22px; font-weight:700; color:#2d3447; line-height:1; }
.stat-item.normal .sn { color:#48bb78; } .stat-item.suspicious .sn { color:#ed8936; } .stat-item.abnormal .sn { color:#f56565; }
.sl { font-size:11px; color:#718096; }
.det-item { border:1px solid #e8eaed; border-radius:8px; padding:8px 12px; margin-bottom:8px; }
.det-item.normal { border-color:#9ae6b4; background:#f0fff4; }
.det-item.suspicious { border-color:#fbd38d; background:#fffbeb; }
.det-item.abnormal { border-color:#feb2b2; background:#fff5f5; }
</style>