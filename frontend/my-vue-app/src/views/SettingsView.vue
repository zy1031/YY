<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/request'

const loading = ref(false)
const saving = ref(false)
const configs = ref<Record<string, string>>({})

const configFields = [
  { key: 'confidence_threshold', label: '默认置信度阈值', type: 'number', min: 0.1, max: 1.0, step: 0.05, desc: '检测框置信度低于此值将被过滤' },
  { key: 'iou_threshold', label: '默认IOU阈值', type: 'number', min: 0.1, max: 1.0, step: 0.05, desc: '非极大值抑制阈值，控制重叠框过滤' },
  { key: 'max_upload_size_mb', label: '最大上传文件大小(MB)', type: 'number', min: 1, max: 2000, step: 1, desc: '单个文件上传大小限制' },
  { key: 'result_save_days', label: '检测结果保留天数', type: 'number', min: 1, max: 365, step: 1, desc: '超过此天数的检测结果将自动清理' },
  { key: 'llm_api_url', label: 'LLM API地址', type: 'text', desc: '大语言模型API接口地址（第10周使用）' },
  { key: 'llm_api_key', label: 'LLM API Key', type: 'password', desc: '大语言模型API密钥' },
  { key: 'llm_model_name', label: 'LLM模型名称', type: 'text', desc: '如：gpt-4o、deepseek-chat 等' },
]

const form = ref<Record<string, any>>({})

onMounted(async () => {
  loading.value = true
  try {
    const res: any = await api.get('/api/config/')
    configs.value = res || {}
    // 初始化表单
    configFields.forEach(f => {
      form.value[f.key] = configs.value[f.key] ?? ''
    })
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  saving.value = true
  try {
    // 使用批量更新接口
    const data: Record<string, string> = {}
    configFields.forEach(f => {
      const val = form.value[f.key]
      if (val !== '' && val !== null && val !== undefined) {
        data[f.key] = String(val)
      }
    })
    await api.post('/api/config/batch', data)
    ElMessage.success('配置保存成功')
  } catch (e: any) {
    ElMessage.error(e || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleInitDefaults() {
  try {
    const res: any = await api.post('/api/config/init-defaults', {})
    ElMessage.success(res.message || '默认配置已初始化')
    // 重新加载
    const fresh: any = await api.get('/api/config/')
    configFields.forEach(f => {
      form.value[f.key] = fresh[f.key] ?? ''
    })
  } catch (e: any) {
    ElMessage.error(e || '初始化失败')
  }
}
</script>

<template>
  <div class="settings-page" v-loading="loading">
    <div class="page-header">
      <h2>⚙️ 系统配置</h2>
      <p>配置检测参数、LLM接口等系统设置</p>
    </div>

    <div class="config-card">
      <h3 class="section-title">🔍 检测参数</h3>
      <div class="config-grid">
        <template v-for="field in configFields.slice(0, 4)" :key="field.key">
          <div class="config-item">
            <div class="config-label">{{ field.label }}</div>
            <div class="config-desc">{{ field.desc }}</div>
            <el-input-number
              v-if="field.type === 'number'"
              v-model="form[field.key]"
              :min="field.min"
              :max="field.max"
              :step="field.step"
              style="width:100%"
            />
          </div>
        </template>
      </div>
    </div>

    <div class="config-card">
      <h3 class="section-title">🤖 LLM 配置（第10周启用）</h3>
      <div class="config-list">
        <template v-for="field in configFields.slice(4)" :key="field.key">
          <div class="config-row">
            <div class="config-row-label">
              <span>{{ field.label }}</span>
              <span class="config-desc">{{ field.desc }}</span>
            </div>
            <el-input
              v-model="form[field.key]"
              :type="field.type === 'password' ? 'password' : 'text'"
              :show-password="field.type === 'password'"
              placeholder="请输入"
              style="width:360px"
            />
          </div>
        </template>
      </div>
    </div>

    <div class="save-bar">
      <el-button @click="handleInitDefaults">初始化默认值</el-button>
      <el-button type="primary" size="large" :loading="saving" @click="handleSave">保存配置</el-button>
    </div>
  </div>
</template>

<style scoped>
.settings-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; }
.page-header p { margin:0; color:#718096; font-size:13px; }
.config-card { background:#fff; border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.section-title { margin:0 0 20px; font-size:15px; font-weight:600; color:#2d3447; }
.config-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:20px; }
.config-item { display:flex; flex-direction:column; gap:6px; }
.config-label { font-size:14px; font-weight:500; color:#2d3447; }
.config-desc { font-size:12px; color:#a0aec0; }
.config-list { display:flex; flex-direction:column; gap:16px; }
.config-row { display:flex; align-items:center; justify-content:space-between; padding:12px 0; border-bottom:1px solid #f0f0f0; }
.config-row:last-child { border-bottom:none; }
.config-row-label { display:flex; flex-direction:column; gap:4px; }
.config-row-label span:first-child { font-size:14px; font-weight:500; color:#2d3447; }
.save-bar { display:flex; justify-content:flex-end; }
</style>
