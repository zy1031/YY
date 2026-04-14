<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { detectionApi, modelsApi } from '../api/detection'
import api from '../api/request'

const router = useRouter()
const loading = ref(false)
const records = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const filterType = ref('')
const filterAnimalType = ref<number | null>(null)
const animalTypes = ref<any[]>([])
const selectedIds = ref<number[]>([])
const tableRef = ref()
const batchDeleting = ref(false)

onMounted(async () => {
  try {
    const res: any = await modelsApi.getAnimalTypes()
    animalTypes.value = res.animal_types || []
  } catch {}
  fetchRecords()
})

async function fetchRecords() {
  loading.value = true
  try {
    const res: any = await detectionApi.getHistory({
      page: page.value,
      page_size: pageSize.value,
      detection_type: filterType.value || undefined,
      animal_type_id: filterAnimalType.value ?? undefined,
    })
    records.value = res.history || []
    total.value = res.total || 0
    selectedIds.value = []
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(p: number) { page.value = p; fetchRecords() }
function handleFilter() { page.value = 1; fetchRecords() }

function handleSelectionChange(rows: any[]) {
  selectedIds.value = rows.map((r: any) => r.id)
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确定删除该记录？', '提示', { type: 'warning' })
  try {
    await detectionApi.deleteRecord(id)
    ElMessage.success('删除成功')
    fetchRecords()
  } catch (e: any) {
    ElMessage.error(e || '删除失败')
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) { ElMessage.warning('请先选择要删除的记录'); return }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selectedIds.value.length} 条记录？此操作不可恢复。`,
    '批量删除',
    { type: 'warning', confirmButtonText: '确定删除', confirmButtonClass: 'el-button--danger' }
  )
  batchDeleting.value = true
  try {
    await api.delete('/api/detection/batch', { data: selectedIds.value })
    ElMessage.success(`成功删除 ${selectedIds.value.length} 条记录`)
    fetchRecords()
  } catch (e: any) {
    ElMessage.error(e || '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

function viewDetail(id: number) { router.push(`/records/${id}`) }

function typeLabel(t: string) { return t === 'image' ? '图片行为' : '实时检测' }
function typeTagType(t: string) { return t === 'image' ? 'primary' : 'warning' }
function statusLabel(s: string) { return s === 'completed' ? '已完成' : s === 'failed' ? '失败' : '处理中' }
function statusTagType(s: string) { return s === 'completed' ? 'success' : s === 'failed' ? 'danger' : 'info' }
function getAnimalTypeName(id: number) { return animalTypes.value.find((t: any) => t.id === id)?.name || '-' }
</script>

<template>
  <div class="records-page">
    <div class="page-header">
      <h2>📋 检测记录</h2>
      <p>查看图片检测与实时检测的历史任务</p>
      <el-button @click="router.push('/detection/camera')" type="primary">+ 开始实时检测</el-button>
    </div>

    <!-- 过滤器 -->
    <div class="filter-bar">
      <el-select v-model="filterType" placeholder="全部类型" clearable @change="handleFilter" style="width:140px">
        <el-option label="图片行为识别" value="image" />
        <el-option label="实时检测" value="camera" />
      </el-select>
      <el-select v-model="filterAnimalType" placeholder="全部动物" clearable @change="handleFilter" style="width:140px">
        <el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <el-button type="primary" @click="handleFilter">查询</el-button>
      <el-button
        v-if="selectedIds.length > 0"
        type="danger"
        :loading="batchDeleting"
        @click="handleBatchDelete"
      >🗑 删除选中 ({{ selectedIds.length }})</el-button>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table
        ref="tableRef"
        :data="records"
        v-loading="loading"
        border
        style="width:100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="类型" width="100">
          <template #default="{row}">
            <el-tag :type="typeTagType(row.detection_type)" size="small">{{ typeLabel(row.detection_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="statusTagType(row.detection_status)" size="small">{{ statusLabel(row.detection_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="动物类型" width="110">
          <template #default="{row}">{{ getAnimalTypeName(row.animal_type_id) }}</template>
        </el-table-column>
        <el-table-column prop="total_targets" label="目标数" width="90" align="center" />
        <el-table-column label="异常数" width="90" align="center">
          <template #default="{row}">
            <template v-if="row.detection_type === 'image'">-</template>
            <span v-else :style="{color: row.abnormal_count > 0 ? '#f56565' : 'inherit', fontWeight: row.abnormal_count > 0 ? '700' : 'normal'}">
              {{ row.abnormal_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="90" align="center">
          <template #default="{row}">{{ row.processing_time ? row.processing_time + 'ms' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="检测时间" min-width="160" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{row}">
            <el-button type="primary" link size="small" @click="viewDetail(row.id)">详情</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <span v-if="selectedIds.length > 0" style="color:#718096;font-size:13px">已选择 {{ selectedIds.length }} 条</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.records-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; }
.page-header p { margin:0; color:#718096; font-size:13px; flex:1; }
.filter-bar { background:#fff; border-radius:12px; padding:16px 20px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.table-card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.table-footer { display:flex; align-items:center; justify-content:space-between; margin-top:16px; }
</style>
