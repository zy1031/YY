<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api/auth'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
})

const validateConfirmPassword = (_: any, value: string, callback: Function) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

const formRef = ref()

async function handleRegister() {
  await formRef.value.validate()
  loading.value = true
  try {
    await authApi.register({
      username: form.username,
      password: form.password,
      email: form.email || undefined,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (err: any) {
    ElMessage.error(err || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <div class="brand-icon">🐾</div>
        <h1 class="brand-title">创建账号</h1>
        <p class="brand-subtitle">加入动物健康检测系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="register-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item label="邮箱（可选）" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" size="large" prefix-icon="Message" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" class="register-btn" @click="handleRegister">
          注 册
        </el-button>
      </el-form>

      <div class="register-footer">
        已有账号？
        <span class="link" @click="router.push('/login')">立即登录</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 50%, #0d2137 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.register-card {
  width: 440px;
  background: rgba(255,255,255,0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(79,195,247,0.2);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.4);
}
.register-header {
  text-align: center;
  margin-bottom: 28px;
}
.brand-icon { font-size: 40px; margin-bottom: 10px; }
.brand-title { font-size: 20px; font-weight: 700; color: #e2e8f0; margin: 0 0 6px; }
.brand-subtitle { font-size: 13px; color: #718096; margin: 0; }
.register-form {
  :deep(.el-form-item__label) { color: #a0aec0; font-size: 13px; }
  :deep(.el-input__wrapper) { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); box-shadow: none; }
  :deep(.el-input__inner) { color: #e2e8f0; }
}
.register-btn {
  width: 100%; height: 44px; font-size: 15px; letter-spacing: 4px;
  background: linear-gradient(135deg, #4fc3f7, #0288d1);
  border: none; margin-top: 4px; border-radius: 8px;
}
.register-footer { text-align: center; margin-top: 16px; color: #718096; font-size: 13px; }
.link { color: #4fc3f7; cursor: pointer; }
.link:hover { text-decoration: underline; }
</style>
