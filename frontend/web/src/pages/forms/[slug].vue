<script lang="ts" setup>
/**
 * 公开表单填写页（前台）
 *
 * 对接 v3 两个公开端点（无需登录）：
 *  - GET  /marketing/form/public/{slug}         取已发布表单定义与激活字段
 *  - POST /marketing/form/public/{slug}/submit  匿名提交
 *
 * 服务端渲染取定义、客户端提交；提交体为 `{data: {字段 label: 值}}`，
 * 键取自字段 label（后端按 label 从 data 中取值），网络逻辑在 formApi。
 */
import {formApi, type FormPublicDetail, type FormPublicField} from '@/api'

const {t} = useI18n()
const route = useRoute()
const slug = String(route.params.slug)

definePageMeta({layout: 'default'})

const site = await useSiteInfo()

const {data: form} = await useAsyncData(`form-public-${slug}`, () =>
  apiGet<FormPublicDetail>(`/marketing/form/public/${slug}`),
)

if (!form.value) {
  throw createError({statusCode: 404, statusMessage: t('publicForm.notFound')})
}

useSeoMeta({
  title: () => `${form.value?.title || t('publicForm.title')} - ${site.value.site_name || 'FastBlog'}`,
  description: () => form.value?.description || '',
})

interface LocalField {
  key: string
  label: string
  type: string
  placeholder: string
  help: string
  required: boolean
  options: string[]
}

