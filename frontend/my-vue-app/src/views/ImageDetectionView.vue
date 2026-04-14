<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { modelsApi, detectionApi } from '../api/detection'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const animalTypes = ref<any[]>([])
const selectedAnimalType = ref<number | null>(null)
const currentModel = ref<any>(null)
const canReadModelConfig = computed(() => authStore.isAdmin)
const currentModelText = computed(() => currentModel.value?.model_name || '按所选动物类型自动匹配')
const uploadedFilePath = ref('')
const previewUrl = ref('')
const uploading = ref(false)
const detecting = ref(false)
const detectResult = ref<any>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)

onMounted(async () => {
  try {
    const typesRes: any = await modelsApi.getAnimalTypes()
    animalTypes.value = typesRes.animal_types || []

    if (canReadModelConfig.value) {
      try {
        const modelRes: any = await modelsApi.getCurrentModel()
        currentModel.value = modelRes.current_model
        if (currentModel.value) selectedAnimalType.value = currentModel.value.animal_type_id
      } catch {
        currentModel.value = null
      }
    }
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
    ElMessage.success(`识别完成，发现 ${res.total_targets} 个目标`)
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

  for (const det of detectResult.value.detections) {
    const color = '#36a2eb'
    const x1 = det.bbox_x1, y1 = det.bbox_y1
    const x2 = det.bbox_x2, y2 = det.bbox_y2
    const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`

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
</script>

<template>
  <div class="image-detection">
    <div class="page-header">
      <h2>🖼️ 图片行为识别</h2>
      <p>上传动物图片，AI 自动识别当前行为类别</p>
      <el-tag v-if="canReadModelConfig && currentModel" type="primary">当前模型：{{ currentModel.model_name }}</el-tag>
      <el-tag v-else type="success">检测时将按所选动物类型自动匹配模型</el-tag>
    </div>

    <div class="main-content">
      <!-- 左侧上传区 -->
      <div class="left-panel">
        <div class="card">
          <h3 class="card-title">选择动物类型</h3>
          <p class="card-hint">
            本次检测会优先使用所选动物类型对应的模型；
            <span v-if="canReadModelConfig">未匹配到时才回退到当前激活模型或 backend/models/best.pt。</span>
            <span v-else>普通用户不展示管理员模型配置，但仍会自动匹配后端可用模型。</span>
          </p>
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
            {{ detecting ? '识别中...' : '开始识别' }}
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
          <p>上传图片后点击「开始识别」</p>
        </div>

        <div v-else>
          <!-- Canvas 标注框可视化 -->
          <div class="canvas-container">
            <img ref="imageRef" :src="previewUrl" class="canvas-img" @load="handleImageLoad" />
            <canvas ref="canvasRef" class="canvas-overlay"></canvas>
          </div>

          <div class="result-stats">
            <div class="stat-item"><span class="sn">{{ detectResult.total_targets }}</span><span class="sl">识别目标</span></div>
            <div class="stat-item behavior"><span class="sn">{{ detectResult.detections?.length || 0 }}</span><span class="sl">行为结果</span></div>
          </div>
          <el-alert v-if="detectResult.is_mock" type="warning" show-icon
            title="演示模式" description="未找到可用模型文件，以下为模拟行为识别结果" style="margin-bottom:14px" />
          <el-alert v-else type="success" show-icon
            title="真实模型推理" description="本次任务为图片行为识别，优先使用所选动物类型对应模型" style="margin-bottom:14px" />
          <h4 style="margin-bottom:12px">识别详情</h4>
          <div v-for="det in detectResult.detections" :key="det.target_index"
            class="det-item behavior">
            <div class="det-header">
              <span class="det-idx">目标 {{ det.target_index + 1 }}</span>
              <el-tag type="primary" size="small">行为识别</el-tag>
            </div>
            <div class="det-body">
              <span>行为类别：<b>{{ det.class_name }}</b></span>
              <span>置信度：<b>{{ (det.confidence * 100).toFixed(1) }}%</b></span>
              <span>位置：({{ det.bbox_x1 }}, {{ det.bbox_y1 }}) → ({{ det.bbox_x2 }}, {{ det.bbox_y2 }})</span>
            </div>
          </div>
          <div class="result-meta">耗时 {{ detectResult.processing_time }}s ｜ 模型：{{ canReadModelConfig ? (detectResult.model_name || currentModelText) : '自动匹配模型' }}</div>
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
.card-hint { margin: -6px 0 12px; font-size: 12px; line-height: 1.6; color: #718096; }
.uploader { width:100%; :deep(.el-upload-dragger) { width:100%; height:200px; border-radius:10px; display:flex; align-items:center; justify-content:center; } }
.upload-placeholder { text-align:center; color:#718096; }
.preview-box { position:relative; width:100%; height:100%; }
.preview-img { width:100%; height:200px; object-fit:contain; border-radius:8px; }
.preview-overlay { position:absolute; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; color:#fff; font-size:14px; border-radius:8px; opacity:0; transition:opacity .2s; cursor:pointer; }
.preview-box:hover .preview-overlay { opacity:1; }
.detect-btn { width:100%; height:44px; font-size:15px; background:linear-gradient(135deg,#4fc3f7,#0288d1); border:none; border-radius:10px; }
.right-panel { background:#fff; border-radius:12px; padding:24px; min-height:400px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.result-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; height:360px; color:#a0aec0; gap:12px; }
.result-stats { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-bottom:20px; }
.stat-item { background:#f7f8fa; border-radius:10px; padding:14px; text-align:center; display:flex; flex-direction:column; gap:4px; }
.stat-item.behavior { background:#eff6ff; }
.sn { font-size:28px; font-weight:700; color:#2d3447; line-height:1; }
.stat-item.behavior .sn { color:#2563eb; }
.sl { font-size:12px; color:#718096; }
.det-item { border:1px solid #e8eaed; border-radius:10px; padding:12px 16px; margin-bottom:10px; }
.det-item.behavior { border-color:#bfdbfe; background:#f8fbff; }
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
