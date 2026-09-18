<script lang="ts" setup>
import {computed, onMounted, ref} from 'vue'

import {cacheApi, type CacheStats} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

/**
 * 缓存管理（v3 `system/cache`）
 *
 * 对应原 astro 后台的 `admin/cache.astro` —— 属「无接口页面」清单里的一项，
 * React 原实现已随 `archive/` 删除。这里按新落的 v3 端点重写：
 * v2 时代这套能力散在 `performance/cache_management.py`（多级缓存）与
 * `admin/cache_management.py`（stats / purge / warmup），v3 模块是二者的并集。
 *
 * 页面构成：多级缓存统计（L1 memory / L2 redis / L3 file）+ 权限缓存统计 +
 * 清空全部缓存 + 批量预热 + 单键读写删。
 */
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '缓存管理',
  permission: 'module_system:cache:view',
})

const LEVEL_LABELS: Record<string, string> = {
  L1_memory: 'L1 · 内存',
  L2_redis: 'L2 · Redis',
  L3_file: 'L3 · 文件',
}

const loading = ref(false)
const stats = ref<CacheStats | null>(null)

const multiLevel = computed(() => stats.value?.multi_level ?? {})
const permissionStats = computed(() => stats.value?.permission ?? {})
const levelEntries = computed(() =>
  Object.entries(multiLevel.value.levels ?? {}) as Array<[string, Record<string, number | boolean>]>,
)

/** 权限缓存统计里可能是嵌套对象，展平成 `路径: 值` 便于展示 */
const permissionRows = computed(() =>
  Object.entries(permissionStats.value).map(([key, value]) => ({
    key,
    value: typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value),
  })),
)

async function load(): Promise<void> {
  loading.value = true
  try {
    stats.value = await cacheApi.stats()
  } finally {
    loading.value = false
  }
}

async function clearAll(): Promise<void> {
  await ElMessageBox.confirm(
    '将清空 L1 / L2 / L3 全部缓存。清空后短期内请求会全部回源，确定继续吗？',
    '危险操作',
    {type: 'warning', confirmButtonText: '确认清空'},
  )
  await cacheApi.clear()
  ElMessage.success('缓存已清空')
  await load()
}

// ── 单键操作 ──────────────────────────────────────────────
const itemKey = ref('')
const itemValue = ref('')
const itemTtl = ref<number | null>(null)
const readResult = ref('')

async function readItem(): Promise<void> {
  if (!itemKey.value) return
  try {
    const result = await cacheApi.getItem(itemKey.value)
    readResult.value = JSON.stringify(result?.value, null, 2)
  } catch {
    // `http` 层已提示错误（404 时后端返回「缓存键不存在」）
    readResult.value = ''
  }
}

async function writeItem(): Promise<void> {
  if (!itemKey.value) return
  let parsed: unknown = itemValue.value
  try {
    parsed = JSON.parse(itemValue.value)
  } catch {
    // 不是合法 JSON 就按字符串写入
  }
  await cacheApi.setItem(itemKey.value, parsed, itemTtl.value)
  ElMessage.success('已写入')
  await load()
}

async function removeItem(): Promise<void> {
  if (!itemKey.value) return
  await cacheApi.removeItem(itemKey.value)
  ElMessage.success('已删除')
  readResult.value = ''
  await load()
}

// ── 批量预热 ──────────────────────────────────────────────
const warmupOpen = ref(false)
const warmupText = ref('[\n  {"key": "example:key", "value": "示例值", "ttl": 60}\n]')

