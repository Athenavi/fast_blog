<script lang="ts" setup>
/**
 * 投稿设置字段（工作台右侧抽屉的内容）
 *
 * 从原 `components/site/ArticleEditor.vue` 里剥出来的那一组表单字段。
 * 独立成组件有两个实打实的原因：
 *
 * 1. **它必须不依赖 Element Plus**。投稿页在 `layouts/default.vue` 下，而 EP 只在
 *    `layouts/admin.vue` 里动态注册；这些字段要塞进工作台的抽屉，抽屉外壳本身也是
 *    EP-free 的，所以这里一律用原生控件 + Tailwind 令牌。写成 `el-*` 会静默渲染不出
 *    （控制台只有一条 warn，界面上什么都没有）。
 * 2. 页面重构后正文区归 `DocWorkspace`，如果字段也留在页面里，一个文件里会同时
 *    有「外壳、正文、协作、历史、字段」五种东西，改哪一处都要通读全文。
 *
 * ## 表单对象与「改过了」这件事
 *
 * `form` 由页面持有（`useArticleForm` 返回的 reactive 对象）传进来，这里只写字段的值 ——
 * 嵌套写入不算改 prop 本身，比把九个字段拆成九个 `v-model` 诚实得多。
 *
 * 但**脏标记不能自己算**：`useArticleForm` 只在用户显式 `markDirty()` 之后才认为
 * 「有未保存改动」（加载完、恢复草稿后都会清掉），所以这里每处改动都要往外发一次
 * `change`。用 `watch(form, ...)` 深 watch 看着更省事，却会在**加载完成那一刻**
 * 误报成"有未保存修改" —— 于是每次打开文章都弹离开确认，比不提醒更糟。
 */
import type {ArticleContentFields} from '@/composables/useArticleForm'
import type {CategoryItem} from '@/api/public'

const props = defineProps<{
  form: ArticleContentFields
  /** 已展平的分类树（一级/二级用全角空格缩进表示层级，由调用方处理好） */
  categories: CategoryItem[]
}>()

const emit = defineEmits<{
  (e: 'change'): void
  (e: 'upload-cover'): void
}>()

const tagInput = ref('')

function addTag(): void {
  const value = tagInput.value.trim()
  if (!value) return
  if (!props.form.tags.includes(value)) {
    props.form.tags.push(value)
    emit('change')
  }
  tagInput.value = ''
}

function removeTag(tag: string): void {
  props.form.tags = props.form.tags.filter((item) => item !== tag)
  emit('change')
}
</script>

<template>
  <div class="space-y-5">
    <div>
      <label class="mb-1.5 block text-sm font-medium text-fg">
        {{ $t('myPosts.fieldSlug') }}
      </label>
      <Input v-model="form.slug" :placeholder="$t('myPosts.slugPlaceholder')" @update:model-value="emit('change')"/>
    </div>

    <div>
      <label class="mb-1.5 block text-sm font-medium text-fg">
        {{ $t('myPosts.fieldCategory') }}
      </label>
      <select
        v-model="form.category_id"
        class="h-9 w-full rounded-control border border-line bg-surface px-3 text-sm text-fg"
        @change="emit('change')"
      >
        <option :value="null">{{ $t('myPosts.uncategorized') }}</option>
        <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select>
    </div>

    <div>
      <label class="mb-1.5 block text-sm font-medium text-fg">
        {{ $t('myPosts.fieldExcerpt') }}
      </label>
      <textarea
        v-model="form.excerpt"
        class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        maxlength="255"
        :placeholder="$t('myPosts.excerptPlaceholder')"
        rows="3"
        @input="emit('change')"
      />
    </div>

    <div>
      <label class="mb-1.5 block text-sm font-medium text-fg">
        {{ $t('myPosts.fieldCover') }}
      </label>
      <div class="flex items-center gap-2">
        <Input
          v-model="form.cover_image"
          :placeholder="$t('myPosts.coverPlaceholder')"
          class="flex-1"
          @update:model-value="emit('change')"
        />
        <Button type="button" variant="outline" @click="emit('upload-cover')">
          {{ $t('myPosts.uploadFromLocal') }}
        </Button>
      </div>
      <img
        v-if="form.cover_image"
        :alt="$t('myPosts.coverPreviewAlt')"
        :src="form.cover_image"
        class="mt-2 h-32 w-full rounded-card object-cover"
        decoding="async"
      >
    </div>

    <div>
      <label class="mb-1.5 block text-sm font-medium text-fg">
        {{ $t('myPosts.fieldTags') }}
      </label>
      <div class="flex gap-2">
        <Input
          v-model="tagInput"
          :placeholder="$t('myPosts.tagPlaceholder')"
          class="flex-1"
          @keyup.enter.prevent="addTag"
        />
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
        <input v-model="form.is_vip_only" type="checkbox" @change="emit('change')">
        {{ $t('myPosts.vipOnly') }}
      </label>
      <div v-if="form.is_vip_only" class="mt-2 flex flex-wrap items-center gap-2">
        <span class="text-sm text-fg-muted">{{ $t('myPosts.requiredVipLevel') }}</span>
        <Input
          v-model="form.required_vip_level"
          class="w-20"
          inputmode="numeric"
          type="number"
          @update:model-value="emit('change')"
        />
        <span class="text-xs text-fg-subtle">{{ $t('myPosts.vipHint') }}</span>
      </div>
    </div>
  </div>
</template>
