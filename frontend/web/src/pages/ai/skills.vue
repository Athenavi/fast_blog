<script lang="ts" setup>
/**
 * AI 技能（`/ai/skill`）
 *
 * 后端技能是**代码注册表**（不是数据库记录）：每个技能都调用 v3 已有真实服务
 * （LLM / SEO / 迁移解析 / 真表聚合），没有空壳技能。
 *
 * 本页做三件事：
 *  - 列出技能（可按分类 / 关键字服务端过滤）；
 *  - 查看技能详情（参数说明直接来自后端声明，不在前端硬编码）；
 *  - 执行技能（按声明的参数渲染输入；执行前远端会再校验技能声明的权限）。
 */
import {Refresh, VideoPlay} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {onMounted, reactive, ref} from 'vue'

import {aiSkillApi, type AiSkillCategory, type AiSkillItem, type AiSkillRunResult} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ai.skill.title',
  permission: 'module_ai:workflow:view',
})

const {t} = useI18n()

const loading = ref(false)
const failed = ref(false)
const skills = ref<AiSkillItem[]>([])
const categories = ref<AiSkillCategory[]>([])

/** 服务端过滤条件 */
const filters = reactive({category: '', keyword: ''})

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const result = await aiSkillApi.list({
      category: filters.category || undefined,
      keyword: filters.keyword.trim() || undefined,
    })
    skills.value = result.items
  } catch {
    // 失败提示由 request 层统一弹出
    failed.value = true
    skills.value = []
  } finally {
    loading.value = false
  }
}

async function loadCategories(): Promise<void> {
  try {
    categories.value = await aiSkillApi.categories()
  } catch {
    categories.value = []
  }
}

function resetFilters(): void {
  filters.category = ''
  filters.keyword = ''
  load().catch(() => undefined)
}

onMounted(async () => {
  await Promise.all([loadCategories(), load()])
})

// ---------------------------------------------------------------- 技能详情
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<AiSkillItem | null>(null)

