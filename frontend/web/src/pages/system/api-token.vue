<script lang="ts" setup>
/**
 * API 令牌（/system/api-token，system 域）
 *
 * 为第三方脚本 / CI 签发的**长期凭据**：明文形如 `fbk_<prefix>_<secret>`，
 * 库里只存 Argon2 哈希，因此**明文仅在创建响应里出现一次**，关掉对话框就再也拿不到。
 * 令牌权限 = `scopes ∩ 你当前拥有的权限码` —— 你被降权时，令牌同步失效。
 *
 * 对齐 v3 `api_token/controller.py` 的 3 个端点：
 *   GET    /             令牌列表（普通用户只见自己的；管理员可见全部）
 *   POST   /             签发令牌（返回明文一次）
 *   DELETE /{token_id}   撤销（软删；非本人且非管理员返回 404，不泄露存在性）
 *
 * 权限：`module_system:api_token:{view,create,delete}`。
 */
import {computed, onMounted, ref} from 'vue'

import {apiTokenApi, type ApiTokenItem} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.apiToken.title',
  permission: 'module_system:api_token:view',
})

const {t} = useI18n()

const loading = ref(false)
const tokens = ref<ApiTokenItem[]>([])

/** 创建对话框 */
const createVisible = ref(false)
const creating = ref(false)
const form = ref<{ name: string; scopes: string; expiresInDays: number | null }>({
  name: '',
  scopes: '',
  expiresInDays: null,
})

/** 明文令牌对话框：只在创建成功后出现一次 */
const plaintextVisible = ref(false)
const plaintext = ref('')

const canCreate = computed(() => form.value.name.trim().length > 0)

