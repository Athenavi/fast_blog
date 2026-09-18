<script lang="ts" setup>
/**
 * 文章列表区块：列表页 / 分类页 / 搜索页复用
 *
 * 数据由页面负责获取（各页查询参数不同），这里只负责呈现、骨架屏与分页。
 */
import type {ArticleItem} from '@/types/content'

const props = withDefaults(
  defineProps<{
    articles: ArticleItem[]
    page: number
    pages: number
    loading?: boolean
    emptyTitle?: string
    emptyDescription?: string
  }>(),
  {loading: false, emptyTitle: '暂无文章', emptyDescription: ''},
)

const emit = defineEmits<{ (e: 'change', page: number): void }>()
</script>

<template>
  <div>
    <div v-if="props.loading" class="grid gap-10 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 6" :key="i" class="space-y-2.5">
        <Skeleton class="h-40 w-full"/>
        <Skeleton class="h-5 w-3/4"/>
        <Skeleton class="h-4 w-full"/>
      </div>
    </div>

    <div v-else-if="props.articles.length" class="grid gap-10 sm:grid-cols-2 lg:grid-cols-3">
      <ArticleCard v-for="article in props.articles" :key="article.id" :article="article"/>
    </div>

    <EmptyState v-else :description="props.emptyDescription" :title="props.emptyTitle"/>

    <PaginationBar
      v-if="!props.loading"
      :page="props.page"
      :pages="props.pages"
      @change="emit('change', $event)"
    />

    <ListLoadingFooter :has-loaded-all="false" :is-loading="props.loading"/>
  </div>
</template>
