<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { statisticsApi } from '../api/animals'
import { modelsApi } from '../api/detection'

const loading = ref(false)
const overview = ref<any>(null)
const selectedDays = ref(7)

const trendRef = ref<HTMLDivElement | null>(null)
const pieRef = ref<HTMLDivElement | null>(null)
const barRef = ref<HTMLDivElement | null>(null)

let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

onMounted(async () => {
  try {
    await modelsApi.getAnimalTypes()
  } catch {}
  fetchAll()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
  barChart?.dispose()
})

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
  barChart?.resize()
}

async function fetchAll() {
  loading.value = true
  try {
    const [ov, tr, by, dist]: any[] = await Promise.all([
      statisticsApi.getOverview(),
      statisticsApi.getTrend(selectedDays.value),
      statisticsApi.getByAnimalType(),
      statisticsApi.getHealthDistribution(),
    ])
    overview.value = ov
    renderTrend(tr.trend || [])
    renderBar(by.stats || [])
    renderPie(dist.distribution || [])
  } catch {}
  finally { loading.value = false }
}

function renderTrend(data: any[]) {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['检测次数', '异常数'], top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.date.slice(5)),
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#718096', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#718096', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [
      {
        name: '检测次数',
        type: 'line',
        data: data.map((d: any) => d.count),
        smooth: true,
        lineStyle: { color: '#4fc3f7', width: 2 },
        itemStyle: { color: '#4fc3f7' },
        areaStyle: { color: 'rgba(79,195,247,0.1)' },
      },
      {
        name: '异常数',
        type: 'line',
        data: data.map((d: any) => d.abnormal),
        smooth: true,
        lineStyle: { color: '#f56565', width: 2 },
        itemStyle: { color: '#f56565' },
        areaStyle: { color: 'rgba(245,101,101,0.08)' },
      },
    ],
  })
}

function renderPie(data: any[]) {
  if (!pieRef.value) return
  if (!pieChart) pieChart = echarts.init(pieRef.value)
  const labelMap: Record<string, string> = {
    normal: '正常', suspicious: '可疑', abnormal: '异常'
  }
  const colorMap: Record<string, string> = {
    normal: '#48bb78', suspicious: '#ed8936', abnormal: '#f56565'
  }
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      data: data.map((d: any) => ({
        name: labelMap[d.status] || d.status,
        value: d.count,
        itemStyle: { color: colorMap[d.status] || '#aaa' },
      })),
      label: { formatter: '{b}\n{d}%', fontSize: 12 },
    }],
  })
}

function renderBar(data: any[]) {
  if (!barRef.value) return
  if (!barChart) barChart = echarts.init(barRef.value)
  barChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['总检测', '异常', '正常'], top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.animal_type),
      axisLabel: { color: '#718096', fontSize: 11 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#718096', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [
      {
        name: '总检测',
        type: 'bar',
        data: data.map((d: any) => d.total),
        itemStyle: { color: '#4fc3f7', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
      {
        name: '异常',
        type: 'bar',
        data: data.map((d: any) => d.abnormal),
        itemStyle: { color: '#f56565', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
      {
        name: '正常',
        type: 'bar',
        data: data.map((d: any) => d.normal),
        itemStyle: { color: '#48bb78', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
    ],
  })
}

function handleDaysChange() { fetchAll() }
</script>

<template>
  <div class="stats-page" v-loading="loading">
    <div class="page-header">
      <h2>📊 统计分析</h2>
      <p>检测数据多维度统计</p>
      <el-select v-model="selectedDays" @change="handleDaysChange" style="width:120px">
        <el-option label="近7天" :value="7" />
        <el-option label="近14天" :value="14" />
        <el-option label="近30天" :value="30" />
      </el-select>
    </div>

    <!-- 概览卡片 -->
    <div class="overview-grid" v-if="overview">
      <div class="ov-card"><span class="ov-num">{{ overview.total_detections }}</span><span class="ov-label">总检测次数</span></div>
      <div class="ov-card"><span class="ov-num">{{ overview.today_detections }}</span><span class="ov-label">今日检测</span></div>
      <div class="ov-card"><span class="ov-num">{{ overview.total_targets }}</span><span class="ov-label">检测目标总数</span></div>
      <div class="ov-card danger"><span class="ov-num">{{ overview.total_abnormal }}</span><span class="ov-label">累计异常目标</span></div>
      <div class="ov-card warning"><span class="ov-num">{{ overview.total_suspicious }}</span><span class="ov-label">累计可疑目标</span></div>
    </div>

    <div class="charts-grid">
      <!-- 趋势折线图 -->
      <div class="chart-card wide">
        <h3 class="chart-title">检测趋势（近 {{ selectedDays }} 天）</h3>
        <div ref="trendRef" style="width:100%;height:240px"></div>
      </div>

      <!-- 健康状态饼图 -->
      <div class="chart-card">
        <h3 class="chart-title">健康状态分布</h3>
        <div ref="pieRef" style="width:100%;height:240px"></div>
      </div>

      <!-- 动物类型柱状图 -->
      <div class="chart-card">
        <h3 class="chart-title">按动物类型统计</h3>
        <div ref="barRef" style="width:100%;height:240px"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; } .page-header p { margin:0; color:#718096; font-size:13px; flex:1; }
.overview-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; }
.ov-card { background:#fff; border-radius:12px; padding:20px; text-align:center; display:flex; flex-direction:column; gap:6px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.ov-card.danger { background:#fff5f5; } .ov-card.warning { background:#fffbeb; }
.ov-num { font-size:32px; font-weight:700; color:#2d3447; line-height:1; }
.ov-card.danger .ov-num { color:#f56565; } .ov-card.warning .ov-num { color:#ed8936; }
.ov-label { font-size:12px; color:#718096; }
.charts-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.chart-card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.chart-card.wide { grid-column:1 / -1; }
.chart-title { margin:0 0 12px; font-size:14px; font-weight:600; color:#2d3447; }
</style>
