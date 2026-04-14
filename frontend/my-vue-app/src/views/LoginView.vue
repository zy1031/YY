<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const formRef = ref<any>()

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const res: any = await authApi.login(form)
    authStore.setAuth(res)
    ElMessage({ message: '登录成功，欢迎回来 👋', type: 'success', duration: 2000 })
    router.push('/')
  } catch (err: any) {
    ElMessage.error(err || '用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-grid"></div>

    <div class="login-card">
      <div class="login-header">
        <div class="brand-logo">
          <span class="brand-emoji">🐾</span>
        </div>
        <h1 class="brand-title">动物健康检测系统</h1>
        <p class="brand-subtitle">AI-Powered Animal Health Detection Platform</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <template #label><span class="field-label">用户名</span></template>
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            prefix-icon="User"
            class="custom-input"
          />
        </el-form-item>

        <el-form-item prop="password">
          <template #label><span class="field-label">密码</span></template>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            prefix-icon="Lock"
            show-password
            class="custom-input"
          />
        </el-form-item>

        <button
          class="login-btn"
          :class="{ loading }"
          @click.prevent="handleLogin"
          :disabled="loading"
        >
          <span v-if="!loading" class="btn-text">登 录</span>
          <span v-else class="btn-loading">
            <span class="spinner"></span>
            登录中...
          </span>
        </button>
      </el-form>

      <div class="login-footer">
        还没有账号？
        <span class="link" @click="router.push('/register')">立即注册 →</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #080f1a;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.25;
  pointer-events: none;
  animation: none !important;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #0288d1, transparent);
  top: -120px;
  left: -120px;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #4fc3f7, transparent);
  bottom: -80px;
  right: -80px;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(79, 195, 247, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 195, 247, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

.login-card {
  width: 420px;
  background: rgba(15, 23, 36, 0.92);
  border: 1px solid rgba(79, 195, 247, 0.15);
  border-radius: 20px;
  padding: 44px 40px;
  box-shadow:
    0 0 0 1px rgba(79, 195, 247, 0.05),
    0 24px 80px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  z-index: 1;
  animation: none;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.brand-logo {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #4fc3f7 0%, #0288d1 100%);
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(79, 195, 247, 0.35);
}

.brand-emoji {
  font-size: 28px;
}

.brand-title {
  font-size: 20px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 6px;
  letter-spacing: 1px;
}

.brand-subtitle {
  font-size: 11px;
  color: #3d5470;
  margin: 0;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.field-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.login-form {
  :deep(.el-form-item) {
    margin-bottom: 18px;
  }

  :deep(.el-form-item__label) {
    padding-bottom: 4px;
  }

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: none;
    border-radius: 10px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  :deep(.el-input__wrapper:hover) {
    border-color: rgba(79, 195, 247, 0.3);
  }

  :deep(.el-input__wrapper.is-focus) {
    border-color: rgba(79, 195, 247, 0.6);
    box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.1);
  }

  :deep(.el-input__inner) {
    color: #e2e8f0;
    font-size: 14px;
  }

  :deep(.el-input__inner::placeholder) {
    color: #2d3d50;
  }

  :deep(.el-input__prefix-icon) {
    color: #3d5470;
  }
}

.login-btn {
  width: 100%;
  height: 46px;
  background: linear-gradient(135deg, #4fc3f7 0%, #0288d1 100%);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  cursor: pointer;
  margin-top: 8px;
  transition: all 0.22s ease;
  box-shadow: 0 4px 16px rgba(79, 195, 247, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  outline: none;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(79, 195, 247, 0.4);
  background: linear-gradient(135deg, #62cbf8 0%, #039be5 100%);
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(79, 195, 247, 0.3);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-loading {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  color: #3d5470;
  font-size: 13px;
}

.link {
  color: #4fc3f7;
  cursor: pointer;
  transition: color 0.18s;
  font-weight: 500;
}

.link:hover {
  color: #81d4fa;
}
</style>
