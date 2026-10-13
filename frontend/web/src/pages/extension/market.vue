<script lang="ts" setup>
/**
 * 插件市场（/extension/market，extension 域）
 *
 * 只读浏览远程插件目录 + **显式二次确认**的安装。市场地址由后端
 * `PLUGIN_MARKETPLACE_URL` 配置（未配置时后端明确报错，本页显示空状态提示）。
 *
 * 对齐 v3 `extension/plugin/controller.py` 的 4 个 market 端点：
 *   GET  /market/plugins            目录（keyword / category / 分页）
 *   GET  /market/plugins/{slug}     详情（含 readme / changelog / 版本列表）
 *   GET  /market/updates            按本机已装插件查更新（只回有更新的）
 *   POST /market/install            安装（必须 `confirm: true`，走校验和验证）
 *
 * 权限：浏览 `module_extension:plugin:view`；安装 `module_extension:plugin:install`。
 */
import {computed, onMounted, ref} from 'vue'

import {type MarketPluginItem, type MarketUpdateItem, pluginMarketApi} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.extension.market.title',
  permission: 'module_extension:plugin:view',
})

const {t} = useI18n()

const loading = ref(false)
const installing = ref(false)
const items = ref<MarketPluginItem[]>([])
const keyword = ref('')
const category = ref('')
const total = ref(0)
const marketUnavailable = ref(false)

const updates = ref<MarketUpdateItem[]>([])
const updatesLoading = ref(false)

const detailVisible = ref(false)
const detail = ref<MarketPluginItem | null>(null)

/** 详情里的版本列表：优先用详情返回的，缺失时退回单版本 */
const detailVersions = computed(() => {
  const versions = detail.value?.versions
  if (Array.isArray(versions) && versions.length) return versions
  const fallback = detail.value?.version
  return fallback ? [{version: fallback, sha256: detail.value?.sha256}] : []
})

async function load() {
  loading.value = true
  try {
    const data = await pluginMarketApi.list({
      keyword: keyword.value.trim(),
      category: category.value.trim(),
      page: 1,
      page_size: 50,
    })
    items.value = data?.items ?? []
    total.value = data?.total ?? items.value.length
    marketUnavailable.value = false
  } catch {
    // 未配置市场 / 市场不可达时，后端会给出明确错误，这里退回空状态
    items.value = []
    total.value = 0
    marketUnavailable.value = true
  } finally {
    loading.value = false
  }
}

async function openDetail(slug: string) {
  try {
    detail.value = await pluginMarketApi.detail(slug)
    detailVisible.value = true
  } catch {
    // 已提示
  }
}

async function checkUpdates() {
  updatesLoading.value = true
  try {
    updates.value = (await pluginMarketApi.updates())?.updates ?? []
    if (!updates.value.length) ElMessage.success(t('admin.extension.market.noUpdates'))
  } catch {
    // 已提示
  } finally {
    updatesLoading.value = false
  }
}

