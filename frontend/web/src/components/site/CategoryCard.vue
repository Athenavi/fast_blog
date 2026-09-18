<script lang="ts" setup>
/** 分类卡片：分类总览页使用，递归展示子分类 */
import {Folder} from '@lucide/vue'

import type {CategoryItem} from '@/types/content'

const props = defineProps<{ category: CategoryItem }>()
</script>

<template>
  <NuxtLink :to="`/category/${props.category.id}`" class="group block">
    <Card class="h-full transition-shadow group-hover:shadow-md">
      <CardHeader class="pb-3">
        <CardTitle class="flex items-center gap-2 text-base">
          <Folder class="h-4 w-4 text-slate-400"/>
          {{ props.category.name }}
        </CardTitle>
        <CardDescription v-if="props.category.description">{{ props.category.description }}</CardDescription>
      </CardHeader>
      <CardContent>
        <p class="text-xs text-slate-400">{{ props.category.article_count ?? 0 }} 篇文章</p>
        <div v-if="props.category.children?.length" class="mt-3 flex flex-wrap gap-1.5">
          <Badge v-for="child in props.category.children" :key="child.id" variant="secondary">{{ child.name }}</Badge>
        </div>
      </CardContent>
    </Card>
  </NuxtLink>
</template>
