<script lang="ts" setup>
/**
 * 社交账号绑定管理（T5-11 批次 3；OAuth 模块接线：追加「我的第三方授权」）
 *
 * 对齐 v3 `/system/social`：OAuthAccount 绑定档案列表 + 解绑。
 * 令牌字段脱敏（响应只有 has_token 布尔位）；OAuth 登录流程本身在 auth 体系。
 *
 * 追加部分对齐 v3 `/system/oauth`（模块端点均为公开或仅认证、只操作本人数据）：
 *   提供方配置状态 / 本人绑定列表 / 生成授权跳转信息 / 解绑本人。
 * 第三方重定向入口（`GET|POST /system/oauth/{provider}/callback`）由后端承接，
 * 本页只做「展示 + 发起」，不伪造完整回调流程。
 */
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, ref} from 'vue'

import {
  oauthApi,
  type OAuthAuthorizeUrl,
  type OAuthBindingItem,
  type OAuthProviderItem,
  type SocialAccountItem,
  socialApi,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.social.title',
  permission: 'module_system:social:view',
})

const {t} = useI18n()

/** 标签页：bindings = 既有管理端绑定档案；mine = 追加的本人第三方授权 */
const activeTab = ref<'bindings' | 'mine'>('bindings')

interface SocialQueryForm extends PageQuery {
  user_id?: number
  provider?: string
}

const list = useAdminList<SocialAccountItem, SocialQueryForm>({
  fetcher: (params) => socialApi.list(params),
  defaultQuery: {provider: ''},
  syncUrl: true,
})

async function onUnbind(row: SocialAccountItem) {
  await ElMessageBox.confirm(t('admin.system.social.unbindConfirm'), t('admin.common.notice'), {type: 'warning'})
  await socialApi.unbind(row.id)
  ElMessage.success(t('admin.common.delete'))
  await list.reload()
}

// ======================================================================
// 追加：本人第三方授权（/api/v3/system/oauth）
//   - 端点均为「公开」或「仅认证且只操作本人数据」，无管理权限码
//   - 因此这里不复用 useAdminList（后端返回数组、非分页）
// ======================================================================

/** 提供方清单 + 是否已在系统设置里配置凭据 */
const providers = ref<OAuthProviderItem[]>([])
const providersLoading = ref(false)
const providersFailed = ref(false)

/** 本人已绑定的第三方账号（脱敏） */
const bindings = ref<OAuthBindingItem[]>([])
const bindingsLoading = ref(false)
const bindingsFailed = ref(false)

/** 是否已加载过：首次切到该标签页时加载一次，之后靠「刷新」按钮 */
const oauthLoaded = ref(false)

/** 已生成的授权跳转信息，按提供方 key 保留最近一次结果 */
const authorizeInfo = ref<Record<string, OAuthAuthorizeUrl>>({})
/** 正在生成授权链接的提供方 key */
const authorizingKey = ref('')

/** provider key → 后端返回的展示名（未收录时回退显示 key 本身，不臆造名称） */
const providerNames = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const item of providers.value) {
    map[item.key] = item.name
  }
  return map
})

function providerLabel(key?: string | null): string {
  if (!key) return ''
  return providerNames.value[key] ?? key
}

/** 拉取提供方清单（含 configured 真实状态） */
async function loadProviders(): Promise<void> {
  providersLoading.value = true
  providersFailed.value = false
  try {
    providers.value = await oauthApi.providers()
  } catch {
    // 失败提示由 request.ts 拦截器统一给出，这里只落状态
    providersFailed.value = true
  } finally {
    providersLoading.value = false
  }
}

/** 拉取本人绑定列表 */
async function loadBindings(): Promise<void> {
  bindingsLoading.value = true
  bindingsFailed.value = false
  try {
    bindings.value = await oauthApi.bindings()
  } catch {
    bindingsFailed.value = true
  } finally {
    bindingsLoading.value = false
  }
}

/** 切换标签页：首次进入「我的第三方授权」时加载数据 */
function onTabChange(name: string | number): void {
  if (name !== 'mine' || oauthLoaded.value) return
  oauthLoaded.value = true
  void loadProviders()
  void loadBindings()
}

/**
 * 生成授权跳转信息
 *
 * 未配置凭据或缺少 redirect_uri 时后端返回 400（绝不返回伪造地址），
 * 错误消息由拦截器提示；此处不额外美化。
 */
