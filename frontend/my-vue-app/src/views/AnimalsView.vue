<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { animalsApi } from '../api/animals'
import { modelsApi } from '../api/detection'

const loading = ref(false)
const animals = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const animalTypes = ref<any[]>([])
const filterType = ref<number | null>(null)
const keyword = ref('')

// 对话框
const dialogVisible = ref(false)
const editMode = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
  animal_type_id: null as number | null,
  animal_number: '',
  breed: '',
  age: null as number | null,
  weight: null as number | null,
  remarks: '',
})
const formRef = ref()
const rules = {
  animal_type_id: [{ required: true, message: '请选择动物类型', trigger: 'change' }],
  animal_number: [{ required: true, message: '请输入动物编号', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const res: any = await modelsApi.getAnimalTypes()
    animalTypes.value = res.animal_types || []
  } catch {}
  fetchAnimals()
})

async function fetchAnimals() {
  loading.value = true
  try {
    const res: any = await animalsApi.list({
      page: page.value,
      page_size: pageSize.value,
      animal_type_id: filterType.value ?? undefined,
      keyword: keyword.value || undefined,
    })
    animals.value = res.animals || []
    total.value = res.total || 0
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleFilter() { page.value = 1; fetchAnimals() }
function handlePageChange(p: number) { page.value = p; fetchAnimals() }

function openCreate() {
  editMode.value = false
  editingId.value = null
  form.value = { animal_type_id: null, animal_number: '', breed: '', age: null, weight: null, remarks: '' }
  dialogVisible.value = true
}

function openEdit(row: any) {
  editMode.value = true
  editingId.value = row.id
  form.value = {
    animal_type_id: row.animal_type_id,
    animal_number: row.animal_number,
    breed: row.breed || '',
    age: row.age,
    weight: row.weight,
    remarks: row.remarks || '',
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (editMode.value && editingId.value) {
      await animalsApi.update(editingId.value, {
        breed: form.value.breed || undefined,
        age: form.value.age,
        weight: form.value.weight,
        remarks: form.value.remarks || undefined,
      })
      ElMessage.success('更新成功')
    } else {
      await animalsApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchAnimals()
  } catch (e: any) {
    ElMessage.error(e || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确定删除该动物档案？', '提示', { type: 'warning' })
  try {
    await animalsApi.delete(id)
    ElMessage.success('删除成功')
    fetchAnimals()
  } catch (e: any) {
    ElMessage.error(e || '删除失败')
  }
}
</script>

<template>
  <div class="animals-page">
    <div class="page-header">
      <h2>🐄 动物档案</h2>
      <p>管理养殖场动物基本信息</p>
      <el-button type="primary" @click="openCreate">+ 新增档案</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterType" placeholder="全部类型" clearable @change="handleFilter" style="width:140px">
        <el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索动物编号" clearable style="width:200px" @keyup.enter="handleFilter" />
      <el-button type="primary" @click="handleFilter">查询</el-button>
    </div>

    <div class="table-card">
      <el-table :data="animals" v-loading="loading" border style="width:100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="animal_number" label="动物编号" min-width="130" />
        <el-table-column prop="animal_type_name" label="动物类型" width="110" />
        <el-table-column prop="breed" label="品种" width="110">
          <template #default="{row}">{{ row.breed || '-' }}</template>
        </el-table-column>
        <el-table-column prop="age" label="月龄" width="80" align="center">
          <template #default="{row}">{{ row.age != null ? row.age + '月' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="weight" label="体重(kg)" width="100" align="center">
          <template #default="{row}">{{ row.weight != null ? row.weight : '-' }}</template>
        </el-table-column>
        <el-table-column prop="remarks" label="备注" min-width="140">
          <template #default="{row}">{{ row.remarks || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{row}">
            <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next" style="margin-top:16px;justify-content:flex-end"
        @current-change="handlePageChange" />
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑档案' : '新增档案'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="动物类型" prop="animal_type_id">
          <el-select v-model="form.animal_type_id" placeholder="请选择" style="width:100%" :disabled="editMode">
            <el-option v-for="t in animalTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="动物编号" prop="animal_number">
          <el-input v-model="form.animal_number" :disabled="editMode" placeholder="如：PIG-2024-001" />
        </el-form-item>
        <el-form-item label="品种">
          <el-input v-model="form.breed" placeholder="可选" />
        </el-form-item>
        <el-form-item label="月龄">
          <el-input-number v-model="form.age" :min="0" :max="240" placeholder="月" style="width:100%" />
        </el-form-item>
        <el-form-item label="体重(kg)">
          <el-input-number v-model="form.weight" :min="0" :precision="1" placeholder="kg" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remarks" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.animals-page { display:flex; flex-direction:column; gap:16px; }
.page-header { background:#fff; border-radius:12px; padding:20px 24px; display:flex; align-items:center; gap:16px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.page-header h2 { margin:0; font-size:18px; }
.page-header p { margin:0; color:#718096; font-size:13px; flex:1; }
.filter-bar { background:#fff; border-radius:12px; padding:16px 20px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.table-card { background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
</style>
