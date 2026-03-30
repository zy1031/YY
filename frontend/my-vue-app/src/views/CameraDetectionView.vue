<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { cameraApi } from '../api/camera'
import { modelsApi } from '../api/detection'

// 配置
const animalTypes = ref<any[]>([])
const selectedAnimalType = ref<number | null>(null)
const selectedCamera = ref(0)
const availableCameras = ref<{id: number, label: string}[]>([
  { id: 0, label: '默认摄像头 (0)' },
  { id: 1, label: '摄像头 1' },
  { id: 2, label: '摄像头 2' },
])

// 状态
const sessionId = ref('')
const sessionInfo = ref<any>(null)
const isConnected = ref(false)
const isRunning = ref(false)
const isPaused = ref(false)
const isMock = ref(false)

// 统计
const stats = ref({
  frame_count: 0,
  total_targets: 0,
  normal_count: 0,
  suspicious_count: 0,
  abnormal_count: 0,
})
const lastDetections = ref<any[]>([])
const screenshotList = ref<string[]>([])

// Refs
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const offscreenCanvas = ref<HTMLCanvasElement | null>(null)

let ws: WebSocket | null = null
let mediaStream: MediaStream | null = null
let frameTimer: ReturnType<typeof setInterval> | null = null
const FRAME_INTERVAL = 200  // 每200ms发送一帧（5fps检测）

onMounted(async () => {
  try {
    const res: any = await modelsApi.getAnimalTypes()
    animalTypes.value = res.animal_types || []
  } catch {}
})

onUnmounted(() => {
  cleanup()
})

async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: selectedCamera.value ? { exact: String(selectedCamera.value) } : undefined }
    })
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
      await videoRef.value.play()
    }
    // 创建离屏 Canvas
    offscreenCanvas.value = document.createElement('canvas')
    offscreenCanvas.value.width = 640
    offscreenCanvas.value.height = 480
    ElMessage.success('摄像头已连接')
    return true
  } catch (e: any) {
    ElMessage.error('无法访问摄像头，将使用模拟模式')
    return false  // 摄像头失败时仍可 mock
  }
}

async function handleStart() {
  // 创建检测会话
  try {
    const res: any = await cameraApi.createSession(selectedAnimalType.value ?? undefined)
    sessionId.value = res.session_id
    sessionInfo.value = res
    isMock.value = res.is_mock
  } catch (e: any) {
    ElMessage.error(e || '创建会话失败')
    return
  }

  // 启动摄像头
  await startCamera()

  // 连接 WebSocket
  connectWs()
}

function connectWs() {
  const url = cameraApi.getWsUrl(sessionId.value)
  ws = new WebSocket(url)

  ws.onopen = () => {
    isConnected.value = true
    isRunning.value = true
    isPaused.value = false
    ElMessage.success('检测已启动')
    startFrameCapture()
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'result') {
      lastDetections.value = msg.detections || []
      stats.value = msg.stats
      drawDetections(msg.detections || [])
    } else if (msg.type === 'status') {
      // 状态更新
    } else if (msg.type === 'screenshot') {
      screenshotList.value.push(msg.filename)
      ElMessage.success('截图已保存: ' + msg.filename)
    } else if (msg.type === 'error') {
      ElMessage.error(msg.message)
    }
  }

  ws.onclose = () => {
    isConnected.value = false
    isRunning.value = false
    stopFrameCapture()
  }

  ws.onerror = () => {
    ElMessage.error('WebSocket 连接错误')
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
  if (frameTimer) { clearInterval(frameTimer); frameTimer = null }
}

function sendFrame() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  const oc = offscreenCanvas.value
  const video = videoRef.value
  if (oc && video && video.readyState >= 2) {
    const ctx = oc.getContext('2d')!
    ctx.drawImage(video, 0, 0, oc.width, oc.height)
    const base64 = oc.toDataURL('image/jpeg', 0.6).split(',')[1]
    ws.send(JSON.stringify({ type: 'frame', data: base64 }))
  } else {
    // 无摄像头时发空帧（触发 mock）
    ws.send(JSON.stringify({ type: 'frame', data: '' }))
  }
}