/** 逗号/空白分隔 → 去重后的权限码数组 */
const parsedScopes = computed(() =>
  Array.from(
    new Set(
      form.value.scopes
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ),
)

async function load() {
  loading.value = true
  try {
    tokens.value = (await apiTokenApi.list()) ?? []
  } catch {
    // http 层已提示错误
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = {name: '', scopes: '', expiresInDays: null}
  createVisible.value = true
}

async function submitCreate() {
  if (!canCreate.value) {
    ElMessage.warning(t('admin.system.apiToken.nameRequired'))
    return
  }
  if (!parsedScopes.value.length) {
    ElMessage.warning(t('admin.system.apiToken.scopesRequired'))
    return
  }

  creating.value = true
  try {
    const created = await apiTokenApi.create({
      name: form.value.name.trim(),
      scopes: parsedScopes.value,
      ...(form.value.expiresInDays ? {expires_in_days: form.value.expiresInDays} : {}),
    })
    createVisible.value = false
    plaintext.value = created.token
    plaintextVisible.value = true
    await load()
  } catch {
    // 越权 scopes / 参数错误由 http 层提示
  } finally {
    creating.value = false
  }
}

async function revoke(item: ApiTokenItem) {
  try {
    await ElMessageBox.confirm(
      t('admin.system.apiToken.revokeConfirm', {name: item.name}),
      t('admin.system.apiToken.revoke'),
      {type: 'warning'},
    )
  } catch {
    return // 用户取消
  }
  try {
    await apiTokenApi.revoke(item.id)
    ElMessage.success(t('admin.system.apiToken.revoked'))
    await load()
  } catch {
    // 已提示
  }
}

async function copyPlaintext() {
  try {
    await navigator.clipboard.writeText(plaintext.value)
    ElMessage.success(t('admin.system.apiToken.copied'))
  } catch {
    ElMessage.warning(t('admin.system.apiToken.copyFailed'))
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4 p-4">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-lg font-semibold">{{ t('admin.system.apiToken.title') }}</h1>
        <p class="mt-1 max-w-2xl text-sm text-fg-subtle">{{ t('admin.system.apiToken.desc') }}</p>
      </div>
      <button
        class="rounded-md bg-primary px-3 py-1.5 text-sm text-white disabled:opacity-50"
        type="button"
        @click="openCreate"
      >
        {{ t('admin.system.apiToken.create') }}
      </button>
    </header>

    <div v-if="loading" class="py-8 text-center text-sm text-fg-subtle">
      {{ t('common.loading') }}
    </div>

    <div v-else-if="!tokens.length" class="rounded-lg bg-surface-soft py-10 text-center text-sm text-fg-subtle">
      {{ t('admin.system.apiToken.empty') }}
    </div>

    <table v-else class="w-full border-collapse text-sm">
      <thead>
      <tr class="border-b border-default text-left text-fg-subtle">
        <th class="py-2 pr-3">{{ t('admin.system.apiToken.colName') }}</th>
        <th class="py-2 pr-3">{{ t('admin.system.apiToken.colPrefix') }}</th>
        <th class="py-2 pr-3">{{ t('admin.system.apiToken.colScopes') }}</th>
        <th class="py-2 pr-3">{{ t('admin.system.apiToken.colExpires') }}</th>
        <th class="py-2 pr-3">{{ t('admin.system.apiToken.colLastUsed') }}</th>
        <th class="py-2">{{ t('admin.system.apiToken.colActions') }}</th>
      </tr>
      </thead>
      <tbody>
      <tr v-for="item in tokens" :key="item.id" class="border-b border-default/60">
        <td class="py-2 pr-3 font-medium">{{ item.name }}</td>
        <td class="py-2 pr-3 font-mono text-xs">{{ item.token_prefix ?? '—' }}</td>
        <td class="py-2 pr-3 text-xs">
          <span v-if="!item.scopes?.length" class="text-fg-subtle">—</span>
          <span v-else class="flex flex-wrap gap-1">
              <code v-for="scope in item.scopes" :key="scope" class="rounded bg-surface-soft px-1.5 py-0.5">
                {{ scope }}
              </code>
            </span>
        </td>
        <td class="py-2 pr-3">{{ item.expires_at ?? t('admin.system.apiToken.never') }}</td>
        <td class="py-2 pr-3">{{ item.last_used_at ?? t('admin.system.apiToken.never') }}</td>
        <td class="py-2">
          <button
            class="text-danger hover:underline"
            type="button"
            @click="revoke(item)"
          >
            {{ t('admin.system.apiToken.revoke') }}
          </button>
        </td>
      </tr>
      </tbody>
    </table>

    <!-- 创建：scopes 用文本输入，避免依赖额外端点；后端会校验是否为已有权限的子集 -->
    <div v-if="createVisible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="w-full max-w-lg rounded-lg bg-surface p-5">
        <h2 class="text-base font-semibold">{{ t('admin.system.apiToken.create') }}</h2>

        <label class="mt-4 block text-sm font-medium">{{ t('admin.system.apiToken.colName') }}</label>
        <input
          v-model="form.name"
          :placeholder="t('admin.system.apiToken.namePlaceholder')"
          class="mt-1 w-full rounded border border-default px-3 py-2 text-sm"
          type="text"
        >

        <label class="mt-4 block text-sm font-medium">{{ t('admin.system.apiToken.colScopes') }}</label>
        <textarea
          v-model="form.scopes"
          :placeholder="t('admin.system.apiToken.scopesPlaceholder')"
          class="mt-1 w-full rounded border border-default px-3 py-2 font-mono text-xs"
          rows="3"
        />
        <p class="mt-1 text-xs text-fg-subtle">{{ t('admin.system.apiToken.scopesHint') }}</p>

        <label class="mt-4 block text-sm font-medium">{{ t('admin.system.apiToken.expiresInDays') }}</label>
        <input
          v-model.number="form.expiresInDays"
          :placeholder="t('admin.system.apiToken.neverPlaceholder')"
          class="mt-1 w-full rounded border border-default px-3 py-2 text-sm"
          min="1"
          type="number"
        >

        <div class="mt-5 flex justify-end gap-2">
          <button class="rounded-md border border-default px-3 py-1.5 text-sm" type="button"
                  @click="createVisible = false">
            {{ t('common.cancel') }}
          </button>
          <button
            :disabled="creating"
            class="rounded-md bg-primary px-3 py-1.5 text-sm text-white disabled:opacity-50"
            type="button"
            @click="submitCreate"
          >
            {{ creating ? t('common.submitting') : t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 明文：只有这一次 -->
    <div v-if="plaintextVisible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="w-full max-w-lg rounded-lg bg-surface p-5">
        <h2 class="text-base font-semibold">{{ t('admin.system.apiToken.plaintextTitle') }}</h2>
        <p class="mt-2 text-sm text-danger">{{ t('admin.system.apiToken.plaintextWarning') }}</p>

        <div class="mt-3 flex items-center gap-2">
          <code class="flex-1 break-all rounded bg-surface-soft px-3 py-2 text-xs">{{ plaintext }}</code>
          <button class="rounded-md border border-default px-3 py-1.5 text-sm" type="button" @click="copyPlaintext">
            {{ t('admin.system.apiToken.copy') }}
          </button>
        </div>

        <div class="mt-5 flex justify-end">
          <button class="rounded-md bg-primary px-3 py-1.5 text-sm text-white" type="button"
                  @click="plaintextVisible = false">
            {{ t('common.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