async function openDetail(row: AiSkillItem): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await aiSkillApi.detail(row.name)
  } catch {
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

// ---------------------------------------------------------------- 执行技能
const runVisible = ref(false)
const running = ref(false)
const runTarget = ref<AiSkillItem | null>(null)
const runConfigId = ref<number | undefined>(undefined)
const runResult = ref<AiSkillRunResult | null>(null)
/** 参数输入值（一律以字符串暂存，提交时按声明类型转换） */
const runValues = reactive<Record<string, string>>({})

function openRun(row: AiSkillItem): void {
  runTarget.value = row
  runResult.value = null
  runConfigId.value = undefined
  for (const key of Object.keys(runValues)) delete runValues[key]
  for (const param of row.params) {
    runValues[param.name] = param.default === undefined ? '' : String(param.default)
  }
  runVisible.value = true
}

/** 按后端声明的类型把输入转成请求参数；留空/未填的可选参数不下发 */
function buildParams(skill: AiSkillItem): Record<string, unknown> {
  const payload: Record<string, unknown> = {}
  for (const param of skill.params) {
    const raw = (runValues[param.name] ?? '').trim()
    if (raw === '') continue
    if (param.type === 'int') {
      const num = Number(raw)
      if (Number.isFinite(num)) payload[param.name] = Math.trunc(num)
      continue
    }
    if (param.type === 'bool' || param.type === 'boolean') {
      payload[param.name] = raw === 'true' || raw === '1'
      continue
    }
    payload[param.name] = raw
  }
  return payload
}

async function submitRun(): Promise<void> {
  const skill = runTarget.value
  if (!skill) return
  const payloadParams = buildParams(skill)
  const missing = skill.params.filter(
    (param) => param.required && payloadParams[param.name] === undefined,
  )
  if (missing.length) {
    ElMessage.warning(t('admin.ai.skill.requiredMissing', {fields: missing.map((m) => m.name).join(', ')}))
    return
  }

  running.value = true
  try {
    runResult.value = await aiSkillApi.run(skill.name, {
      params: payloadParams,
      config_id: runConfigId.value ?? null,
    })
    ElMessage.success(t('admin.ai.skill.runSuccess', {ms: runResult.value.duration_ms}))
  } finally {
    running.value = false
  }
}

/** 结果 JSON 文本（技能返回值形状由技能自己决定，这里原样展示） */
function resultText(result: AiSkillRunResult | null): string {
  if (!result) return ''
  return JSON.stringify(result.result, null, 2)
}
</script>

<template>
  <AdminPage :desc="$t('admin.ai.skill.desc')" :title="$t('admin.ai.skill.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="load()">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-form class="mb-3" inline @submit.prevent>
      <el-form-item :label="$t('admin.ai.skill.category')">
        <el-select v-model="filters.category" :placeholder="$t('admin.ai.skill.categoryAll')" clearable
                   style="width: 200px" @change="load()">
          <el-option v-for="item in categories" :key="item.category" :label="item.label" :value="item.category"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.ai.skill.keyword')">
        <el-input v-model="filters.keyword" :placeholder="$t('admin.ai.skill.keywordPlaceholder')" clearable
                  style="width: 220px" @keyup.enter="load()"/>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="load()">{{ $t('admin.common.search') }}</el-button>
        <el-button @click="resetFilters">{{ $t('admin.common.reset') }}</el-button>
      </el-form-item>
    </el-form>

    <div v-if="failed"
         class="mb-3 flex items-center gap-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
      <span>{{ $t('admin.ai.skill.loadFailed') }}</span>
      <el-button link type="primary" @click="load()">{{ $t('admin.common.retry') }}</el-button>
    </div>

    <el-table v-loading="loading" :data="skills" border stripe>
      <el-table-column :label="$t('admin.ai.skill.label')" min-width="150" prop="label"/>
      <el-table-column :label="$t('admin.ai.skill.name')" min-width="160" prop="name"/>
      <el-table-column :label="$t('admin.ai.skill.category')" prop="category_label" width="120"/>
      <el-table-column :label="$t('admin.ai.skill.requiredPermission')" min-width="220">
        <template #default="{row}">
          <span v-if="row.required_permission">{{ row.required_permission }}</span>
          <span v-else class="text-fg-subtle">{{ $t('admin.ai.skill.noPermission') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.ai.skill.description')" min-width="280" prop="description"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="170">
        <template #default="{row}">
          <el-button link type="primary" @click="openDetail(row)">{{ $t('admin.ai.skill.detail') }}</el-button>
          <el-button v-auth="'module_ai:workflow:execute'" link type="primary" @click="openRun(row)">
            {{ $t('admin.ai.skill.run') }}
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="$t('admin.ai.skill.empty')"/>
      </template>
    </el-table>

    <!-- 技能详情：参数说明直接来自后端声明 -->
    <el-drawer v-model="detailVisible" :title="$t('admin.ai.skill.detailTitle')" size="560px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions :column="1" border>
            <el-descriptions-item :label="$t('admin.ai.skill.name')">{{ detail.name }}</el-descriptions-item>
            <el-descriptions-item :label="$t('admin.ai.skill.label')">{{ detail.label }}</el-descriptions-item>
            <el-descriptions-item :label="$t('admin.ai.skill.category')">{{
                detail.category_label
              }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.ai.skill.requiredPermission')">
              {{ detail.required_permission || $t('admin.ai.skill.noPermission') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.ai.skill.description')">{{
                detail.description
              }}
            </el-descriptions-item>
          </el-descriptions>

          <h4 class="mt-4 mb-2 font-medium text-fg">{{ $t('admin.ai.skill.params') }}</h4>
          <el-table :data="detail.params" border size="small">
            <el-table-column :label="$t('admin.ai.skill.paramName')" prop="name" width="140"/>
            <el-table-column :label="$t('admin.ai.skill.paramType')" prop="type" width="90"/>
            <el-table-column :label="$t('admin.ai.skill.paramRequired')" width="90">
              <template #default="{row}">
                {{ row.required ? $t('admin.ai.skill.yes') : $t('admin.ai.skill.no') }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.ai.skill.paramDescription')" min-width="200" prop="description"/>
          </el-table>
          <p v-if="!detail.params.length" class="mt-2 text-sm text-fg-muted">{{ $t('admin.ai.skill.noParams') }}</p>
        </template>
      </div>
    </el-drawer>

    <!-- 执行技能 -->
    <el-dialog v-model="runVisible" :title="$t('admin.ai.skill.runTitle', {name: runTarget?.label ?? ''})"
               width="680px">
      <template v-if="runTarget">
        <el-alert :closable="false" :title="$t('admin.ai.skill.runHint')" class="mb-3" type="info"/>

        <el-form label-width="150px">
          <el-form-item v-for="param in runTarget.params" :key="param.name" :label="param.name"
                        :required="param.required">
            <el-input v-model="runValues[param.name]" :placeholder="param.description || ''" clearable/>
            <p class="mt-1 text-xs text-fg-subtle">{{
                param.type
              }}{{ param.required ? ' · ' + $t('admin.ai.skill.paramRequired') : '' }}</p>
          </el-form-item>
          <el-form-item :label="$t('admin.ai.skill.configId')">
            <el-input-number v-model="runConfigId" :controls="false" :min="1" style="width: 180px"/>
            <span class="ml-2 text-xs text-fg-subtle">{{ $t('admin.ai.skill.configIdHint') }}</span>
          </el-form-item>
        </el-form>

        <template v-if="runResult">
          <el-divider/>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="$t('admin.ai.skill.runSkill')">{{ runResult.label }}</el-descriptions-item>
            <el-descriptions-item :label="$t('admin.ai.skill.runDuration')">{{ runResult.duration_ms }} ms
            </el-descriptions-item>
          </el-descriptions>
          <h4 class="mt-3 mb-2 font-medium text-fg">{{ $t('admin.ai.skill.runResult') }}</h4>
          <pre class="skill-result">{{ resultText(runResult) }}</pre>
        </template>
      </template>

      <template #footer>
        <el-button @click="runVisible = false">{{ $t('admin.common.close') }}</el-button>
        <el-button :icon="VideoPlay" :loading="running" type="primary" @click="submitRun">
          {{ $t('admin.ai.skill.run') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.skill-result {
  max-height: 320px;
  margin: 0;
  overflow: auto;
  border: 1px solid var(--admin-border, #e5e7eb);
  border-radius: 6px;
  background: var(--admin-surface-soft, #f8fafc);
  padding: 12px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
