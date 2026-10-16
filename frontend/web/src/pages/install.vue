<script lang="ts" setup>
import type {WizardStatus} from '@/api/modules/install'
/**
 * Web 安装向导（单机部署）
 *
 * 后端按部署模式分流：`enterprise`（**默认**）不开放 Web 写口、初始化走命令行；
 * `single` 才开放，且**安装完成即永久关闭**。所以这里先读 `status()`：
 * `available === false` 时只显示对应提示、**不渲染任何表单** —— 企业部署与
 * 已安装站点因此看不到写入口。
 *
 * 与 `login.vue` 同一约定：只用 Tailwind + shadcn-vue（Element Plus 仅后台页用）。
 */
import {installWizardApi} from '@/api/modules/install'

const {t} = useI18n()

definePageMeta({layout: false, title: 'installWizard.title'})
// 安装页不该被索引：它可能是未完成部署的临时状态
useSeoMeta({title: t('installWizard.seoTitle'), robots: 'noindex'})

const loading = ref(true)
const status = ref<WizardStatus | null>(null)
const loadError = ref('')

/** 当前步骤下标（对应 status.steps 的顺序） */
const step = ref(0)
const busy = ref(false)
const message = ref('')
const failed = ref(false)

const dbForm = reactive({
  host: 'localhost',
  port: 5432,
  database: 'fast_blog',
  username: 'postgres',
  password: '',
})
const adminForm = reactive({username: '', email: '', password: ''})
const siteForm = reactive({site_name: 'FastBlog', site_url: '', site_description: ''})

const currentStepKey = computed(() => status.value?.steps?.[step.value]?.key ?? '')

async function loadStatus(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    status.value = await installWizardApi.status()
  } catch {
    loadError.value = t('installWizard.loadFailed')
  } finally {
    loading.value = false
  }
}

/**
 * 统一跑一步：成功则前进，失败留在原地并显示后端给出的原因。
 * 每一步都是独立的 HTTP 调用 —— 向导状态不靠前端内存维持，刷新页面可继续。
 */
async function runStep(action: () => Promise<{ success: boolean; message: string }>): Promise<void> {
  busy.value = true
  failed.value = false
  message.value = ''
  try {
    const result = await action()
    failed.value = !result.success
    message.value = result.message || (result.success ? '' : t('installWizard.stepFailed'))
    if (result.success) step.value += 1
  } catch {
    failed.value = true
    message.value = t('installWizard.stepFailed')
  } finally {
    busy.value = false
  }
}

const onPrerequisites = () => runStep(() => installWizardApi.prerequisites())
const onDatabase = () => runStep(() => installWizardApi.database({...dbForm}))
const onMigrate = () => runStep(() => installWizardApi.migrate())
const onAdmin = () => runStep(() => installWizardApi.admin({...adminForm}))
const onSettings = () => runStep(() => installWizardApi.settings({...siteForm}))
const onComplete = () => runStep(() => installWizardApi.complete())

