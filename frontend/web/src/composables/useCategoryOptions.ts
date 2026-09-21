/**
 * 分类下拉选项（后端 `/content/category/tree` 全量拉取 + 扁平化）
 *
 * 后台多处（文章列表筛选、文章编辑表单）都需要"分类 id → 名称"的映射与选项列表，
 * 这里统一实现，避免每个页面各写一遍 flatten。
 *
 * 用法（在 setup 内调用，挂载后自动加载）：
 *   const {categories, nameOf} = useCategoryOptions()
 */

import {onMounted, ref} from 'vue'

import {categoryApi, type CategoryItem} from '@/api'

export function useCategoryOptions() {
  const categories = ref<CategoryItem[]>([])

  function flatten(nodes: CategoryItem[]): CategoryItem[] {
    const out: CategoryItem[] = []
    const walk = (list: CategoryItem[]): void => {
      for (const node of list) {
        out.push(node)
        if (node.children?.length) walk(node.children)
      }
    }
    walk(nodes)
    return out
  }

  async function load(): Promise<void> {
    try {
      categories.value = flatten(await categoryApi.tree())
    } catch {
      categories.value = []
    }
  }

  /** 名称映射：拿不到时回退成 id 字符串，避免界面出现空白 */
  function nameOf(id?: number | null): string {
    if (!id) return '-'
    return categories.value.find((item) => item.id === id)?.name ?? String(id)
  }

  onMounted(load)

  return {categories, load, nameOf}
}
