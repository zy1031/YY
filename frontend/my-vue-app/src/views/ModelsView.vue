<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const FALLBACK_MODEL_PATH = 'backend/models/best.pt'

const models = ref<any[]>([])
const animalTypes = ref<any[]>([])
const currentModel = ref<any>(null)
const loading = ref(false)
const switchLoading = ref(false)

const animalTypeNameMap = computed(() => {
  return Object.fromEntries(animalTypes.value.map((item: any) => [item.id, item.name]))
})

const groupedModels = computed(() => {
  const groups = new Map<number | string, { key: number | string; title: string; models: any[] }>()

  for (const model of models.value) {
    const key = model.animal_type_id ?? 'unknown'
    const title = model.animal_type_id
      ? (animalTypeNameMap.value[model.animal_type_id] || `动物类型 ${model.animal_type_id}`)
      : '未分类模型'

    if (!groups.has(key)) {
      groups.set(key, { key, title, models: [] })
    }
    groups.get(key)!.models.push(model)
  }

  return Array.from(groups.values())
})

const actualModelText = computed(() => {
  if (currentModel.value) {
    return currentModel.value.model_name
  }
  return FALLBACK_MODEL_PATH
})

const actualModelDesc = computed(() => {
  if (currentModel.value) {
    return `${currentModel.value.animal_type_name} · ${currentModel.value.framework}`
  }
  return '未在数据库中切换模型时，后端会自动回退加载该文件'
})

async function fetchModels() {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const [modelsRes, currentRes, typesRes] = await Promise.all([
      fetch('http://localhost:8000/api/models/', { headers: { Authorization: `Bearer ${token}` } }),
      fetch('http://localhost:8000/api/models/switch', { headers: { Authorization: `Bearer ${token}` } }),
      fetch('http://localhost:8000/api/animal-types/', { headers: { Authorization: `Bearer ${token}` } }),
    ])
    const modelsData = await modelsRes.json()
    const currentData = await currentRes.json()
    const typesData = await typesRes.json()
    models.value = modelsData.models || []
    currentModel.value = currentData.current_model
    animalTypes.value = typesData.animal_types || []
  } catch {
    ElMessage.error('获取模型列表失败')
  } finally {
    loading.value = false
  }
}

async function switchModel(modelId: number) {
  switchLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('http://localhost:8000/api/models/switch', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId }),
    })
    if (res.ok) {
      ElMessage.success('模型切换成功')
      await fetchModels()
    } else {
      ElMessage.error('切换失败')
    }
  } finally {
    switchLoading.value = false
  }
}

async function updateConfig(model: any) {
  try {
    const token = localStorage.getItem('token')
    const res = await fetch(`http://localhost:8000/api/models/${model.id}/config`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        confidence_threshold: model.confidence_threshold,
        iou_threshold: model.iou_threshold,
      }),
    })
    if (res.ok) ElMessage.success('参数更新成功')
    else ElMessage.error('更新失败')
  } catch {
    ElMessage.error('更新失败')
  }
}

onMounted(fetchModels)
</script>

