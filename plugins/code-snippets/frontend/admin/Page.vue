<script lang="ts" setup>
import {computed, onMounted, reactive, ref} from 'vue'

import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {pluginAction} from '@/utils/pluginAction'
import {useUserStore} from '@/store/modules/user'

/**
 * 代码片段（code-snippets 插件后台页）
 *
 * 对应 `plugins/code-snippets/frontend/admin/Page.tsx`：
 * 当前用户的片段列表 + 本地搜索 + 新建弹窗 + 复制嵌入标记 `[snippet:N]` + 删除。
 *
 * 与 astro 版的两点差异：
 *  1. 原实现额外请求 `/api/v2/users/me` 拿用户 ID；这里直接用 Pinia 的
 *     `useUserStore().userInfo`（后台本来就已加载），少一次请求。
 *  2. 原实现只实现了「新建」，编辑弹窗虽叫 `SnippetEditor` 但只用于创建；
 *     这里保持同样范围（活动 `update_snippet` 接口仍在后端，需要时可补编辑）。
 */
interface Snippet {
  id: number
  title: string
  code: string
  language: string
  description?: string | null
  tags?: string[] | null
  visibility?: string | null
  view_count?: number | null
  embed_count?: number | null
  created_at?: string | null
}

interface SnippetForm {
  title: string
  code: string
  language: string
  description: string
  tags: string
  visibility: 'public' | 'private' | 'unlisted'
}

const SUPPORTED_LANGUAGES = [
  'python', 'javascript', 'typescript', 'java', 'cpp', 'c',
  'html', 'css', 'sql', 'bash', 'json', 'yaml', 'markdown',
]

const userStore = useUserStore()
const userId = computed(() => userStore.userInfo?.id ?? 0)

const loading = ref(false)
const error = ref('')
const snippets = ref<Snippet[]>([])
const searchQuery = ref('')
const copiedId = ref<number | null>(null)

const editorOpen = ref(false)
const saving = ref(false)
const form = reactive<SnippetForm>(emptyForm())

function emptyForm(): SnippetForm {
  return {title: '', code: '', language: 'python', description: '', tags: '', visibility: 'public'}
}

const filtered = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return snippets.value
  return snippets.value.filter(
    (item) =>
      item.title?.toLowerCase().includes(query) ||
      item.tags?.some((tag) => tag.toLowerCase().includes(query)),
  )
})

async function loadSnippets(): Promise<void> {
  if (!userId.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await pluginAction<{ data?: Snippet[] } | Snippet[]>(
      'code-snippets',
      'get_user_snippets',
      {user_id: userId.value, limit: 100, offset: 0},
    )
    const payload = result.data
    snippets.value = Array.isArray(payload) ? payload : (payload?.data ?? [])
    if (!result.success) error.value = result.error || '加载失败'
  } finally {
    loading.value = false
  }
}

function openEditor(): void {
  Object.assign(form, emptyForm())
  editorOpen.value = true
}

async function saveSnippet(): Promise<void> {
  if (!form.title.trim() || !userId.value) return
  saving.value = true
  try {
    const result = await pluginAction('code-snippets', 'create_snippet', {
      title: form.title,
      code: form.code,
      language: form.language,
      description: form.description,
      visibility: form.visibility,
      tags: form.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      user_id: userId.value,
    })
    if (result.success) {
      ElMessage.success('片段已创建')
      editorOpen.value = false
      await loadSnippets()
    } else {
      ElMessage.error(result.error || '创建失败')
    }
  } finally {
    saving.value = false
  }
}

async function removeSnippet(snippet: Snippet): Promise<void> {
  await ElMessageBox.confirm(`确定删除片段「${snippet.title}」吗？`, '提示', {type: 'warning'})
  const result = await pluginAction('code-snippets', 'delete_snippet', {
    snippet_id: snippet.id,
    user_id: userId.value,
  })
  if (result.success) {
    ElMessage.success('已删除')
    await loadSnippets()
  } else {
    ElMessage.error(result.error || '删除失败')
  }
}

