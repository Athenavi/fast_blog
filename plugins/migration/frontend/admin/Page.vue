<script lang="ts" setup>
import {onMounted, reactive, ref, watch} from 'vue'

import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {pluginAction} from '@/utils/pluginAction'

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
  {key: 'tasks', label: '迁移任务', icon: 'refresh-cw'},
  {key: 'logs', label: '迁移日志', icon: 'clipboard-list'},
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
    if (!result.success) error.value = result.error || '加载失败'
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
      ElMessage.success('任务已创建')
      dialogOpen.value = false
      await loadCurrent()
    } else {
      ElMessage.error(result.error || '创建失败')
    }
  } finally {
    creating.value = false
  }
}

async function removeTask(task: MigrationTask): Promise<void> {
  await ElMessageBox.confirm(`确定删除迁移任务「${task.name || task.id}」吗？`, '提示', {type: 'warning'})
  const result = await pluginAction('migration', 'delete_task', {id: task.id})
  if (result.success) {
    ElMessage.success('已删除')
    await loadCurrent()
  } else {
    ElMessage.error(result.error || '删除失败')
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

      <el-button v-if="tab === 'tasks'" class="ml-auto" type="primary" @click="openCreate">新建任务</el-button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 5" :key="i" class="h-14 w-full"/>
    </div>

    <EmptyState
      v-else-if="tab === 'tasks' ? !tasks.length : !logs.length"
      description="新建任务或迁移完成后的记录会出现在这里"
      title="暂无数据"
    />

    <div v-else class="overflow-hidden rounded-card border border-line bg-surface">
      <table class="w-full text-sm">
        <thead class="bg-surface-soft text-xs uppercase text-fg-muted">
        <tr v-if="tab === 'tasks'">
          <th class="px-5 py-3 text-left font-semibold">名称</th>
          <th class="px-5 py-3 text-left font-semibold">平台</th>
          <th class="px-5 py-3 text-left font-semibold">进度</th>
          <th class="px-5 py-3 text-right font-semibold">操作</th>
        </tr>
        <tr v-else>
          <th class="px-5 py-3 text-left font-semibold">任务</th>
          <th class="px-5 py-3 text-left font-semibold">级别</th>
          <th class="px-5 py-3 text-right font-semibold">时间</th>
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
    <el-dialog v-model="dialogOpen" title="新建迁移任务" width="480px">
      <div class="space-y-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-fg">任务名称</label>
          <el-input v-model="form.name" placeholder="例如：WordPress 主站迁移"/>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-fg">源平台</label>
          <el-select v-model="form.source_platform" class="w-full">
            <el-option v-for="item in PLATFORMS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button :disabled="!form.name" :loading="creating" type="primary" @click="createTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
