<template>
  <div class="login">
    <el-card class="login__card" shadow="always">
      <template #header>
        <div class="login__title">
          <h2>FastBlog 管理后台</h2>
          <p>请使用管理员账号登录</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @keyup.enter="onSubmit"
      >
        <el-form-item label="用户名 / 邮箱" prop="identifier">
          <el-input v-model="form.identifier" placeholder="请输入用户名或邮箱" :prefix-icon="User"/>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.remember_me">保持登录（签发 refresh token）</el-checkbox>
        </el-form-item>

        <el-form-item v-if="requires2fa">
          <el-alert
            type="warning"
            :closable="false"
            title="该账号启用了双因素认证"
            description="请在移动端或认证器完成二次验证（后台暂未提供 2FA 输入界面，属二期）。"
          />
        </el-form-item>

        <el-button
          type="primary"
          class="login__submit"
          :loading="loading"
          @click="onSubmit"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import {Lock, User} from '@element-plus/icons-vue'
import {ElMessage, type FormInstance, type FormRules} from 'element-plus'
import {reactive, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'

import {HOME_PATH} from '@/constants'
import {useUserStore} from '@/store/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const requires2fa = ref(false)

const form = reactive({
  identifier: '',
  password: '',
  remember_me: true,
})

const rules: FormRules = {
  identifier: [{required: true, message: '请输入用户名或邮箱', trigger: 'blur'}],
  password: [{required: true, message: '请输入密码', trigger: 'blur'}],
}

async function onSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  requires2fa.value = false
  try {
    // 后端同时接受 username / email，这里统一按 identifier 传（填了 @ 就当邮箱）
    const payload = form.identifier.includes('@')
      ? {email: form.identifier, password: form.password, remember_me: form.remember_me}
      : {username: form.identifier, password: form.password, remember_me: form.remember_me}

    const result = await userStore.login(payload)

    if (result.requires2fa) {
      requires2fa.value = true
      ElMessage.warning('该账号需要双因素验证')
      return
    }

    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string | undefined) || HOME_PATH
    await router.replace(redirect)
  } catch {
    // 错误提示已由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
}

.login__card {
  width: 400px;
  border-radius: 10px;
}

.login__title {
  text-align: center;
}

.login__title h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

.login__title p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.login__submit {
  width: 100%;
}
</style>
