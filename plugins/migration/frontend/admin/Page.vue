<script lang="ts" setup>
import {onMounted, reactive, ref, watch} from 'vue'

import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {pluginAction} from '@/utils/pluginAction'

const {t} = useI18n()

/**
 * 迁移管理（migration 插件后台页）
 *
 * 对应 `plugins/migration/frontend/admin/Page.tsx`：
 * 「迁移任务 / 迁移日志」两个页签；任务页支持新建（名称 + 源平台）与删除。
 */
interface MigrationTask {
  id: number
  name?: string | null
  source_platform?: string | null
  progress?: number | null
}

interface MigrationLog {
  id: number
  task_id?: number | null
  task_name?: string | null
  level?: string | null
  created_at?: string | null
}

interface ListResult<T> {
  items: T[]
  total: number
}

type TabKey = 'tasks' | 'logs'

const TABS: Array<{ key: TabKey; label: string; icon: string }> = [
  {key: 'tasks', label: t('admin.pluginPages.migration.tabs.tasks'), icon: 'refresh-cw'},
  {key: 'logs', label: t('admin.pluginPages.migration.tabs.logs'), icon: 'clipboard-list'},
]

const PLATFORMS = [
  {value: 'wordpress', label: 'WordPress'},
  {value: 'halo', label: 'Halo'},
  {value: 'ghost', label: 'Ghost'},
]

const PER_PAGE = 20

const tab = ref<TabKey>('tasks')
const page = ref(1)
const loading = ref(false)
const error = ref('')

const tasks = ref<MigrationTask[]>([])
const logs = ref<MigrationLog[]>([])
const total = ref(0)

const dialogOpen = ref(false)
const creating = ref(false)
const form = reactive({name: '', source_platform: 'wordpress'})

async function loadCurrent(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const action = tab.value === 'tasks' ? 'list_tasks' : 'list_logs'
    const result = await pluginAction<ListResult<MigrationTask | MigrationLog>>('migration', action, {
      page: page.value,
      per_page: PER_PAGE,
    })
    if (tab.value === 'tasks') tasks.value = (result.data?.items ?? []) as MigrationTask[]
    else logs.value = (result.data?.items ?? []) as MigrationLog[]
    total.value = result.data?.total ?? 0
    if (!result.success) error.value = result.error || t('admin.pluginPages.common.loadFailed')
  } finally {
    loading.value = false
  }
}

function switchTab(key: TabKey): void {
  tab.value = key
  page.value = 1
}

function openCreate(): void {
  form.name = ''
  form.source_platform = 'wordpress'
  dialogOpen.value = true
}

async function createTask(): Promise<void> {
  if (!form.name) return
  creating.value = true
  try {
    const result = await pluginAction('migration', 'create_task', {
      name: form.name,
      source_platform: form.source_platform,
    })
    if (result.success) {
      ElMessage.success(t('admin.pluginPages.migration.taskCreated'))
      dialogOpen.value = false
      await loadCurrent()
    } else {
      ElMessage.error(result.error || t('admin.pluginPages.common.createFailed'))
    }
  } finally {
    creating.value = false
  }
}

async function removeTask(task: MigrationTask): Promise<void> {
  await ElMessageBox.confirm(t('admin.pluginPages.common.confirmDeleteNamed', {name: task.name || task.id}), t('admin.common.notice'), {type: 'warning'})
  const result = await pluginAction('migration', 'delete_task', {id: task.id})
  if (result.success) {
    ElMessage.success(t('admin.common.deleted'))
    await loadCurrent()
  } else {
    ElMessage.error(result.error || t('admin.pluginPages.common.deleteFailed'))
  }
}

function levelClass(level?: string | null): string {
  if (level === 'error') return 'bg-danger-soft text-danger'
  if (level === 'warning') return 'bg-warning-soft text-warning'
  return 'bg-surface-soft text-fg-muted'
}