/** 安装：危险操作，先二次确认再带 `confirm: true` 提交 */
async function install(slug: string, version?: string, sha256?: string) {
  if (!version) {
    ElMessage.warning(t('admin.extension.market.versionRequired'))
    return
  }
  try {
    await ElMessageBox.confirm(
      t('admin.extension.market.installConfirm', {slug, version}),
      t('admin.extension.market.install'),
      {type: 'warning'},
    )
  } catch {
    return // 用户取消
  }

  installing.value = true
  try {
    await pluginMarketApi.install({slug, version, confirm: true, ...(sha256 ? {sha256} : {})})
    ElMessage.success(t('admin.extension.market.installed', {slug, version}))
    detailVisible.value = false
    updates.value = updates.value.filter((item) => item.slug !== slug)
  } catch {
    // 校验和不符 / 依赖不满足 / 未确认 等，http 层已提示
  } finally {
    installing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-5 p-4">
    <header>
      <h1 class="text-lg font-semibold">{{ t('admin.extension.market.title') }}</h1>
      <p class="mt-1 max-w-2xl text-sm text-fg-subtle">{{ t('admin.extension.market.desc') }}</p>
    </header>

    <!-- 搜索 -->
    <div class="flex flex-wrap items-end gap-2">
      <input
        v-model="keyword"
        :placeholder="t('admin.extension.market.keywordPlaceholder')"
        class="rounded border border-default px-3 py-1.5 text-sm"
        type="text"
        @keyup.enter="load"
      >
      <input
        v-model="category"
        :placeholder="t('admin.extension.market.categoryPlaceholder')"
        class="w-40 rounded border border-default px-3 py-1.5 text-sm"
        type="text"
        @keyup.enter="load"
      >
      <button class="rounded-md bg-primary px-3 py-1.5 text-sm text-white" type="button" @click="load">
        {{ t('admin.extension.market.search') }}
      </button>
      <button
        :disabled="updatesLoading"
        class="rounded-md border border-default px-3 py-1.5 text-sm disabled:opacity-50"
        type="button"
        @click="checkUpdates"
      >
        {{ updatesLoading ? t('common.loading') : t('admin.extension.market.checkUpdates') }}
      </button>
    </div>

    <!-- 可用更新 -->
    <section v-if="updates.length" class="rounded-lg border border-default p-3">
      <h2 class="text-sm font-semibold">{{ t('admin.extension.market.updatesTitle', {count: updates.length}) }}</h2>
      <ul class="mt-2 space-y-2">
        <li v-for="item in updates" :key="item.slug" class="flex items-center justify-between gap-3 text-sm">
          <span>
            <code>{{ item.slug }}</code>
            <span class="mx-1 text-fg-subtle">{{ item.current || '—' }} → {{ item.latest }}</span>
          </span>
          <button
            :disabled="installing"
            class="rounded-md bg-primary px-2.5 py-1 text-xs text-white disabled:opacity-50"
            type="button"
            @click="install(item.slug, item.latest, item.sha256)"
          >
            {{ t('admin.extension.market.update') }}
          </button>
        </li>
      </ul>
    </section>

    <!-- 目录 -->
    <div v-if="loading" class="py-8 text-center text-sm text-fg-subtle">{{ t('common.loading') }}</div>

    <div v-else-if="marketUnavailable" class="rounded-lg bg-surface-soft p-4 text-sm">
      <p class="font-medium">{{ t('admin.extension.market.unavailableTitle') }}</p>
      <p class="mt-1 text-fg-subtle">{{ t('admin.extension.market.unavailableHint') }}</p>
    </div>

    <div v-else-if="!items.length" class="rounded-lg bg-surface-soft py-10 text-center text-sm text-fg-subtle">
      {{ t('admin.extension.market.empty') }}
    </div>

    <ul v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <li v-for="item in items" :key="item.slug" class="rounded-lg border border-default p-3">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="truncate font-medium">{{ item.name || item.slug }}</p>
            <p class="mt-0.5 text-xs text-fg-subtle">
              {{ item.slug }} · {{ item.version || '—' }}
              <span v-if="item.category"> · {{ item.category }}</span>
            </p>
          </div>
          <span v-if="item.rating" class="shrink-0 text-xs text-fg-subtle">★ {{ item.rating }}</span>
        </div>

        <p class="mt-2 line-clamp-2 text-sm text-fg-subtle">{{ item.summary || item.description || '—' }}</p>

        <div class="mt-3 flex gap-2">
          <button
            class="rounded-md border border-default px-2.5 py-1 text-xs"
            type="button"
            @click="openDetail(item.slug)"
          >
            {{ t('admin.extension.market.detail') }}
          </button>
          <button
            :disabled="installing"
            class="rounded-md bg-primary px-2.5 py-1 text-xs text-white disabled:opacity-50"
            type="button"
            @click="install(item.slug, item.version, item.sha256)"
          >
            {{ t('admin.extension.market.install') }}
          </button>
        </div>
      </li>
    </ul>

    <!-- 详情 -->
    <div v-if="detailVisible && detail" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-surface p-5">
        <h2 class="text-base font-semibold">{{ detail.name || detail.slug }}</h2>
        <p class="mt-1 text-xs text-fg-subtle">
          {{ detail.slug }} · {{ detail.version || '—' }}
          <span v-if="detail.license"> · {{ detail.license }}</span>
        </p>

        <p class="mt-3 whitespace-pre-wrap text-sm">{{ detail.description || detail.summary || '—' }}</p>

        <section v-if="detail.changelog" class="mt-4">
          <h3 class="text-sm font-semibold">{{ t('admin.extension.market.changelog') }}</h3>
          <p class="mt-1 whitespace-pre-wrap text-sm text-fg-subtle">{{ detail.changelog }}</p>
        </section>

        <section v-if="detailVersions.length" class="mt-4">
          <h3 class="text-sm font-semibold">{{ t('admin.extension.market.versions') }}</h3>
          <ul class="mt-2 space-y-2">
            <li
              v-for="version in detailVersions"
              :key="version.version"
              class="flex items-center justify-between gap-3 text-sm"
            >
              <span>
                <code>{{ version.version }}</code>
                <span v-if="version.published_at" class="ml-2 text-xs text-fg-subtle">{{ version.published_at }}</span>
              </span>
              <button
                :disabled="installing"
                class="rounded-md bg-primary px-2.5 py-1 text-xs text-white disabled:opacity-50"
                type="button"
                @click="install(detail!.slug, version.version, version.sha256)"
              >
                {{ t('admin.extension.market.install') }}
              </button>
            </li>
          </ul>
        </section>

        <div class="mt-5 flex justify-end">
          <button class="rounded-md border border-default px-3 py-1.5 text-sm" type="button"
                  @click="detailVisible = false">
            {{ t('common.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
