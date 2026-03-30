<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { reportsApi } from '../api/reports'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const report = ref<any>(null)

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) { router.push('/reports'); return }
  loading.value = true
  try {
    report.value = await reportsApi.get(id)
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
    router.push('/reports')
  } finally { loading.value = false }
})

function typeLabel(t: string) {
  return t === 'image' ? '图片检测' : t === 'video' ? '视频检测' : '实时监测'
}
function healthType(s: string) {
  return s === '正常' ? 'success' : s === '需关注' ? 'warning' : s === '警告' ? 'danger' : 'info'
}

// 将 Markdown 简单渲染为 HTML
function renderMarkdown(md: string): string {
  if (!md) return ''
  return md
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^---$/gm, '<hr>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.+<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[a-z])/gm, '')
    .replace(/\n/g, '<br>')
}
</script>

<template>
  <div class="report-detail" v-loading="loading">
    <div class="page-header">
      <el-button link @click="router.push('/reports')">← 返回列表</el-button>
      <h2 v-if="report">{{ report.report_title }}</h2>
      <template v-if="report">
        <el-tag :type="healthType(report.health_assessment)" v-if="report.health_assessment">
          {{ report.health_assessment }}
        </el-tag>
        <el-button type="primary" @click="reportsApi.download(report.id)">⬇ 下载 MD</el-button>
        <el-button type="danger" @click="reportsApi.downloadPdf(report.id)">📄 下载 PDF</el-button>
      </template>
    </div>

    <template v-if="report">
      <!-- 报告元信息 -->
      <div class="meta-card">
        <div class="meta-item"><span class="ml">报告类型</span><span class="mv">{{ typeLabel(report.report_type) }}</span></div>
        <div class="meta-item"><span class="ml">生成状态</span><span class="mv">{{ report.generation_status === 'completed' ? '✅ 已完成' : report.generation_status }}</span></div>
        <div class="meta-item"><span class="ml">生成模型</span><span class="mv">{{ report.llm_model_used === 'mock' ? 'Mock模板' : report.llm_model_used || '-' }}</span></div>
        <div class="meta-item"><span class="ml">生成时间</span><span class="mv">{{ report.created_at }}</span></div>
        <div class="meta-item"><span class="ml">关联记录</span>
          <el-button link type="primary" @click="router.push('/records/' + report.detection_record_id)">
            #{{ report.detection_record_id }}
          </el-button>
        </div>
      </div>

      <!-- Mock 提示 -->
      <el-alert v-if="report.llm_model_used === 'mock'" type="warning" show-icon
        title="演示报告" description="当前为模板报告，配置 LLM API 后可生成 AI 个性化报告"
        style="margin-bottom:16px" />

      <!-- 报告内容 -->
      <div class="report-content">
        <div class="markdown-body" v-html="renderMarkdown(report.report_content)" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-detail { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:16px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; flex:1; }
.meta-card { background:#fff; border-radius:12px; padding:20px 24px; display:flex; gap:32px; flex-wrap:wrap; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.meta-item { display:flex; flex-direction:column; gap:4px; }
.ml { font-size:12px; color:#a0aec0; }
.mv { font-size:14px; font-weight:600; color:#2d3447; }
.report-content { background:#fff; border-radius:12px; padding:32px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.markdown-body { font-size:15px; line-height:1.8; color:#2d3447; }
.markdown-body :deep(h1) { font-size:22px; font-weight:700; margin:0 0 16px; color:#1a202c; border-bottom:2px solid #e2e8f0; padding-bottom:8px; }
.markdown-body :deep(h2) { font-size:17px; font-weight:600; margin:24px 0 12px; color:#2d3447; }
.markdown-body :deep(h3) { font-size:15px; font-weight:600; margin:16px 0 8px; color:#4a5568; }
.markdown-body :deep(hr) { border:none; border-top:1px solid #e2e8f0; margin:20px 0; }
.markdown-body :deep(ul) { padding-left:20px; margin:8px 0; }
.markdown-body :deep(li) { margin:4px 0; }
.markdown-body :deep(strong) { color:#1a202c; font-weight:600; }
</style>
