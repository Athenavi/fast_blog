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

const {t} = useI18n()
const isEdit = computed(() => props.articleId !== undefined)

/** 正文字模式：富文本（Tiptap RichEditor）或源码（HTML / Markdown） */
const contentMode = ref<'rich' | 'source'>('rich')

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
  // VIP 可见性（内容属性，批次 16 起作者可自助设置；status 等管理字段仍不接受）
  is_vip_only: false,
  required_vip_level: 0,
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
      is_vip_only: Boolean(detail.is_vip_only),
      required_vip_level: detail.required_vip_level ?? 0,
    })
  } catch {
    error.value = t('myPosts.loadFailed')
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
      message.value = t('myPosts.coverUploaded')
    } catch {
      error.value = t('myPosts.coverUploadFailed')
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
    error.value = t('myPosts.titleRequired')
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
      is_vip_only: form.is_vip_only,
      required_vip_level: Number(form.required_vip_level) || 0,
    }

    const saved = isEdit.value
      ? await mobileApi.updateMyArticle(props.articleId as number, payload)
      : await mobileApi.createDraft(payload)

    message.value = isEdit.value ? t('myPosts.saved') : t('myPosts.draftCreated')
    emit('saved', saved.id)
  } catch {
    error.value = t('myPosts.saveFailed')
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
        <h1 class="text-2xl font-bold tracking-tight text-fg">
          {{ isEdit ? $t('myPosts.editTitle') : $t('myPosts.createTitle') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('myPosts.draftNotice') }}</p>
      </div>
      <NuxtLink to="/my/posts">
        <Button variant="outline">{{ $t('myPosts.backToList') }}</Button>
      </NuxtLink>
    </div>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton class="h-10 w-full"/>
      <Skeleton class="h-64 w-full"/>
    </div>

    <form v-else class="mt-6 space-y-4" @submit.prevent="save">
      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('myPosts.fieldTitle') }} <span
          class="text-danger">*</span></label>
        <Input v-model="form.title" :placeholder="$t('myPosts.titlePlaceholder')" maxlength="255"/>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('myPosts.fieldSlug') }}</label>
          <Input v-model="form.slug" :placeholder="$t('myPosts.slugPlaceholder')"/>
        </div>
        <div>
          <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('myPosts.fieldCategory') }}</label>
          <select
            v-model="form.category_id"
            class="h-9 w-full rounded-control border border-line bg-surface px-3 text-sm text-fg"
          >
            <option :value="undefined">{{ $t('myPosts.uncategorized') }}</option>
            <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('myPosts.fieldExcerpt') }}</label>
        <textarea
          v-model="form.excerpt"
          class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          maxlength="255"
          :placeholder="$t('myPosts.excerptPlaceholder')"
          rows="2"
        />
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('myPosts.fieldCover') }}</label>
        <div class="flex items-center gap-2">
          <Input v-model="form.cover_image" :placeholder="$t('myPosts.coverPlaceholder')" class="flex-1"/>
          <Button type="button" variant="outline" @click="pickCover">{{ $t('myPosts.uploadFromLocal') }}</Button>
        </div>
        <img v-if="form.cover_image" :alt="$t('myPosts.coverPreviewAlt')" :src="form.cover_image"
             class="mt-2 h-32 w-full rounded-card object-cover">
      </div>

      <div>
        <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('myPosts.fieldTags') }}</label>
        <div class="flex gap-2">
          <Input v-model="tagInput" :placeholder="$t('myPosts.tagPlaceholder')" class="flex-1"
                 @keyup.enter.prevent="addTag"/>
          <Button type="button" variant="outline" @click="addTag">{{ $t('myPosts.addTag') }}</Button>
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

      <!-- VIP 可见性：内容属性，作者可自助设置（发布仍走后台审核） -->
      <div class="rounded-card border border-line bg-surface-soft p-3">
        <label class="flex items-center gap-2 text-sm text-fg">
          <input v-model="form.is_vip_only" type="checkbox">
          {{ $t('myPosts.vipOnly') }}
        </label>
        <div v-if="form.is_vip_only" class="mt-2 flex flex-wrap items-center gap-2">
          <span class="text-sm text-fg-muted">{{ $t('myPosts.requiredVipLevel') }}</span>
          <Input v-model="form.required_vip_level" class="w-20" inputmode="numeric" type="number"/>
          <span class="text-xs text-fg-subtle">{{ $t('myPosts.vipHint') }}</span>
        </div>
      </div>

      <div>
        <div class="mb-1.5 flex items-center justify-between">
          <label class="block text-sm font-medium text-fg">{{ $t('myPosts.fieldContent') }}</label>
          <div class="flex items-center gap-1 rounded-control bg-surface-soft p-0.5 text-xs">
            <button
              :class="contentMode === 'rich' ? 'bg-surface text-fg shadow-sm' : 'text-fg-muted'"
              class="rounded-control px-2 py-1 transition-colors"
              type="button"
              @click="contentMode = 'rich'"
            >{{ $t('myPosts.modeRich') }}
            </button>
            <button
              :class="contentMode === 'source' ? 'bg-surface text-fg shadow-sm' : 'text-fg-muted'"
              class="rounded-control px-2 py-1 transition-colors"
              type="button"
              @click="contentMode = 'source'"
            >{{ $t('myPosts.modeSource') }}
            </button>
          </div>
        </div>

        <!-- 富文本（Tiptap） / 源码（HTML、Markdown）两种模式共用同一个 form.content -->
        <RichEditor v-if="contentMode === 'rich'" v-model="form.content"
                    :placeholder="$t('myPosts.contentPlaceholder')"/>
        <textarea
          v-else
          v-model="form.content"
          class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm leading-relaxed text-fg outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          :placeholder="$t('myPosts.sourcePlaceholder')"
          rows="16"
        />
      </div>

      <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>
      <p v-else-if="message" class="rounded-control bg-success-soft px-3 py-2 text-sm text-success">{{ message }}</p>

      <div class="flex items-center justify-end gap-2 pt-1">
        <NuxtLink to="/my/posts">
          <Button type="button" variant="outline">{{ $t('myPosts.cancel') }}</Button>
        </NuxtLink>
        <Button :disabled="saving" type="submit">
          <Icon v-if="saving" class="h-4 w-4 animate-spin" name="loader-circle"/>
          <Icon v-else class="h-4 w-4" name="save"/>
          {{ isEdit ? $t('myPosts.saveUpdate') : $t('myPosts.saveDraft') }}
        </Button>
      </div>
    </form>
  </div>
</template>
