<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { modelsApi, detectionApi } from '../api/detection'

const animalTypes = ref<any[]>([])
const selectedAnimalType = ref<number | null>(null)
const currentModel = ref<any>(null)
const uploadedFilePath = ref('')
const previewUrl = ref('')
const uploading = ref(false)
const detecting = ref(false)
const detectResult = ref<any>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)

onMounted(async () => {
  try {
    const [typesRes, modelRes]: any[] = await Promise.all([
      modelsApi.getAnimalTypes(),
      modelsApi.getCurrentModel(),
    ])
    animalTypes.value = typesRes.animal_types || []
    currentModel.value = modelRes.current_model
    if (currentModel.value) selectedAnimalType.value = currentModel.value.animal_type_id
  } catch {}
})

function handleFileChange(uploadFile: any) {
  const file: File = uploadFile.raw
  if (!file) return
  previewUrl.value = URL.createObjectURL(file)
  uploadedFilePath.value = ''
  detectResult.value = null
  doUpload(file)
}

async function doUpload(file: File) {
  uploading.value = true
  try {
    const res: any = await detectionApi.uploadImage(file)
    uploadedFilePath.value = res.file_path
    ElMessage.success('图片上传成功')
  } catch (e: any) {
    ElMessage.error(e || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleDetect() {
  if (!uploadedFilePath.value) { ElMessage.warning('请先上传图片'); return }
  detecting.value = true
  detectResult.value = null
  try {
    const res: any = await detectionApi.detectImage(uploadedFilePath.value, selectedAnimalType.value ?? undefined)
    detectResult.value = res
    ElMessage.success(`检测完成，发现 ${res.total_targets} 个目标`)
    await nextTick()
    drawBBoxes()
  } catch (e: any) {
    ElMessage.error(e || '检测失败')
  } finally {
    detecting.value = false
  }
}

function drawBBoxes() {
  const canvas = canvasRef.value
  const img = imageRef.value
  if (!canvas || !img || !detectResult.value) return

  canvas.width = img.naturalWidth || img.width
  canvas.height = img.naturalHeight || img.height
  const ctx = canvas.getContext('2d')!
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const colorMap: Record<string, string> = {
    normal: '#48bb78',
    suspicious: '#ed8936',
    abnormal: '#f56565',
  }
  const labelMap: Record<string, string> = {
    normal: '正常', suspicious: '可疑', abnormal: '异常'
  }

  for (const det of detectResult.value.detections) {
    const color = colorMap[det.health_status] || '#aaa'
    const x1 = det.bbox_x1, y1 = det.bbox_y1
    const x2 = det.bbox_x2, y2 = det.bbox_y2
    const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}% [${labelMap[det.health_status]}]`

    // 绘制边框
    ctx.strokeStyle = color
    ctx.lineWidth = Math.max(2, canvas.width / 300)
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

    // 绘制标签背景
    ctx.font = `${Math.max(12, canvas.width / 60)}px sans-serif`
    const tw = ctx.measureText(label).width
    const th = Math.max(16, canvas.width / 50)
    const ly = Math.max(y1 - 4, th)
    ctx.fillStyle = color
    ctx.fillRect(x1, ly - th, tw + 8, th + 4)

    // 绘制标签文字
    ctx.fillStyle = '#fff'
    ctx.fillText(label, x1 + 4, ly)
  }
}

function handleImageLoad() {
  if (detectResult.value) drawBBoxes()
}

function resetAll() {
  uploadedFilePath.value = ''
  previewUrl.value = ''
  detectResult.value = null
}

function downloadResult(id: number) {
  window.open(`http://localhost:8000/api/detection/${id}/download`, '_blank')
}

function healthTagType(s: string) {
  return s === 'normal' ? 'success' : s === 'suspicious' ? 'warning' : 'danger'
}
function healthLabel(s: string) {
  return s === 'normal' ? '正常' : s === 'suspicious' ? '可疑' : '异常'
}
</script>

<template>
  <div class="image-detection">
    <div class="page-header">
      <h2>🖼️ 图片检测</h2>
      <p>上传动物图片，AI 自动识别健康状态</p>
      <el-tag v-if="currentModel" type="primary">当前模型：{{ currentModel.model_name }}</el-tag>
      <el-tag v-else type="info">Mock 演示模式</el-tag>
    </div>

    <div class="main-content">
      <!-- 左侧上传区 -->
      <div class="left-panel">
        <div class="card">
          <h3 class="card-title">选择动物类型</h3>
          <el-select v-model="selectedAnimalType" placeholder="请选择" style="width:100%" clearable>
            <el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>

        <div class="card">
          <h3 class="card-title">上传图片</h3>
          <el-upload class="uploader" :auto-upload="false" :show-file-list="false"
            accept="image/*" :on-change="handleFileChange" drag>
            <div v-if="!previewUrl" class="upload-placeholder">
              <el-icon style="font-size:40px;color:#cbd5e0"><UploadFilled /></el-icon>
              <p>拖拽图片到此处或 <em>点击上传</em></p>
              <p style="font-size:12px;color:#a0aec0">支持 JPG、PNG、WEBP</p>
            </div>
            <div v-else class="preview-box">
              <img :src="previewUrl" class="preview-img" />
              <div class="preview-overlay" @click.stop="resetAll">重新选择</div>
            </div>
          </el-upload>
          <div v-if="uploading" style="margin-top:10px;color:#718096;font-size:13px">⏳ 上传中...</div>
          <div v-else-if="uploadedFilePath" style="margin-top:10px;color:#48bb78;font-size:13px">✅ 图片已就绪</div>
        </div>

        <div class="btn-row">
          <el-button type="primary" size="large" :loading="detecting"
            :disabled="!uploadedFilePath || uploading" class="detect-btn" @click="handleDetect">
            {{ detecting ? '检测中...' : '开始检测' }}
          </el-button>
          <el-button v-if="detectResult" size="large" @click="downloadResult(detectResult.record_id)">
            ⬇ 下载标注图
          </el-button>
        </div>
      </div>

      <!-- 右侧结果区 -->
      <div class="right-panel">
        <div v-if="!detectResult" class="result-placeholder">
          <span style="font-size:64px">🔍</span>
          <p>上传图片后点击「开始检测」</p>
        </div>

        <div v-else>
          <!-- Canvas 标注框可视化 -->
          <div class="canvas-container">
            <img ref="imageRef" :src="previewUrl" class="canvas-img" @load="handleImageLoad" />
            <canvas ref="canvasRef" class="canvas-overlay"></canvas>
          </div>

          <div class="result-stats">
            <div class="stat-item"><span class="sn">{{ detectResult.total_targets }}</span><span class="sl">检测目标</span></div>
            <div class="stat-item normal"><span class="sn">{{ detectResult.normal_count }}</span><span class="sl">正常</span></div>
            <div class="stat-item suspicious"><span class="sn">{{ detectResult.suspicious_count }}</span><span class="sl">可疑</span></div>
            <div class="stat-item abnormal"><span class="sn">{{ detectResult.abnormal_count }}</span><span class="sl">异常</span></div>
          </div>
          <el-alert v-if="detectResult.is_mock" type="warning" show-icon
            title="演示模式" description="模型文件未配置，以下为模拟结果" style="margin-bottom:14px" />
          <h4 style="margin-bottom:12px">检测详情</h4>
          <div v-for="det in detectResult.detections" :key="det.target_index"
            class="det-item" :class="det.health_status">
            <div class="det-header">
              <span class="det-idx">目标 {{ det.target_index + 1 }}</span>
              <el-tag :type="healthTagType(det.health_status)" size="small">{{ healthLabel(det.health_status) }}</el-tag>
            </div>
            <div class="det-body">
              <span>类别：<b>{{ det.class_name }}</b></span>
              <span>置信度：<b>{{ (det.confidence * 100).toFixed(1) }}%</b></span>
              <span>位置：({{ det.bbox_x1 }}, {{ det.bbox_y1 }}) → ({{ det.bbox_x2 }}, {{ det.bbox_y2 }})</span>
            </div>
          </div>
          <div class="result-meta">耗时 {{ detectResult.processing_time }}s ｜ 模型：{{ detectResult.model_name }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-detection { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; }
.page-header p { margin:0; color:#718096; font-size:13px; flex:1; }
.main-content { display:grid; grid-template-columns:340px 1fr; gap:16px; align-items:start; }
.card { background:#fff; border-radius:12px; padding:20px; margin-bottom:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.card-title { margin:0 0 14px; font-size:14px; font-weight:600; color:#2d3447; }
.uploader { width:100%; :deep(.el-upload-dragger) { width:100%; height:200px; border-radius:10px; display:flex; align-items:center; justify-content:center; } }
.upload-placeholder { text-align:center; color:#718096; }
.preview-box { position:relative; width:100%; height:100%; }
.preview-img { width:100%; height:200px; object-fit:contain; border-radius:8px; }
.preview-overlay { position:absolute; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; color:#fff; font-size:14px; border-radius:8px; opacity:0; transition:opacity .2s; cursor:pointer; }
.preview-box:hover .preview-overlay { opacity:1; }
.detect-btn { width:100%; height:44px; font-size:15px; background:linear-gradient(135deg,#4fc3f7,#0288d1); border:none; border-radius:10px; }
.right-panel { background:#fff; border-radius:12px; padding:24px; min-height:400px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.result-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; height:360px; color:#a0aec0; gap:12px; }
.result-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px; }
.stat-item { background:#f7f8fa; border-radius:10px; padding:14px; text-align:center; display:flex; flex-direction:column; gap:4px; }
.stat-item.normal { background:#f0fff4; } .stat-item.suspicious { background:#fffbeb; } .stat-item.abnormal { background:#fff5f5; }
.sn { font-size:28px; font-weight:700; color:#2d3447; line-height:1; }
.stat-item.normal .sn { color:#48bb78; } .stat-item.suspicious .sn { color:#ed8936; } .stat-item.abnormal .sn { color:#f56565; }
.sl { font-size:12px; color:#718096; }
.det-item { border:1px solid #e8eaed; border-radius:10px; padding:12px 16px; margin-bottom:10px; }
.det-item.abnormal { border-color:#feb2b2; background:#fff5f5; } .det-item.suspicious { border-color:#fbd38d; background:#fffbeb; } .det-item.normal { border-color:#9ae6b4; background:#f0fff4; }
.det-header { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.det-idx { font-weight:600; font-size:13px; color:#2d3447; }
.det-body { display:flex; gap:20px; flex-wrap:wrap; font-size:13px; color:#4a5568; }
.result-meta { margin-top:16px; font-size:12px; color:#a0aec0; text-align:right; }
.btn-row { display:flex; gap:10px; }
.detect-btn { flex:1; height:44px; font-size:15px; background:linear-gradient(135deg,#4fc3f7,#0288d1); border:none; border-radius:10px; }
.canvas-container { position:relative; width:100%; margin-bottom:16px; background:#f0f0f0; border-radius:8px; overflow:hidden; }
.canvas-img { width:100%; display:block; }
.canvas-overlay { position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; }
</style>
