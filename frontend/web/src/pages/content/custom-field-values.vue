<script lang="ts" setup>
/**
 * 自定义字段值（/content/custom-field-values，content 域）
 *
 * 后端 `custom_post_types.fields` 存放字段定义（JSON 字符串），字段值存在 EAV 表
 * `custom_fields`（一行一个字段）。本页按定义**动态渲染**表单，覆盖后端支持的全部类型：
 * text / textarea / richtext / number / boolean / select / date / url / email / json。
 *
 * 对齐 v3 的两个端点（`custom_post_type/controller.py`）：
 *   GET /content/custom-post-type/{type_id}/values/{content_id}   读（未填字段按定义补 null）
 *   PUT /content/custom-post-type/{type_id}/values/{content_id}   写（**全量语义**）
 *
 * ⚠️ PUT 是全量语义：必填缺失、类型不符、出现未定义字段名都会被后端拒绝（400），
 *    所以这里不做“局部提交”。前端先做一次规范化，后端仍会二次校验。
 *
 * 权限：读 `module_content:custom_post_type:view`；写 `module_content:custom_post_type:edit`。
 */
import {computed, onMounted, ref} from 'vue'

import {type CustomFieldEntry, customPostTypeApi, type CustomPostTypeItem} from '@/api'
import {ElMessage} from '@/utils/feedback'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.customFieldValues.title',
  permission: 'module_content:custom_post_type:view',
})

const {t} = useI18n()

const types = ref<CustomPostTypeItem[]>([])
const typeId = ref<number | null>(null)
const contentId = ref<number | null>(null)
const loading = ref(false)
const saving = ref(false)

/** 字段定义（由所选类型的 `fields` JSON 解析而来） */
const entries = ref<CustomFieldEntry[]>([])
/** 表单值。用宽松类型承接多种控件（checkbox / number / 文本），提交前统一规范化 */
const editing = ref<Record<string, any>>({})

const currentType = computed(() => types.value.find((item) => item.id === typeId.value) ?? null)

function parseEntries(raw?: string | null): CustomFieldEntry[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as CustomFieldEntry[]) : []
  } catch {
    return []
  }
}

/** 类型 → 原生 input 的 type 属性（其余走文本） */
function inputType(entry: CustomFieldEntry): string {
  const map: Record<string, string> = {number: 'number', date: 'date', url: 'url', email: 'email'}
  return map[entry.type] ?? 'text'
}

/** JSON 字段的输入提示。
 *
 * 放在 script 而不是模板里：Vue 模板表达式中的花括号会被解析器当作对象字面量，
 * `:placeholder="'{\"k\": 1}'"` 这种写法直接导致 TS1005 语法错误。
 */
const jsonPlaceholder = '{"key": "value"}'

function isLongText(entry: CustomFieldEntry): boolean {
  return entry.type === 'textarea' || entry.type === 'richtext' || entry.type === 'json'
}

async function loadTypes() {
  try {
    const data = await customPostTypeApi.list({page: 1, page_size: 100})
    types.value = data?.items ?? []
    if (types.value.length && typeId.value === null) typeId.value = types.value[0]!.id
  } catch {
    // http 层已提示
  }
}

/** 载入字段值：boolean 与 select 多选需要反显转换 */
async function loadValues() {
  if (!typeId.value || !contentId.value) {
    ElMessage.warning(t('admin.content.customFieldValues.typeAndContentRequired'))
    return
  }

  loading.value = true
  try {
    entries.value = parseEntries(currentType.value?.fields)
    if (!entries.value.length) ElMessage.warning(t('admin.content.customFieldValues.noFields'))

    const data = await customPostTypeApi.getValues(typeId.value, contentId.value)
    const next: Record<string, any> = {}
    for (const entry of entries.value) {
      const value = data?.values?.[entry.key]
      if (entry.type === 'boolean') {
        next[entry.key] = value === true || value === 'true' || value === 1
      } else if (entry.type === 'select' && entry.multiple && Array.isArray(value)) {
        next[entry.key] = value.join(', ')
      } else {
        next[entry.key] = value ?? ''
      }
    }
    editing.value = next
  } catch {
    entries.value = []
    editing.value = {}
  } finally {
    loading.value = false
  }
}