/** 复制嵌入标记，供文章正文引用 */
async function copyEmbed(snippet: Snippet): Promise<void> {
  try {
    await navigator.clipboard.writeText(`[snippet:${snippet.id}]`)
    copiedId.value = snippet.id
    window.setTimeout(() => {
      copiedId.value = null
    }, 2000)
    ElMessage.success('已复制嵌入标记')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

onMounted(loadSnippets)
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <el-input v-model="searchQuery" class="max-w-md" placeholder="搜索标题或标签…"/>
      <el-button class="ml-auto" type="primary" @click="openEditor">
        <Icon class="mr-1 h-4 w-4" name="plus"/>
        新建片段
      </el-button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 3" :key="i" class="h-20 w-full"/>
    </div>

    <EmptyState
      v-else-if="!filtered.length"
      :description="searchQuery ? '换个关键词试试' : '点右上角「新建片段」开始'"
      :title="searchQuery ? '没有匹配的片段' : '还没有代码片段'"
    />

    <div v-else class="space-y-3">
      <div
        v-for="snippet in filtered"
        :key="snippet.id"
        class="rounded-card border border-line bg-surface p-4 transition-colors hover:border-line-strong"
      >
        <div class="mb-2 flex items-center gap-3">
          <Icon class="h-4 w-4 text-primary" name="code"/>
          <h3 class="text-sm font-semibold text-fg">{{ snippet.title }}</h3>
          <span class="rounded-pill bg-primary-soft px-2 py-0.5 text-xs text-primary">{{ snippet.language }}</span>
          <span
            v-if="snippet.visibility && snippet.visibility !== 'public'"
            class="rounded-pill bg-surface-soft px-2 py-0.5 text-xs text-fg-muted"
          >{{ snippet.visibility }}</span>
        </div>

        <p v-if="snippet.description" class="mb-2 line-clamp-1 text-sm text-fg-muted">{{ snippet.description }}</p>

        <div v-if="snippet.tags?.length" class="mb-2 flex flex-wrap gap-1.5">
          <span
            v-for="tag in snippet.tags"
            :key="tag"
            class="rounded-pill bg-surface-soft px-2 py-0.5 text-xs text-fg-muted"
          >{{ tag }}</span>
        </div>

        <div class="flex items-center justify-between text-xs text-fg-subtle">
          <div class="flex items-center gap-3">
            <span class="flex items-center gap-1">
              <Icon class="h-3 w-3" name="eye"/>{{ snippet.view_count ?? 0 }}
            </span>
            <span class="flex items-center gap-1">
              <Icon class="h-3 w-3" name="code"/>{{ snippet.embed_count ?? 0 }}
            </span>
            <span>{{ formatDate(snippet.created_at) }}</span>
          </div>
          <div class="flex items-center gap-1">
            <el-button link title="复制嵌入标记 [snippet:N]" @click="copyEmbed(snippet)">
              <Icon
                :class="copiedId === snippet.id ? 'text-success' : 'text-fg-subtle'"
                :name="copiedId === snippet.id ? 'check' : 'copy'"
                class="h-4 w-4"
              />
            </el-button>
            <el-button link title="删除" type="danger" @click="removeSnippet(snippet)">
              <Icon class="h-4 w-4" name="trash-2"/>
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建片段 -->
    <el-dialog v-model="editorOpen" title="新建代码片段" width="720px">
      <div class="space-y-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-fg">标题</label>
          <el-input v-model="form.title" placeholder="片段标题"/>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-fg">语言</label>
            <el-select v-model="form.language" class="w-full">
              <el-option v-for="lang in SUPPORTED_LANGUAGES" :key="lang" :label="lang" :value="lang"/>
            </el-select>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium text-fg">可见性</label>
            <el-select v-model="form.visibility" class="w-full">
              <el-option label="公开" value="public"/>
              <el-option label="私有" value="private"/>
              <el-option label="不列出" value="unlisted"/>
            </el-select>
          </div>
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-fg">描述</label>
          <el-input v-model="form.description"/>
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-fg">标签（英文逗号分隔）</label>
          <el-input v-model="form.tags" placeholder="例如 python, tutorial, beginner"/>
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-fg">代码</label>
          <el-input v-model="form.code" :rows="12" type="textarea"/>
        </div>
      </div>

      <template #footer>
        <el-button @click="editorOpen = false">取消</el-button>
        <el-button :disabled="!form.title.trim()" :loading="saving" type="primary" @click="saveSnippet">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