async function onAuthorize(provider: OAuthProviderItem): Promise<void> {
  authorizingKey.value = provider.key
  try {
    const info = await oauthApi.authorizeUrl(provider.key)
    authorizeInfo.value = {...authorizeInfo.value, [provider.key]: info}
    ElMessage.success(t('admin.system.social.oauth.authorizeReady'))
  } catch {
    /* 拦截器已提示 */
  } finally {
    authorizingKey.value = ''
  }
}

/** 解绑本人该提供方的绑定（仅影响本人绑定记录，不影响登录态） */
async function onUnbindSelf(row: OAuthBindingItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.system.social.oauth.unbindSelfConfirm'),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await oauthApi.unbind(String(row.provider ?? ''))
  ElMessage.success(t('admin.system.social.oauth.unbound'))
  await loadBindings()
}

/** 复制文本；非安全上下文下 clipboard 不可用时如实提示手动复制 */
async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('admin.system.social.oauth.copied'))
  } catch {
    ElMessage.warning(t('admin.system.social.oauth.copyFailed'))
  }
}

/** 打开第三方授权页（授权完成后由第三方重定向到后端回调端点） */
function openAuthorizeUrl(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.social.desc')" :title="$t('admin.system.social.title')">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 既有：管理端绑定档案（需 module_system:social:view / :delete） -->
      <el-tab-pane :label="$t('admin.system.social.oauth.tabBindings')" name="bindings">
        <AdminListShell
          :empty-desc="list.hasFilters.value ? $t('admin.system.social.emptyFiltered') : $t('admin.system.social.emptyDesc')"
          :empty-title="$t('admin.system.social.emptyTitle')"
          :failed="list.failed.value"
          :loading="list.loading.value"
          :page="list.page.value"
          :page-size="list.pageSize.value"
          :rows="list.rows.value"
          :selectable="false"
          :total="list.total.value"
          @refresh="list.reload"
          @reset="list.reset"
          @search="list.search"
          @page-change="list.onPageChange"
          @size-change="list.onSizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.social.userId')">
              <el-input-number
                v-model="list.query.user_id"
                :min="1"
                controls-position="right"
                style="width: 140px"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.social.provider')">
              <el-input
                v-model="list.query.provider"
                :placeholder="$t('admin.system.social.providerPlaceholder')"
                clearable
                style="width: 160px"
                @keyup.enter="list.search()"
              />
            </el-form-item>
          </template>

          <el-table-column label="ID" prop="id" width="80"/>
          <el-table-column :label="$t('admin.system.social.userId')" prop="user_id" width="100"/>
          <el-table-column :label="$t('admin.system.social.provider')" prop="provider" width="130"/>
          <el-table-column :label="$t('admin.system.social.providerUserId')" min-width="160" prop="provider_user_id"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.social.hasToken')" width="100">
            <template #default="{ row }">
              <el-tag :type="(row as SocialAccountItem).has_token ? 'success' : 'info'" size="small">
                {{ (row as SocialAccountItem).has_token ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.social.tokenExpiresAt')" min-width="170" prop="token_expires_at"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="110">
            <template #default="{ row }">
              <el-button
                v-auth="'module_system:social:delete'"
                link
                type="danger"
                @click="onUnbind(row as SocialAccountItem)"
              >
                {{ $t('admin.system.social.unbind') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- 追加：本人第三方授权（查看配置状态 / 生成授权链接 / 查看与解除本人绑定） -->
      <el-tab-pane :label="$t('admin.system.social.oauth.tabMine')" name="mine">
        <el-alert
          :closable="false"
          :title="$t('admin.system.social.oauth.mineDesc')"
          class="mb-4"
          show-icon
          type="info"
        />

        <!-- 提供方与配置状态 -->
        <el-card class="mb-4" shadow="never">
          <template #header>
            <div class="flex items-center justify-between">
              <span>{{ $t('admin.system.social.oauth.providersTitle') }}</span>
              <el-button :loading="providersLoading" link size="small" @click="loadProviders">
                {{ $t('admin.common.refresh') }}
              </el-button>
            </div>
          </template>

          <el-alert
            v-if="providersFailed"
            :closable="false"
            :title="$t('admin.common.loadFailed')"
            class="mb-2"
            show-icon
            type="error"
          />
          <el-table v-else v-loading="providersLoading" :data="providers" size="small">
            <el-table-column :label="$t('admin.system.social.oauth.providerName')" min-width="120" prop="name"/>
            <el-table-column :label="$t('admin.system.social.oauth.providerKey')" prop="key" width="100"/>
            <el-table-column :label="$t('admin.system.social.oauth.providerConfigured')" width="110">
              <template #default="{ row }">
                <el-tag :type="(row as OAuthProviderItem).configured ? 'success' : 'info'" size="small">
                  {{
                    (row as OAuthProviderItem).configured
                      ? $t('admin.system.social.oauth.configured')
                      : $t('admin.system.social.oauth.notConfigured')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.social.oauth.supportsPkce')" width="90">
              <template #default="{ row }">
                {{ (row as OAuthProviderItem).supports_pkce ? $t('admin.common.yes') : $t('admin.common.no') }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="160">
              <template #default="{ row }">
                <el-button
                  :disabled="!(row as OAuthProviderItem).configured"
                  :loading="authorizingKey === (row as OAuthProviderItem).key"
                  link
                  type="primary"
                  @click="onAuthorize(row as OAuthProviderItem)"
                >
                  {{ $t('admin.system.social.oauth.generateAuthorize') }}
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty :description="$t('admin.common.empty')" :image-size="80"/>
            </template>
          </el-table>

          <p v-if="providers.some((item) => !item.configured)" class="mt-2 text-xs">
            {{ $t('admin.system.social.oauth.notConfiguredHint') }}
          </p>
        </el-card>

        <!-- 已生成的授权跳转信息 -->
        <el-card v-for="(info, key) in authorizeInfo" :key="key" class="mb-4" shadow="never">
          <template #header>
            <span>{{ providerLabel(info.provider) }}</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item :label="$t('admin.system.social.oauth.authorizeUrlLabel')">
              <span class="break-all text-xs">{{ info.authorize_url }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.social.oauth.stateLabel')">
              <span class="break-all text-xs">{{ info.state }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.social.oauth.redirectUriLabel')">
              <span class="break-all text-xs">{{ info.redirect_uri }}</span>
            </el-descriptions-item>
            <el-descriptions-item v-if="info.code_challenge"
                                  :label="$t('admin.system.social.oauth.codeChallengeLabel')">
              <span class="break-all text-xs">{{ info.code_challenge }}</span>
            </el-descriptions-item>
            <el-descriptions-item v-if="info.code_verifier" :label="$t('admin.system.social.oauth.codeVerifierLabel')">
              <span class="break-all text-xs">{{ info.code_verifier }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <div class="mt-2 flex gap-2">
            <el-button size="small" @click="copyText(info.authorize_url)">
              {{ $t('admin.system.social.oauth.copy') }}
            </el-button>
            <el-button size="small" type="primary" @click="openAuthorizeUrl(info.authorize_url)">
              {{ $t('admin.system.social.oauth.openAuthorize') }}
            </el-button>
          </div>
        </el-card>

        <!-- 我的绑定 -->
        <el-card shadow="never">
          <template #header>
            <div class="flex items-center justify-between">
              <span>{{ $t('admin.system.social.oauth.bindingsTitle') }}</span>
              <el-button :loading="bindingsLoading" link size="small" @click="loadBindings">
                {{ $t('admin.common.refresh') }}
              </el-button>
            </div>
          </template>

          <el-alert
            v-if="bindingsFailed"
            :closable="false"
            :title="$t('admin.common.loadFailed')"
            class="mb-2"
            show-icon
            type="error"
          />
          <el-table v-else v-loading="bindingsLoading" :data="bindings" size="small">
            <el-table-column :label="$t('admin.system.social.provider')" min-width="120">
              <template #default="{ row }">
                {{ providerLabel((row as OAuthBindingItem).provider) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.social.providerUserId')" min-width="160"
                             prop="provider_user_id" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.system.social.hasToken')" width="110">
              <template #default="{ row }">
                <el-tag :type="(row as OAuthBindingItem).has_token ? 'success' : 'info'" size="small">
                  {{ (row as OAuthBindingItem).has_token ? $t('admin.common.yes') : $t('admin.common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.social.tokenExpiresAt')" min-width="170"
                             prop="token_expires_at" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.common.updatedAt')" min-width="170" prop="updated_at"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="110">
              <template #default="{ row }">
                <el-button link type="danger" @click="onUnbindSelf(row as OAuthBindingItem)">
                  {{ $t('admin.system.social.unbind') }}
                </el-button>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty :description="$t('admin.system.social.oauth.bindingsEmpty')" :image-size="80"/>
            </template>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </AdminPage>
</template>