/** 后端 options 约定为逗号分隔字符串 */
function parseOptions(raw?: string | null): string[] {
  return (raw ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

const localFields = computed<LocalField[]>(() =>
  (form.value?.fields ?? []).map((f: FormPublicField) => ({
    key: f.label ?? '',
    label: f.label ?? '',
    type: f.field_type ?? 'text',
    placeholder: f.placeholder ?? '',
    help: f.help_text ?? '',
    required: f.required,
    options: parseOptions(f.options),
  })),
)

/** 表单值统一以字符串承载；复选多选以逗号拼接（选项本身不含逗号），单个复选框存 '1' / '' */
const model = reactive<Record<string, string>>({})
const errors = ref<Record<string, string>>({})
const submitting = ref(false)
const submitted = ref(false)
const submitMessage = ref('')
const failed = ref(false)

/** 为每个字段准备初始值（仅缺失时写入，避免覆盖用户输入） */
watch(
  localFields,
  (list) => {
    for (const f of list) {
      if (!(f.key in model)) model[f.key] = ''
    }
  },
  {immediate: true},
)

function controlId(index: number): string {
  return `ff-${index}`
}

function errorId(index: number): string {
  return `ff-${index}-err`
}

function splitSelected(value: string): string[] {
  return value ? value.split(',') : []
}

function isChecked(event: Event): boolean {
  const target = event.target
  return target instanceof HTMLInputElement ? target.checked : false
}

function clearError(key: string): void {
  if (!errors.value[key]) return
  const next = {...errors.value}
  delete next[key]
  errors.value = next
}

function onToggleSingle(key: string, event: Event): void {
  model[key] = isChecked(event) ? '1' : ''
  clearError(key)
}

function onToggleOption(key: string, option: string, event: Event): void {
  const current = splitSelected(model[key] ?? '')
  const checked = isChecked(event)
  const index = current.indexOf(option)
  if (checked && index === -1) current.push(option)
  if (!checked && index !== -1) current.splice(index, 1)
  model[key] = current.join(',')
  clearError(key)
}

/** 与后端必填判定一致：空白字符串 / 空多选 / 未勾选 视为缺失 */
function isBlank(field: LocalField): boolean {
  const value = model[field.key] ?? ''
  if (field.type === 'checkbox') {
    return field.options.length ? value.trim() === '' : value !== '1'
  }
  return value.trim() === ''
}

async function onSubmit(): Promise<void> {
  // 阻断重复提交：进行中或已成功都不再触发
  if (submitting.value || submitted.value) return
  failed.value = false

  const nextErrors: Record<string, string> = {}
  for (const f of localFields.value) {
    if (f.required && isBlank(f)) nextErrors[f.key] = t('publicForm.fieldRequired', {label: f.label})
  }
  errors.value = nextErrors
  if (Object.keys(nextErrors).length > 0) return

  const data: Record<string, unknown> = {}
  for (const f of localFields.value) {
    data[f.key] = model[f.key] ?? ''
  }

  submitting.value = true
  try {
    const result = await formApi.publicSubmit(slug, data)
    if (result?.accepted) {
      submitMessage.value = form.value?.submit_message || t('publicForm.success')
      submitted.value = true
    } else {
      failed.value = true
    }
  } catch {
    failed.value = true
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">
      {{ form?.title || t('publicForm.title') }}
    </h1>
    <p v-if="form?.description" class="mt-3 text-fg-muted">{{ form.description }}</p>

    <div
      v-if="submitted"
      class="mt-8 flex flex-col items-start gap-3 rounded-card border border-line bg-surface p-6"
      role="status"
    >
      <Icon class="h-8 w-8 text-primary" name="circle-check"/>
      <p class="text-base font-medium text-fg">{{ submitMessage }}</p>
    </div>

    <form v-else class="mt-8 space-y-6" novalidate @submit.prevent="onSubmit">
      <EmptyState v-if="!localFields.length" :title="t('publicForm.noFields')"/>

      <template v-for="(f, i) in localFields" :key="f.key">
        <div>
          <!-- 单个复选框：标签即字段名，内联渲染 -->
          <template v-if="f.type === 'checkbox' && !f.options.length">
            <label :for="controlId(i)" class="flex items-center gap-2 text-sm font-medium text-fg">
              <input
                :id="controlId(i)"
                :aria-describedby="errors[f.key] ? errorId(i) : undefined"
                :aria-invalid="errors[f.key] ? 'true' : undefined"
                :checked="model[f.key] === '1'"
                class="h-4 w-4 rounded border-line text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                type="checkbox"
                @change="onToggleSingle(f.key, $event)"
              >
              {{ f.label }}<span v-if="f.required" class="text-danger">*</span>
            </label>
          </template>

          <template v-else>
            <label :for="controlId(i)" class="mb-1.5 block text-sm font-medium text-fg">
              {{ f.label }}<span v-if="f.required" class="text-danger">*</span>
            </label>

            <textarea
              v-if="f.type === 'textarea'"
              :id="controlId(i)"
              v-model="model[f.key]"
              :aria-describedby="errors[f.key] ? errorId(i) : undefined"
              :aria-invalid="errors[f.key] ? 'true' : undefined"
              :placeholder="f.placeholder"
              class="flex w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg transition-colors placeholder:text-fg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              rows="4"
              @input="clearError(f.key)"
            />

            <select
              v-else-if="f.type === 'select'"
              :id="controlId(i)"
              v-model="model[f.key]"
              :aria-describedby="errors[f.key] ? errorId(i) : undefined"
              :aria-invalid="errors[f.key] ? 'true' : undefined"
              class="flex h-9 w-full rounded-control border border-line bg-surface px-3 text-sm text-fg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              @change="clearError(f.key)"
            >
              <option value="">{{ t('publicForm.selectPlaceholder') }}</option>
              <option v-for="opt in f.options" :key="opt" :value="opt">{{ opt }}</option>
            </select>

            <div v-else-if="f.type === 'radio'" class="space-y-2">
              <label v-for="opt in f.options" :key="opt" class="flex items-center gap-2 text-sm text-fg">
                <input
                  v-model="model[f.key]"
                  :name="controlId(i)"
                  :value="opt"
                  class="h-4 w-4 border-line text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  type="radio"
                  @change="clearError(f.key)"
                >
                {{ opt }}
              </label>
            </div>

            <div v-else-if="f.type === 'checkbox'" class="space-y-2">
              <label v-for="opt in f.options" :key="opt" class="flex items-center gap-2 text-sm text-fg">
                <input
                  :checked="splitSelected(model[f.key] ?? '').includes(opt)"
                  :value="opt"
                  class="h-4 w-4 rounded border-line text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  type="checkbox"
                  @change="onToggleOption(f.key, opt, $event)"
                >
                {{ opt }}
              </label>
            </div>

            <Input
              v-else
              :id="controlId(i)"
              v-model="model[f.key]"
              :placeholder="f.placeholder"
              :type="f.type"
              @input="clearError(f.key)"
            />
          </template>

          <p
            v-if="f.help && !(f.type === 'checkbox' && !f.options.length)"
            class="mt-1.5 text-xs text-fg-subtle"
          >
            {{ f.help }}
          </p>
          <p v-if="errors[f.key]" :id="errorId(i)" class="mt-1.5 text-sm text-danger">
            {{ errors[f.key] }}
          </p>
        </div>
      </template>

      <p v-if="failed" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger" role="alert">
        {{ t('publicForm.failed') }}
      </p>

      <Button :disabled="submitting" class="w-full" type="submit">
        <Icon v-if="submitting" class="h-4 w-4 animate-spin" name="loader-circle"/>
        {{ submitting ? t('publicForm.submitting') : t('publicForm.submit') }}
      </Button>
    </form>
  </div>
</template>