async function doWarmup(): Promise<void> {
  let parsed: unknown
  try {
    parsed = JSON.parse(warmupText.value)
  } catch {
    ElMessage.error('JSON 格式有误')
    return
  }
  if (!Array.isArray(parsed) || !parsed.length) {
    ElMessage.warning('请至少填一条预热数据')
    return
  }
  const result = await cacheApi.warmup(parsed as Array<{ key: string; value: unknown; ttl?: number | null }>)
  ElMessage.success(`已预热 ${result?.warmed ?? 0} 条`)
  warmupOpen.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <div class="cache-page">
    <!-- 顶部操作 -->
    <div class="mb-3 flex flex-wrap items-center gap-3">
      <el-button :loading="loading" @click="load">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        刷新
      </el-button>
      <el-button @click="warmupOpen = true">
        <Icon class="mr-1 h-3.5 w-3.5" name="upload"/>
        批量预热
      </el-button>
      <el-button class="ml-auto" type="danger" @click="clearAll">
        <Icon class="mr-1 h-3.5 w-3.5" name="trash-2"/>
        清空全部缓存
      </el-button>
    </div>

    <!-- 多级缓存概览 -->
    <el-card class="mb-4" shadow="never">
      <template #header>
        <span class="font-medium">多级缓存</span>
      </template>

      <p v-if="multiLevel.error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
        统计失败：{{ multiLevel.error }}
      </p>

      <div v-else class="mb-4 grid grid-cols-2 gap-4 md:grid-cols-3">
        <div class="stat">
          <p class="stat__label">总请求</p>
          <p class="stat__value">{{ multiLevel.total_requests ?? '—' }}</p>
        </div>
        <div class="stat">
          <p class="stat__label">总命中</p>
          <p class="stat__value">{{ multiLevel.total_hits ?? '—' }}</p>
        </div>
        <div class="stat">
          <p class="stat__label">命中率</p>
          <p class="stat__value">{{ multiLevel.hit_rate ?? '—' }}</p>
        </div>
      </div>

      <el-table :data="levelEntries" border size="small">
        <el-table-column label="层级" width="140">
          <template #default="{row}">{{ LEVEL_LABELS[row[0]] || row[0] }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{row}">
            <template v-if="row[1].enabled === undefined">—</template>
            <el-tag v-else :type="row[1].available === false ? 'warning' : 'success'" size="small">
              {{ row[1].available === false ? '不可用' : '启用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="命中" width="90">
          <template #default="{row}">{{ row[1].hits ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="未命中" width="90">
          <template #default="{row}">{{ row[1].misses ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="写入" width="90">
          <template #default="{row}">{{ row[1].sets ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="条目/错误">
          <template #default="{row}">
            <span v-if="row[1].size !== undefined">条目 {{ row[1].size }}</span>
            <span v-else-if="row[1].errors !== undefined">错误 {{ row[1].errors }}</span>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 权限缓存 -->
    <el-card class="mb-4" shadow="never">
      <template #header>
        <span class="font-medium">权限缓存</span>
      </template>
      <el-table v-if="permissionRows.length" :data="permissionRows" border size="small">
        <el-table-column label="项" min-width="180" prop="key"/>
        <el-table-column label="值" prop="value"/>
      </el-table>
      <p v-else class="text-sm text-fg-muted">暂无权限缓存统计</p>
    </el-card>

    <!-- 单键操作 -->
    <el-card shadow="never">
      <template #header>
        <span class="font-medium">单键读写</span>
        <span class="ml-2 text-xs text-fg-subtle">用于排查具体缓存内容</span>
      </template>

      <div class="flex flex-wrap items-center gap-3">
        <el-input v-model="itemKey" class="max-w-xs" placeholder="缓存键" @keyup.enter="readItem"/>
        <el-button @click="readItem">读取</el-button>
        <el-button type="danger" @click="removeItem">删除</el-button>
      </div>

      <pre v-if="readResult" class="mt-3 overflow-auto rounded-control bg-surface-soft p-3 text-xs">{{
          readResult
        }}</pre>

      <div class="mt-4 flex flex-wrap items-end gap-3">
        <el-input
          v-model="itemValue"
          class="min-w-[240px] flex-1"
          placeholder="要写入的值（JSON 或纯字符串）"
        />
        <el-input v-model.number="itemTtl" class="w-32" placeholder="TTL 秒（可空）"/>
        <el-button type="primary" @click="writeItem">写入</el-button>
      </div>
    </el-card>

    <!-- 预热弹窗 -->
    <el-dialog v-model="warmupOpen" title="批量预热缓存" width="620px">
      <p class="mb-2 text-sm text-fg-muted">
        填一个 JSON 数组，每项形如 <code>{"key": "...", "value": ..., "ttl": 60}</code>（ttl 可省略）。
      </p>
      <el-input v-model="warmupText" :rows="10" type="textarea"/>
      <template #footer>
        <el-button @click="warmupOpen = false">取消</el-button>
        <el-button type="primary" @click="doWarmup">开始预热</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cache-page {
  padding: 16px;
}

.stat {
  padding: 12px 14px;
  background-color: var(--color-surface-soft);
  border-radius: var(--radius-control);
}

.stat__label {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--color-fg-muted);
}

.stat__value {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg);
}
</style>