/** 提交前的规范化（后端还会按定义二次校验并给出 400） */
function normalizeForSubmit(entry: CustomFieldEntry, value: unknown): unknown {
  if (entry.type === 'boolean') return Boolean(value)

  if (entry.type === 'select' && entry.multiple) {
    if (Array.isArray(value)) return value
    return String(value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }

  if (entry.type === 'number') {
    if (value === '' || value === null || value === undefined) return null
    const num = Number(value)
    return Number.isNaN(num) ? value : num
  }

  return value
}

async function save() {
  if (!typeId.value || !contentId.value) {
    ElMessage.warning(t('admin.content.customFieldValues.typeAndContentRequired'))
    return
  }

  const payload: Record<string, unknown> = {}
  for (const entry of entries.value) {
    payload[entry.key] = normalizeForSubmit(entry, editing.value[entry.key])
  }

  saving.value = true
  try {
    const result = await customPostTypeApi.setValues(typeId.value, contentId.value, payload)
    ElMessage.success(t('admin.content.customFieldValues.saved', {count: result?.updated?.length ?? 0}))
    await loadValues()
  } catch {
    // 必填缺失 / 未定义字段名 / 类型不符 → 后端 400，http 层已提示
  } finally {
    saving.value = false
  }
}

onMounted(loadTypes)
</script>

<template>
  <AdminPage
    :desc="t('admin.content.customFieldValues.desc')"
    :title="t('admin.content.customFieldValues.title')"
  >
    <div class="space-y-4">

    <!-- 目标选择 -->
    <div class="flex flex-wrap items-end gap-2">
      <label class="text-sm">
        <span class="mb-1 block text-fg-subtle">{{ t('admin.content.customFieldValues.typeLabel') }}</span>
        <select v-model.number="typeId" class="rounded border border-default px-3 py-1.5 text-sm">
          <option v-for="item in types" :key="item.id" :value="item.id">{{ item.name || item.slug || item.id }}</option>
        </select>
      </label>

      <label class="text-sm">
        <span class="mb-1 block text-fg-subtle">{{ t('admin.content.customFieldValues.contentIdLabel') }}</span>
        <input v-model.number="contentId" class="w-32 rounded border border-default px-3 py-1.5 text-sm" min="1"
               type="number">
      </label>

      <button
        :disabled="loading"
        class="rounded-md border border-default px-3 py-1.5 text-sm disabled:opacity-50"
        type="button"
        @click="loadValues"
      >
        {{ loading ? t('common.loading') : t('admin.content.customFieldValues.load') }}
      </button>
    </div>

    <div v-if="!types.length" class="rounded-lg bg-surface-soft p-4 text-sm text-fg-subtle">
      {{ t('admin.content.customFieldValues.noTypes') }}
    </div>

    <div v-else-if="!entries.length" class="rounded-lg bg-surface-soft p-4 text-sm text-fg-subtle">
      {{ t('admin.content.customFieldValues.needLoad') }}
    </div>

    <!-- 动态表单 -->
    <template v-else>
      <div class="space-y-3">
        <div v-for="entry in entries" :key="entry.key" class="rounded-lg border border-default p-3">
          <label class="block text-sm font-medium">
            {{ entry.label }}
            <span v-if="entry.required" class="text-danger">*</span>
            <code class="ml-2 text-xs text-fg-subtle">{{ entry.key }} · {{ entry.type }}</code>
          </label>
          <p v-if="entry.help" class="mt-0.5 text-xs text-fg-subtle">{{ entry.help }}</p>

          <input
            v-if="entry.type === 'boolean'"
            v-model="editing[entry.key]"
            class="mt-2"
            type="checkbox"
          >

          <select
            v-else-if="entry.type === 'select' && !entry.multiple"
            v-model="editing[entry.key]"
            class="mt-2 w-full rounded border border-default px-3 py-2 text-sm"
          >
            <option value="">{{ t('admin.content.customFieldValues.selectPlaceholder') }}</option>
            <option v-for="option in entry.options ?? []" :key="option" :value="option">{{ option }}</option>
          </select>

          <textarea
            v-else-if="isLongText(entry)"
            v-model="editing[entry.key]"
            :placeholder="entry.type === 'json' ? jsonPlaceholder : ''"
            class="mt-2 w-full rounded border border-default px-3 py-2 font-mono text-xs"
            rows="3"
          />

          <input
            v-else
            v-model="editing[entry.key]"
            :max="entry.max ?? undefined"
            :min="entry.min ?? undefined"
            :type="inputType(entry)"
            class="mt-2 w-full rounded border border-default px-3 py-2 text-sm"
          >

          <p v-if="entry.type === 'select' && entry.multiple" class="mt-1 text-xs text-fg-subtle">
            {{ t('admin.content.customFieldValues.multiHint') }}
          </p>
        </div>
      </div>

      <div class="flex justify-end">
        <button
          :disabled="saving"
          class="rounded-md bg-primary px-3 py-1.5 text-sm text-white disabled:opacity-50"
          type="button"
          @click="save"
        >
          {{ saving ? t('common.submitting') : t('admin.content.customFieldValues.save') }}
        </button>
      </div>
    </template>
  </div>
  </AdminPage>
</template>
