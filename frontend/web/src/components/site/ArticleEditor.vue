<script lang="ts" setup>
/**
 * 投稿编辑器（`/my/posts/create` 与 `/my/posts/edit/[id]` 共用）
 *
 * 说明：请求体**不含** `status` / `is_featured` 等管理字段——后端 schema 也不接受，
 * 投稿一律存为草稿，发布由管理员在后台执行。因此界面上只提示"保存草稿"。
 */

import {categoryApi, type CategoryItem, mobileApi} from '@/api'

const props = defineProps<{ articleId?: number }>()
const emit = defineEmits<{ (e: 'saved', id: number): void }>()

const isEdit = computed(() => props.articleId !== undefined)

const loading = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')
const categories = ref<CategoryItem[]>([])

const form = reactive({
  title: '',
  slug: '',
  excerpt: '',
  cover_image: '',
  category_id: undefined as number | undefined,
  tags: [] as string[],
  content: '',
})

const tagInput = ref('')

async function loadCategories(): Promise<void> {
  try {
    const tree = await categoryApi.publicTree()
    // 展平为一级 + 二级，便于下拉选择
    const flat: CategoryItem[] = []
    const walk = (items: CategoryItem[], depth = 0) => {
      for (const item of items) {
        flat.push({...item, name: `${'　'.repeat(depth)}${item.name}`})
        if (item.children?.length) walk(item.children, depth + 1)
      }
    }
    walk(tree)
    categories.value = flat
  } catch {
    categories.value = []
  }
}

async function loadArticle(): Promise<void> {
  if (!isEdit.value) return
  loading.value = true
  try {
    const detail = await mobileApi.myArticleDetail(props.articleId as number)
    Object.assign(form, {
      title: detail.title ?? '',
      slug: detail.slug ?? '',
      excerpt: detail.excerpt ?? '',
      cover_image: detail.cover_image ?? '',
      category_id: detail.category_id ?? undefined,
      tags: [...(detail.tags ?? [])],
      content: detail.content ?? '',
    })
  } catch {
    error.value = '加载文章失败，可能不存在或不属于你'
  } finally {
    loading.value = false
  }
}

function addTag(): void {
  const value = tagInput.value.trim()
  if (!value) return
  if (!form.tags.includes(value)) form.tags.push(value)
  tagInput.value = ''
}

function removeTag(tag: string): void {
  form.tags = form.tags.filter((item) => item !== tag)
}

/** 用媒体库的文件作为封面 */
async function pickCover(): Promise<void> {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    saving.value = true
    try {
      const uploaded = await mobileApi.mediaUpload(file)
      form.cover_image = uploaded.file_url ?? ''
      message.value = '封面已上传'
    } catch {
      error.value = '封面上传失败'
    } finally {
      saving.value = false
    }
  }
  input.click()
}

async function save(): Promise<void> {
  error.value = ''
  message.value = ''

  const title = form.title.trim()
  if (!title) {
    error.value = '请填写标题'
    return
  }

  saving.value = true
  try {
    const payload = {
      title,
      slug: form.slug.trim() || undefined,
      excerpt: form.excerpt.trim() || undefined,
      cover_image: form.cover_image.trim() || undefined,
      category_id: form.category_id ?? null,
      tags: form.tags,
      content: form.content,
    }

    const saved = isEdit.value
      ? await mobileApi.updateMyArticle(props.articleId as number, payload)
      : await mobileApi.createDraft(payload)

    message.value = isEdit.value ? '已保存' : '草稿已创建'
    emit('saved', saved.id)
  } catch {
    error.value = '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadArticle()])
})
</script>

<template>
  <div class="mx-auto max-w-read px-4 py-10">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ isEdit ? '编辑文章' : '写文章' }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">
          投稿将以<strong class="font-medium text-fg">草稿</strong>保存，发布由管理员审核后执行。
        </p>
      </div>
      <NuxtLink to="/my/posts">
        <Button variant="outline">返回列表</Button>
      </NuxtLink>
    </div>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton class="h-10 w-full"/>
      <Skeleton class="h-64 w-full"/>
    </div>

    <form v-else class="mt-6 space-y-4" @submit.prevent="save">
      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">标题 <span class="text-danger">*</span></label>
        <Input v-model="form.title" maxlength="255" placeholder="文章标题"/>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="mb-1.5 block text-sm font-medium text-fg">URL 别名</label>
          <Input v-model="form.slug" placeholder="留空由后端生成"/>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-medium text-fg">分类</label>
          <select
            v-model="form.category_id"
            class="h-9 w-full rounded-control border border-line bg-surface px-3 text-sm text-fg"
          >
            <option :value="undefined">未分类</option>
            <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">摘要</label>
        <textarea
          v-model="form.excerpt"
          class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          maxlength="255"
          placeholder="一两句话概括内容，用于列表与搜索展示"
          rows="2"
        />
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">封面</label>
        <div class="flex items-center gap-2">
          <Input v-model="form.cover_image" class="flex-1" placeholder="封面图地址"/>
          <Button type="button" variant="outline" @click="pickCover">从本地上传</Button>
        </div>
        <img v-if="form.cover_image" :src="form.cover_image" alt="封面预览"
             class="mt-2 h-32 w-full rounded-card object-cover">
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">标签</label>
        <div class="flex gap-2">
          <Input v-model="tagInput" class="flex-1" placeholder="输入后回车添加" @keyup.enter.prevent="addTag"/>
          <Button type="button" variant="outline" @click="addTag">添加</Button>
        </div>
        <div v-if="form.tags.length" class="mt-2 flex flex-wrap gap-1.5">
          <button
            v-for="tag in form.tags"
            :key="tag"
            class="inline-flex items-center gap-1 rounded-pill bg-surface-soft px-2.5 py-0.5 text-xs text-fg-muted transition-colors hover:text-danger"
            type="button"
            @click="removeTag(tag)"
          >
            {{ tag }} ×
          </button>
        </div>
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">正文</label>
        <textarea
          v-model="form.content"
          class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm leading-relaxed text-fg outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          placeholder="支持 HTML / Markdown 源码"
          rows="16"
        />
      </div>

      <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>
      <p v-else-if="message" class="rounded-control bg-success-soft px-3 py-2 text-sm text-success">{{ message }}</p>

      <div class="flex items-center justify-end gap-2 pt-1">
        <NuxtLink to="/my/posts">
          <Button type="button" variant="outline">取消</Button>
        </NuxtLink>
        <Button :disabled="saving" type="submit">
          <Icon v-if="saving" class="h-4 w-4 animate-spin" name="loader-circle"/>
          <Icon v-else class="h-4 w-4" name="save"/>
          {{ isEdit ? '保存修改' : '保存草稿' }}
        </Button>
      </div>
    </form>
  </div>
</template>