<template>
  <div class="models-page">
    <div class="page-header">
      <h2 class="page-title">模型管理</h2>
      <p class="page-desc">管理检测模型，切换当前使用的模型并调整参数</p>
    </div>

    <!-- 当前模型 -->
    <div class="current-model-card">
      <div class="current-badge">当前实际加载</div>
      <div class="current-info">
        <span class="current-name">{{ actualModelText }}</span>
        <span class="current-meta">{{ actualModelDesc }}</span>
        <span class="current-path">路径：{{ currentModel?.model_path || FALLBACK_MODEL_PATH }}</span>
      </div>
      <div class="current-thresholds">
        <span>置信度: {{ currentModel?.confidence_threshold ?? 0.5 }}</span>
        <span>IOU: {{ currentModel?.iou_threshold ?? 0.45 }}</span>
      </div>
    </div>

    <!-- 模型列表 -->
    <div class="section">
      <h3 class="section-title">可用模型列表</h3>
      <div v-loading="loading">
        <div v-if="models.length === 0 && !loading" class="empty-tip">
          暂无可用模型，请先在数据库中添加模型记录
        </div>
        <div v-else class="group-list">
          <div v-for="group in groupedModels" :key="String(group.key)" class="model-group">
            <div class="group-header">
              <h4 class="group-title">{{ group.title }}</h4>
              <el-tag size="small" type="info">{{ group.models.length }} 个模型</el-tag>
            </div>
            <div class="model-grid">
              <div
                v-for="model in group.models"
                :key="model.id"
                class="model-card"
                :class="{ active: currentModel && currentModel.id === model.id }"
              >
                <div class="model-card-header">
                  <div class="model-name">{{ model.model_name }}</div>
                  <el-tag size="small" :type="currentModel && currentModel.id === model.id ? 'success' : 'info'">
                    {{ currentModel && currentModel.id === model.id ? '使用中' : '可切换' }}
                  </el-tag>
                </div>
                <div class="model-meta">
                  <span>框架: {{ model.framework }}</span>
                  <span>版本: {{ model.model_version }}</span>
                </div>

                <!-- 参数调整 -->
                <div class="model-params">
                  <div class="param-row">
                    <label>置信度阈值</label>
                    <el-slider
                      v-model="model.confidence_threshold"
                      :min="0.1" :max="0.95" :step="0.05"
                      :show-tooltip="true" size="small"
                      style="flex:1; margin: 0 12px"
                    />
                    <span class="param-val">{{ model.confidence_threshold?.toFixed(2) }}</span>
                  </div>
                  <div class="param-row">
                    <label>IOU 阈值</label>
                    <el-slider
                      v-model="model.iou_threshold"
                      :min="0.1" :max="0.95" :step="0.05"
                      :show-tooltip="true" size="small"
                      style="flex:1; margin: 0 12px"
                    />
                    <span class="param-val">{{ model.iou_threshold?.toFixed(2) }}</span>
                  </div>
                </div>

                <div class="model-actions">
                  <el-button
                    size="small"
                    type="primary"
                    :disabled="currentModel && currentModel.id === model.id"
                    :loading="switchLoading"
                    @click="switchModel(model.id)"
                  >切换为当前模型</el-button>
                  <el-button size="small" @click="updateConfig(model)">保存参数</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.models-page { display: flex; flex-direction: column; gap: 20px; }

.page-header { background: #fff; border-radius: 12px; padding: 20px 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.page-title { margin: 0 0 4px; font-size: 18px; font-weight: 700; color: #1a202c; }
.page-desc { margin: 0; font-size: 13px; color: #718096; }

.current-model-card {
  background: linear-gradient(135deg, #1a2a3a, #0d2137);
  border-radius: 12px; padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  color: #e2e8f0;
}
.current-model-card.empty { justify-content: center; color: #718096; font-size: 13px; }
.current-badge {
  background: #48bb78; color: #fff;
  font-size: 11px; font-weight: 700;
  padding: 4px 10px; border-radius: 20px;
  white-space: nowrap;
}
.current-info { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.current-name { font-size: 16px; font-weight: 600; }
.current-meta { font-size: 12px; color: #b8c7d9; }
.current-path { font-size: 12px; color: #8fd3ff; word-break: break-all; }
.current-thresholds { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #a0aec0; text-align: right; }

.section { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section-title { margin: 0 0 16px; font-size: 15px; font-weight: 600; color: #2d3447; }
.empty-tip { text-align: center; color: #a0aec0; padding: 40px; font-size: 14px; }

.group-list { display: flex; flex-direction: column; gap: 18px; }
.model-group { border: 1px solid #edf2f7; border-radius: 12px; padding: 16px; background: #f8fafc; }
.group-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.group-title { margin: 0; font-size: 14px; font-weight: 700; color: #243b53; }
.model-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.model-card {
  border: 1px solid #e8eaed; border-radius: 10px;
  padding: 16px; transition: all 0.2s;
}
.model-card.active { border-color: #48bb78; background: #f0fff4; }
.model-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.model-name { font-size: 15px; font-weight: 600; color: #2d3447; }
.model-meta { font-size: 12px; color: #718096; display: flex; gap: 12px; margin-bottom: 14px; }
.model-params { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
.param-row { display: flex; align-items: center; gap: 4px; }
.param-row label { font-size: 12px; color: #718096; white-space: nowrap; width: 72px; }
.param-val { font-size: 12px; font-weight: 600; color: #2d3447; width: 32px; text-align: right; }
.model-actions { display: flex; gap: 8px; }
</style>