function formatTime(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

watch(page, loadCurrent)
onMounted(loadCurrent)
</script>

<template>
  <div class="p-4">
    <div class="mb-6 flex flex-wrap items-center gap-2">
      <button
        v-for="item in TABS"
        :key="item.key"
        :class="
          tab === item.key
            ? 'bg-primary text-primary-fg'
            : 'border border-line bg-surface text-fg-muted hover:bg-surface-soft'
        "
        class="flex items-center gap-1.5 rounded-control px-4 py-2 text-sm font-medium transition-colors"
        type="button"
        @click="switchTab(item.key)"
      >
        <Icon :name="item.icon" class="h-4 w-4"/>
        {{ item.label }}
      </button>

      <el-button v-if="tab === 'tasks'" class="ml-auto" type="primary" @click="openCreate">
        {{ t('admin.pluginPages.migration.createTask') }}
      </el-button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 5" :key="i" class="h-14 w-full"/>
    </div>

    <EmptyState
      v-else-if="tab === 'tasks' ? !tasks.length : !logs.length"
      :description="t('admin.pluginPages.migration.emptyDesc')"
      :title="t('admin.common.empty')"
    />

    <div v-else class="overflow-hidden rounded-card border border-line bg-surface">
      <table class="w-full text-sm">
        <thead class="bg-surface-soft text-xs uppercase text-fg-muted">
        <tr v-if="tab === 'tasks'">
          <th class="px-5 py-3 text-left font-semibold">{{ t('admin.common.name') }}</th>
          <th class="px-5 py-3 text-left font-semibold">{{ t('admin.pluginPages.migration.platform') }}</th>
          <th class="px-5 py-3 text-left font-semibold">{{ t('admin.pluginPages.migration.progress') }}</th>
          <th class="px-5 py-3 text-right font-semibold">{{ t('admin.common.actions') }}</th>
        </tr>
        <tr v-else>
          <th class="px-5 py-3 text-left font-semibold">{{ t('admin.pluginPages.migration.task') }}</th>
          <th class="px-5 py-3 text-left font-semibold">{{ t('admin.pluginPages.migration.level') }}</th>
          <th class="px-5 py-3 text-right font-semibold">{{ t('admin.pluginPages.common.time') }}</th>
        </tr>
        </thead>

        <tbody class="divide-y divide-line">
        <template v-if="tab === 'tasks'">
          <tr v-for="item in tasks" :key="item.id" class="hover:bg-surface-soft">
            <td class="px-5 py-4 font-medium text-fg">{{ item.name || `#${item.id}` }}</td>
            <td class="px-5 py-4 text-fg-muted">{{ item.source_platform || '—' }}</td>
            <td class="px-5 py-4">
              <div class="flex items-center gap-2">
                <div class="h-2 flex-1 overflow-hidden rounded-pill bg-surface-soft">
                  <div
                    :style="{width: `${item.progress || 0}%`}"
                    class="h-full rounded-pill bg-primary transition-all"
                  />
                </div>
                <span class="text-xs text-fg-muted">{{ item.progress || 0 }}%</span>
              </div>
            </td>
            <td class="px-5 py-4 text-right">
              <el-button link type="danger" @click="removeTask(item)">
                <Icon class="h-4 w-4" name="trash-2"/>
              </el-button>
            </td>
          </tr>
        </template>

        <template v-else>
          <tr v-for="item in logs" :key="item.id" class="hover:bg-surface-soft">
            <td class="px-5 py-4 text-fg">{{ item.task_name || `#${item.task_id}` }}</td>
            <td class="px-5 py-4">
                <span :class="levelClass(item.level)" class="rounded-pill px-2 py-0.5 text-xs">
                  {{ item.level || 'info' }}
                </span>
            </td>
            <td class="px-5 py-4 text-right text-fg-muted">{{ formatTime(item.created_at) }}</td>
          </tr>
        </template>
        </tbody>
      </table>
    </div>

    <el-pagination
      v-if="total > PER_PAGE"
      v-model:current-page="page"
      :page-size="PER_PAGE"
      :total="total"
      class="mt-3 justify-end"
      layout="total, prev, pager, next"
    />

    <!-- 新建任务 -->
    <el-dialog v-model="dialogOpen" :title="t('admin.pluginPages.migration.createTitle')" width="480px">
      <div class="space-y-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-fg">{{ t('admin.pluginPages.migration.taskName') }}</label>
          <el-input v-model="form.name" :placeholder="t('admin.pluginPages.migration.namePlaceholder')"/>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-fg">{{
              t('admin.pluginPages.migration.sourcePlatform')
            }}</label>
          <el-select v-model="form.source_platform" class="w-full">
            <el-option v-for="item in PLATFORMS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogOpen = false">{{ t('admin.common.cancel') }}</el-button>
        <el-button :disabled="!form.name" :loading="creating" type="primary" @click="createTask">
          {{ t('admin.common.create') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