onMounted(loadStatus)
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-surface-soft px-4 py-10">
    <div class="w-full max-w-lg">
      <div class="mb-6 text-center">
        <NuxtLink class="text-xl font-semibold tracking-tight text-fg" to="/">FastBlog</NuxtLink>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('installWizard.subtitle') }}</p>
      </div>

      <Card>
        <CardContent class="p-6">
          <Skeleton v-if="loading" class="h-28 w-full"/>

          <p v-else-if="loadError" class="text-sm text-fg">{{ loadError }}</p>

          <!-- 向导不可用：企业部署 / 已安装，两种情况给不同出路 -->
          <template v-else-if="status && !status.available">
            <p class="text-sm font-medium text-fg">
              {{
                status.wizard_enabled
                  ? $t('installWizard.installedHint')
                  : $t('installWizard.notAvailable')
              }}
            </p>
            <p v-if="!status.wizard_enabled" class="mt-2 text-xs leading-relaxed text-fg-muted">
              {{ $t('installWizard.enterpriseHint') }}
            </p>
          </template>

          <!-- 向导可用 -->
          <template v-else-if="status">
            <!-- 步骤条：用纯 Tailwind，不引 Element Plus（前台风格一致性） -->
            <ol class="mb-5 flex flex-wrap gap-x-3 gap-y-1 text-xs">
              <li
                v-for="(s, i) in status.steps"
                :key="s.key"
                :class="[
                  'rounded px-1.5 py-0.5',
                  i === step ? 'bg-fg font-medium text-surface' : 'text-fg-muted',
                ]"
              >
                {{ i + 1 }}. {{ s.label }}
              </li>
            </ol>

            <!-- 已完成 -->
            <div v-if="step >= status.steps.length" class="space-y-3">
              <p class="text-sm font-medium text-fg">{{ $t('installWizard.done') }}</p>
              <p class="text-xs leading-relaxed text-fg-muted">
                {{ $t('installWizard.doneHint') }}
              </p>
              <Button class="w-full" @click="navigateTo('/login')">
                {{ $t('installWizard.goLogin') }}
              </Button>
            </div>

            <!-- 当前步 -->
            <div v-else class="space-y-4">
              <div>
                <p class="text-sm font-medium text-fg">
                  {{ status.steps[step]?.label }}
                </p>
                <p class="mt-0.5 text-xs text-fg-muted">
                  {{ status.steps[step]?.description }}
                </p>
              </div>

              <!-- 数据库 -->
              <div v-if="currentStepKey === 'database'" class="space-y-3">
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="db-host">
                    {{ $t('installWizard.db.host') }}
                  </label>
                  <Input id="db-host" v-model="dbForm.host" autocomplete="off"/>
                </div>
                <div class="flex gap-3">
                  <div class="flex-1">
                    <label class="mb-1 block text-xs text-fg-muted" for="db-port">
                      {{ $t('installWizard.db.port') }}
                    </label>
                    <Input id="db-port" v-model.number="dbForm.port" type="number"/>
                  </div>
                  <div class="flex-1">
                    <label class="mb-1 block text-xs text-fg-muted" for="db-name">
                      {{ $t('installWizard.db.database') }}
                    </label>
                    <Input id="db-name" v-model="dbForm.database" autocomplete="off"/>
                  </div>
                </div>
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="db-user">
                    {{ $t('installWizard.db.username') }}
                  </label>
                  <Input id="db-user" v-model="dbForm.username" autocomplete="off"/>
                </div>
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="db-pass">
                    {{ $t('installWizard.db.password') }}
                  </label>
                  <Input id="db-pass" v-model="dbForm.password" autocomplete="new-password" type="password"/>
                </div>
              </div>

              <!-- 管理员 -->
              <div v-else-if="currentStepKey === 'admin'" class="space-y-3">
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="ad-user">
                    {{ $t('installWizard.admin.username') }}
                  </label>
                  <Input id="ad-user" v-model="adminForm.username" autocomplete="off"/>
                </div>
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="ad-mail">
                    {{ $t('installWizard.admin.email') }}
                  </label>
                  <Input id="ad-mail" v-model="adminForm.email" autocomplete="off" type="email"/>
                </div>
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="ad-pass">
                    {{ $t('installWizard.admin.password') }}
                  </label>
                  <Input
                    id="ad-pass"
                    v-model="adminForm.password"
                    autocomplete="new-password"
                    type="password"
                  />
                  <p class="mt-1 text-xs text-fg-muted">{{ $t('installWizard.admin.passwordHint') }}</p>
                </div>
              </div>

              <!-- 站点设置 -->
              <div v-else-if="currentStepKey === 'settings'" class="space-y-3">
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="st-name">
                    {{ $t('installWizard.site.siteName') }}
                  </label>
                  <Input id="st-name" v-model="siteForm.site_name"/>
                </div>
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="st-url">
                    {{ $t('installWizard.site.siteUrl') }}
                  </label>
                  <Input id="st-url" v-model="siteForm.site_url" placeholder="https://example.com"/>
                </div>
                <div>
                  <label class="mb-1 block text-xs text-fg-muted" for="st-desc">
                    {{ $t('installWizard.site.siteDescription') }}
                  </label>
                  <Input id="st-desc" v-model="siteForm.site_description"/>
                </div>
              </div>

              <!-- 结果提示 -->
              <p v-if="message" :class="['text-xs leading-relaxed', failed ? 'text-fg' : 'text-fg-muted']">
                {{ message }}
              </p>

              <div class="flex gap-2">
                <Button
                  v-if="step > 0"
                  :disabled="busy"
                  class="flex-1"
                  variant="outline"
                  @click="step -= 1"
                >
                  {{ $t('installWizard.prev') }}
                </Button>

                <Button
                  v-if="currentStepKey === 'prerequisites'"
                  :disabled="busy"
                  class="flex-1"
                  @click="onPrerequisites"
                >
                  {{ $t('installWizard.runCheck') }}
                </Button>
                <Button
                  v-else-if="currentStepKey === 'database'"
                  :disabled="busy"
                  class="flex-1"
                  @click="onDatabase"
                >
                  {{ $t('installWizard.testAndSave') }}
                </Button>
                <Button
                  v-else-if="currentStepKey === 'migration'"
                  :disabled="busy"
                  class="flex-1"
                  @click="onMigrate"
                >
                  {{ $t('installWizard.runMigrate') }}
                </Button>
                <Button
                  v-else-if="currentStepKey === 'admin'"
                  :disabled="busy"
                  class="flex-1"
                  @click="onAdmin"
                >
                  {{ $t('installWizard.createAdmin') }}
                </Button>
                <Button
                  v-else-if="currentStepKey === 'settings'"
                  :disabled="busy"
                  class="flex-1"
                  @click="onSettings"
                >
                  {{ $t('installWizard.saveSettings') }}
                </Button>
                <Button
                  v-else-if="currentStepKey === 'complete'"
                  :disabled="busy"
                  class="flex-1"
                  @click="onComplete"
                >
                  {{ $t('installWizard.finish') }}
                </Button>
              </div>
            </div>
          </template>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
