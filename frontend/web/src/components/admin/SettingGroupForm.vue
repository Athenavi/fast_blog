<script lang="ts" setup>
/**
 * 设置项分组表单
 *
 * 背景：系统设置此前是一张 `key / value / 描述` 的裸表格，管理员要面对
 * `smtp_host`、`site_name` 这类原始键名和裸字符串，没有分组、没有类型化控件。
 *
 * 这里按 **key 前缀**推导分组（后端没有 group 字段），并按 `setting_type` 渲染控件：
 * boolean → 开关、number → 数字、json → 文本域、其余 → 输入框。
 * 保存走后端已有的批量接口 `PUT /system/setting`（`batchSave`），且只提交**本组内改动过**的项。
 */
import {computed, reactive, watch} from 'vue'

import type {SettingItem, SettingUpsert} from '@/api'
import {ElMessage} from '@/utils/feedback'

const props = defineProps<{
  items: SettingItem[]
  saving?: boolean
}>()

const emit = defineEmits<{ (e: 'save', payload: SettingUpsert[]): void }>()

const {t} = useI18n()

/** 分组规则（顺序即展示顺序）；未命中任何规则的进 "other" */
const GROUP_RULES: Array<{ key: string; test: RegExp }> = [
  {key: 'site', test: /^(site|brand|footer|icp|about)[_.]/i},
  {key: 'seo', test: /^seo[_.]/i},
  {key: 'content', test: /^(content|article|post|page|category)[_.]/i},
  {key: 'comment', test: /^comment[_.]/i},
  {key: 'security', test: /^(security|auth|login|user|password|session|sensitive|gdpr)[_.]/i},
  {key: 'mail', test: /^(smtp|mail|email)[_.]/i},
  {key: 'storage', test: /^(storage|upload|media|cdn|image|oss|s3)[_.]/i},
]

function groupKeyOf(key: string): string {
  return GROUP_RULES.find((rule) => rule.test.test(key))?.key ?? 'other'
}

const groups = computed(() => {
  const map = new Map<string, SettingItem[]>()
  for (const item of props.items) {
    const key = groupKeyOf(item.setting_key)
    map.set(key, [...(map.get(key) ?? []), item])
  }
  return [...map.entries()].map(([key, items]) => ({key, items}))
})

/** 草稿值：后端 `setting_value` 本身就是字符串 */
const draft = reactive<Record<string, string>>({})

function originalOf(item: SettingItem): string {
  return item.setting_value ?? ''
}

watch(
  () => props.items,
  (items) => {
    for (const key of Object.keys(draft)) delete draft[key]
    for (const item of items) draft[item.setting_key] = originalOf(item)
  },
  {immediate: true, deep: true},
)

function changedIn(groupItems: SettingItem[]): SettingUpsert[] {
  return groupItems
    .filter((item) => (draft[item.setting_key] ?? '') !== originalOf(item))
    .map((item) => ({
      setting_key: item.setting_key,
      setting_value: draft[item.setting_key] ?? '',
      setting_type: item.setting_type ?? 'string',
      description: item.description ?? undefined,
      is_public: item.is_public,
    }))
}

function saveGroup(groupItems: SettingItem[]): void {
  const payload = changedIn(groupItems)
  if (!payload.length) {
    ElMessage.info(t('admin.system.setting.noChange'))
    return
  }
  emit('save', payload)
}

/** 按 `setting_type` 决定控件形态 */
function controlType(item: SettingItem): 'boolean' | 'number' | 'json' | 'string' {
  const type = (item.setting_type ?? 'string').toLowerCase()
  if (type === 'boolean' || type === 'bool') return 'boolean'
  if (type === 'number' || type === 'int' || type === 'integer' || type === 'float') return 'number'
  if (type === 'json' || type === 'array' || type === 'object') return 'json'
  return 'string'
}

function boolValue(key: string): boolean {
  return String(draft[key] ?? '').toLowerCase() === 'true'
}

function setBool(key: string, value: boolean): void {
  draft[key] = value ? 'true' : 'false'
}

function setNumber(key: string, value: number | undefined): void {
  draft[key] = String(value ?? 0)
}
</script>

<template>
  <div class="setting-groups">
    <el-card v-for="group in groups" :key="group.key" class="setting-group" shadow="never">
      <template #header>
        <div class="setting-group__header">
          <span class="setting-group__title">{{ t(`admin.system.setting.group.${group.key}`) }}</span>
          <el-button :disabled="saving" link type="primary" @click="saveGroup(group.items)">
            {{ t('admin.system.setting.saveGroup') }}
          </el-button>
        </div>
      </template>

      <el-form label-position="top">
        <el-form-item v-for="item in group.items" :key="item.setting_key">
          <template #label>
            <span class="setting-item__label">
              <span>{{ item.description || item.setting_key }}</span>
              <code class="setting-item__key">{{ item.setting_key }}</code>
              <el-tag v-if="item.is_public" size="small" type="info">
                {{ t('admin.system.setting.publicLabel') }}
              </el-tag>
            </span>
          </template>

          <el-switch
            v-if="controlType(item) === 'boolean'"
            :model-value="boolValue(item.setting_key)"
            @update:model-value="(value: string | number | boolean) => setBool(item.setting_key, Boolean(value))"
          />
          <el-input-number
            v-else-if="controlType(item) === 'number'"
            :model-value="Number(draft[item.setting_key] ?? 0)"
            @update:model-value="(value: number | undefined) => setNumber(item.setting_key, value)"
          />
          <el-input
            v-else-if="controlType(item) === 'json'"
            v-model="draft[item.setting_key]"
            :rows="4"
            type="textarea"
          />
          <el-input v-else v-model="draft[item.setting_key]"/>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.setting-groups {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap);
}

.setting-group__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setting-group__title {
  font-weight: 600;
}

.setting-item__label {
  display: inline-flex;
  gap: var(--admin-gap-sm);
  align-items: center;
}

.setting-item__key {
  padding: 0 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--admin-fg-subtle);
  background: var(--admin-surface-soft);
  border-radius: 4px;
}
</style>