function drawDetections(detections: any[]) {
  const canvas = canvasRef.value
  const video = videoRef.value
  if (!canvas) return
  const w = canvas.offsetWidth || 640
  const h = canvas.offsetHeight || 480
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')!
  ctx.clearRect(0, 0, w, h)

  // 如果有视频，将视频帧绘制到 canvas
  if (video && video.readyState >= 2) {
    ctx.drawImage(video, 0, 0, w, h)
  } else {
    ctx.fillStyle = '#1a2a3a'
    ctx.fillRect(0, 0, w, h)
    ctx.fillStyle = '#a0aec0'
    ctx.font = '18px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('摄像头未连接（Mock模式）', w / 2, h / 2)
  }

  const colorMap: Record<string, string> = {
    normal: '#48bb78', suspicious: '#ed8936', abnormal: '#f56565'
  }
  const labelMap: Record<string, string> = {
    normal: '正常', suspicious: '可疑', abnormal: '异常'
  }

  // 坐标缩放比例（mock 坐标基于 640x480）
  const scaleX = w / 640
  const scaleY = h / 480

  for (const det of detections) {
    const color = colorMap[det.health_status] || '#aaa'
    const x1 = det.bbox_x1 * scaleX
    const y1 = det.bbox_y1 * scaleY
    const x2 = det.bbox_x2 * scaleX
    const y2 = det.bbox_y2 * scaleY
    const label = `ID:${det.track_id} ${det.class_name} ${(det.confidence * 100).toFixed(0)}% [${labelMap[det.health_status]}]`

    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    ctx.font = '13px sans-serif'
    const tw = ctx.measureText(label).width
    const ly = Math.max(y1 - 4, 18)
    ctx.fillStyle = color
    ctx.fillRect(x1, ly - 16, tw + 8, 20)
    ctx.fillStyle = '#fff'
    ctx.fillText(label, x1 + 4, ly)
  }
}

function handlePause() {
  if (!ws) return
  isPaused.value = true
  ws.send(JSON.stringify({ type: 'control', action: 'pause' }))
}
function handleResume() {
  if (!ws) return
  isPaused.value = false
  ws.send(JSON.stringify({ type: 'control', action: 'resume' }))
}
function handleStop() {
  if (ws) {
    ws.send(JSON.stringify({ type: 'control', action: 'stop' }))
    ws.close()
  }
  cleanup()
  cameraApi.stopSession(sessionId.value).catch(() => {})
  sessionId.value = ''
  ElMessage.info('检测已停止')
}
function handleScreenshot() {
  if (!ws || !ws.OPEN) return
  const oc = offscreenCanvas.value
  const video = videoRef.value
  let frameData = ''
  if (oc && video && video.readyState >= 2) {
    const ctx = oc.getContext('2d')!
    ctx.drawImage(video, 0, 0, oc.width, oc.height)
    frameData = oc.toDataURL('image/jpeg', 0.9).split(',')[1]
  }
  ws.send(JSON.stringify({ type: 'control', action: 'screenshot', frame_data: frameData }))
}
function cleanup() {
  stopFrameCapture()
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null }
  if (ws) { ws.close(); ws = null }
  isRunning.value = false
  isPaused.value = false
  isConnected.value = false
}
function handleReset() {
  stats.value = { frame_count: 0, total_targets: 0, normal_count: 0, suspicious_count: 0, abnormal_count: 0 }
  lastDetections.value = []
  screenshotList.value = []
  sessionId.value = ''
  sessionInfo.value = null
  const canvas = canvasRef.value
  if (canvas) {
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
  }
}
function healthTagType(s: string) {
  return s === 'normal' ? 'success' : s === 'suspicious' ? 'warning' : 'danger'
}
function healthLabel(s: string) {
  return s === 'normal' ? '正常' : s === 'suspicious' ? '可疑' : '异常'
}
</script>

<template>
  <div class="camera-page">
    <div class="page-header">
      <h2>📷 摄像头实时检测</h2>
      <p>实时视频流 + AI 检测 + BoT-SORT 目标跟踪</p>
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
            </el-form-item>
          </el-form>
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