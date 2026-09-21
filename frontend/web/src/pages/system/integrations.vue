<script lang="ts" setup>
/**
 * 第三方集成（T5-11 批次 3）
 *
 * 对齐 v3 `/system/integration`：SSO Provider 与 LDAP 两组 CRUD。
 * 凭据（client_secret / bind_password）只写不读，响应仅含 has_* 布尔位；
 * 更新时留空保持原值。
 *
 * 后端这两个列表接口不分页（直接返回数组），因此列表壳关闭分页器。
 */
import {Plus} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {integrationApi, type LdapConfigItem, type SsoProviderItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.integration.title',
  permission: 'module_system:integration:view',
})

const {t} = useI18n()

const activeTab = ref<'sso' | 'ldap'>('sso')

// ---- SSO ----
const sso = useAdminList<SsoProviderItem, PageQuery>({
  // 列表接口不分页（返回数组），包一层以满足 fetcher 契约
  fetcher: async () => {
    const items = await integrationApi.listSso()
    return {items: items ?? [], total: items?.length ?? 0, page: 1, pageSize: 0, pages: 1}
  },
  pageSize: 100,
})

const ssoFormVisible = ref(false)
const ssoEditingId = ref<number | null>(null)
const ssoSaving = ref(false)
const ssoForm = reactive<{
  provider_type: string;
  name: string;
  client_id: string;
  client_secret: string;
  authorization_url: string;
  token_url: string;
  userinfo_url: string;
  scope: string;
  redirect_uri: string;
  auto_provision_users: boolean;
  default_role: string;
  is_active: boolean
}>({
  provider_type: 'oauth2',
  name: '',
  client_id: '',
  client_secret: '',
  authorization_url: '',
  token_url: '',
  userinfo_url: '',
  scope: '',
  redirect_uri: '',
  auto_provision_users: false,
  default_role: '',
  is_active: true,
})

const ssoFormTitle = computed(() =>
  ssoEditingId.value ? t('admin.system.integration.editSso') : t('admin.system.integration.createSso'))

function openSsoCreate() {
  ssoEditingId.value = null
  Object.assign(ssoForm, {
    provider_type: 'oauth2', name: '', client_id: '', client_secret: '',
    authorization_url: '', token_url: '', userinfo_url: '', scope: '', redirect_uri: '',
    auto_provision_users: false, default_role: '', is_active: true,
  })
  ssoFormVisible.value = true
}

function openSsoEdit(row: SsoProviderItem) {
  ssoEditingId.value = row.id
  Object.assign(ssoForm, {
    provider_type: row.provider_type || 'oauth2',
    name: row.name || '',
    client_id: row.client_id || '',
    client_secret: '', // 脱敏字段不回填，留空保持原值
    authorization_url: row.authorization_url || '',
    token_url: row.token_url || '',
    userinfo_url: row.userinfo_url || '',
    scope: row.scope || '',
    redirect_uri: row.redirect_uri || '',
    auto_provision_users: row.auto_provision_users,
    default_role: row.default_role || '',
    is_active: row.is_active,
  })
  ssoFormVisible.value = true
}

async function submitSso() {
  if (!ssoForm.name.trim() || !ssoForm.client_id.trim()) {
    ElMessage.warning(t('admin.system.integration.ssoRequired'))
    return
  }
  if (!ssoEditingId.value && !ssoForm.client_secret) {
    ElMessage.warning(t('admin.system.integration.secretRequired'))
    return
  }
  ssoSaving.value = true
  try {
    const payload = {
      provider_type: ssoForm.provider_type,
      name: ssoForm.name.trim(),
      client_id: ssoForm.client_id.trim(),
      client_secret: ssoForm.client_secret || undefined,
      authorization_url: ssoForm.authorization_url || null,
      token_url: ssoForm.token_url || null,
      userinfo_url: ssoForm.userinfo_url || null,
      scope: ssoForm.scope || null,
      redirect_uri: ssoForm.redirect_uri || null,
      auto_provision_users: ssoForm.auto_provision_users,
      default_role: ssoForm.default_role || null,
      is_active: ssoForm.is_active,
    }
    if (ssoEditingId.value) {
      await integrationApi.updateSso(ssoEditingId.value, payload)
    } else {
      await integrationApi.createSso(payload as Parameters<typeof integrationApi.createSso>[0])
    }
    ElMessage.success(t('admin.common.save'))
    ssoFormVisible.value = false
    await sso.reload()
  } finally {
    ssoSaving.value = false
  }
}

async function deleteSso(row: SsoProviderItem) {
  await ElMessageBox.confirm(t('admin.system.integration.deleteSsoConfirm'), t('admin.common.notice'), {type: 'warning'})
  await integrationApi.removeSso(row.id)
  ElMessage.success(t('admin.common.delete'))
  await sso.reload()
}

// ---- LDAP ----
const ldap = useAdminList<LdapConfigItem, PageQuery>({
  fetcher: async () => {
    const items = await integrationApi.listLdap()
    return {items: items ?? [], total: items?.length ?? 0, page: 1, pageSize: 0, pages: 1}
  },
  pageSize: 100,
})

const ldapFormVisible = ref(false)
const ldapEditingId = ref<number | null>(null)
const ldapSaving = ref(false)
const ldapForm = reactive<{
  server_url: string;
  bind_dn: string;
  bind_password: string;
  base_dn: string;
  user_filter: string;
  use_ssl: boolean;
  auto_sync_users: boolean;
  sync_interval: number;
  default_role: string;
  is_active: boolean
}>({
  server_url: '',
  bind_dn: '',
  bind_password: '',
  base_dn: '',
  user_filter: '',
  use_ssl: true,
  auto_sync_users: false,
  sync_interval: 3600,
  default_role: '',
  is_active: true,
})

const ldapFormTitle = computed(() =>
  ldapEditingId.value ? t('admin.system.integration.editLdap') : t('admin.system.integration.createLdap'))

function openLdapCreate() {
  ldapEditingId.value = null
  Object.assign(ldapForm, {
    server_url: '', bind_dn: '', bind_password: '', base_dn: '', user_filter: '',
    use_ssl: true, auto_sync_users: false, sync_interval: 3600, default_role: '', is_active: true,
  })
  ldapFormVisible.value = true
}

function openLdapEdit(row: LdapConfigItem) {
  ldapEditingId.value = row.id
  Object.assign(ldapForm, {
    server_url: row.server_url || '',
    bind_dn: row.bind_dn || '',
    bind_password: '', // 脱敏字段不回填，留空保持原值
    base_dn: row.base_dn || '',
    user_filter: row.user_filter || '',
    use_ssl: row.use_ssl,
    auto_sync_users: row.auto_sync_users,
    sync_interval: row.sync_interval,
    default_role: row.default_role || '',
    is_active: row.is_active,
  })
  ldapFormVisible.value = true
}

async function submitLdap() {
  if (!ldapForm.server_url.trim()) {
    ElMessage.warning(t('admin.system.integration.serverRequired'))
    return
  }
  if (!ldapEditingId.value && !ldapForm.bind_password) {
    ElMessage.warning(t('admin.system.integration.passwordRequired'))
    return
  }
  ldapSaving.value = true
  try {
    const payload = {
      server_url: ldapForm.server_url.trim(),
      bind_dn: ldapForm.bind_dn || null,
      bind_password: ldapForm.bind_password || undefined,
      base_dn: ldapForm.base_dn || null,
      user_filter: ldapForm.user_filter || null,
      use_ssl: ldapForm.use_ssl,
      auto_sync_users: ldapForm.auto_sync_users,
      sync_interval: ldapForm.sync_interval,
      default_role: ldapForm.default_role || null,
      is_active: ldapForm.is_active,
    }
    if (ldapEditingId.value) {
      await integrationApi.updateLdap(ldapEditingId.value, payload)
    } else {
      await integrationApi.createLdap(payload as Parameters<typeof integrationApi.createLdap>[0])
    }
    ElMessage.success(t('admin.common.save'))
    ldapFormVisible.value = false
    await ldap.reload()
  } finally {
    ldapSaving.value = false
  }
}

async function deleteLdap(row: LdapConfigItem) {
  await ElMessageBox.confirm(t('admin.system.integration.deleteLdapConfirm'), t('admin.common.notice'), {type: 'warning'})
  await integrationApi.removeLdap(row.id)
  ElMessage.success(t('admin.common.delete'))
  await ldap.reload()
}

onMounted(() => {
  sso.reload().catch(() => {
  })
  ldap.reload().catch(() => {
  })
})
</script>

<template>
  <AdminPage :desc="$t('admin.system.integration.desc')" :title="$t('admin.system.integration.title')">
    <el-tabs v-model="activeTab">
      <!-- SSO -->
      <el-tab-pane :label="$t('admin.system.integration.tabSso')" name="sso">
        <AdminListShell
          :empty-desc="$t('admin.system.integration.ssoEmptyDesc')"
          :empty-title="$t('admin.system.integration.ssoEmptyTitle')"
          :failed="sso.failed.value"
          :loading="sso.loading.value"
          :page="sso.page.value"
          :page-size="sso.pageSize.value"
          :paginate="false"
          :rows="sso.rows.value"
          :selectable="false"
          :total="sso.total.value"
          @refresh="sso.reload"
        >
          <template #actions>
            <el-button v-auth="'module_system:integration:create'" :icon="Plus" type="primary" @click="openSsoCreate">
              {{ $t('admin.system.integration.createSso') }}
            </el-button>
          </template>

          <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.integration.providerType')" prop="provider_type" width="110"/>
          <el-table-column :label="$t('admin.system.integration.clientId')" min-width="150" prop="client_id"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.integration.hasSecret')" width="110">
            <template #default="{ row }">
              <el-tag :type="(row as SsoProviderItem).has_client_secret ? 'success' : 'info'" size="small">
                {{
                  (row as SsoProviderItem).has_client_secret ? $t('admin.common.yes') : $t('admin.common.no')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.status')" width="90">
            <template #default="{ row }">
              <el-tag :type="(row as SsoProviderItem).is_active ? 'success' : 'info'" size="small">
                {{
                  (row as SsoProviderItem).is_active
                    ? $t('admin.system.integration.active')
                    : $t('admin.system.integration.inactive')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
            <template #default="{ row }">
              <el-button v-auth="'module_system:integration:edit'" link type="primary"
                         @click="openSsoEdit(row as SsoProviderItem)">
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button v-auth="'module_system:integration:delete'" link type="danger"
                         @click="deleteSso(row as SsoProviderItem)">
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- LDAP -->
      <el-tab-pane :label="$t('admin.system.integration.tabLdap')" name="ldap">
        <AdminListShell
          :empty-desc="$t('admin.system.integration.ldapEmptyDesc')"
          :empty-title="$t('admin.system.integration.ldapEmptyTitle')"
          :failed="ldap.failed.value"
          :loading="ldap.loading.value"
          :page="ldap.page.value"
          :page-size="ldap.pageSize.value"
          :paginate="false"
          :rows="ldap.rows.value"
          :selectable="false"
          :total="ldap.total.value"
          @refresh="ldap.reload"
        >
          <template #actions>
            <el-button v-auth="'module_system:integration:create'" :icon="Plus" type="primary" @click="openLdapCreate">
              {{ $t('admin.system.integration.createLdap') }}
            </el-button>
          </template>

          <el-table-column :label="$t('admin.system.integration.serverUrl')" min-width="200" prop="server_url"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.integration.bindDn')" min-width="180" prop="bind_dn"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.integration.hasPassword')" width="110">
            <template #default="{ row }">
              <el-tag :type="(row as LdapConfigItem).has_bind_password ? 'success' : 'info'" size="small">
                {{
                  (row as LdapConfigItem).has_bind_password ? $t('admin.common.yes') : $t('admin.common.no')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.integration.useSsl')" width="90">
            <template #default="{ row }">
              {{ (row as LdapConfigItem).use_ssl ? $t('admin.common.yes') : $t('admin.common.no') }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.status')" width="90">
            <template #default="{ row }">
              <el-tag :type="(row as LdapConfigItem).is_active ? 'success' : 'info'" size="small">
                {{
                  (row as LdapConfigItem).is_active
                    ? $t('admin.system.integration.active')
                    : $t('admin.system.integration.inactive')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
            <template #default="{ row }">
              <el-button v-auth="'module_system:integration:edit'" link type="primary"
                         @click="openLdapEdit(row as LdapConfigItem)">
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button v-auth="'module_system:integration:delete'" link type="danger"
                         @click="deleteLdap(row as LdapConfigItem)">
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>
    </el-tabs>

    <!-- SSO 表单 -->
    <el-drawer v-model="ssoFormVisible" :title="ssoFormTitle" destroy-on-close size="520px">
      <el-form :model="ssoForm" label-width="130px">
        <el-form-item :label="$t('admin.system.integration.providerType')" required>
          <el-select v-model="ssoForm.provider_type" style="width: 100%">
            <el-option label="OAuth2" value="oauth2"/>
            <el-option label="OIDC" value="oidc"/>
            <el-option label="SAML" value="saml"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="ssoForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.clientId')" required>
          <el-input v-model="ssoForm.client_id"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.clientSecret')"
                      :required="!ssoEditingId">
          <el-input
            v-model="ssoForm.client_secret"
            :placeholder="ssoEditingId ? $t('admin.system.integration.secretKeepHint') : ''"
            show-password
            type="password"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.authorizationUrl')">
          <el-input v-model="ssoForm.authorization_url"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.tokenUrl')">
          <el-input v-model="ssoForm.token_url"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.userinfoUrl')">
          <el-input v-model="ssoForm.userinfo_url"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.scope')">
          <el-input v-model="ssoForm.scope"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.redirectUri')">
          <el-input v-model="ssoForm.redirect_uri"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.autoProvision')">
          <el-switch v-model="ssoForm.auto_provision_users"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.defaultRole')">
          <el-input v-model="ssoForm.default_role"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="ssoForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ssoFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="ssoSaving" type="primary" @click="submitSso">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- LDAP 表单 -->
    <el-drawer v-model="ldapFormVisible" :title="ldapFormTitle" destroy-on-close size="520px">
      <el-form :model="ldapForm" label-width="130px">
        <el-form-item :label="$t('admin.system.integration.serverUrl')" required>
          <el-input v-model="ldapForm.server_url" placeholder="ldaps://..."/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.bindDn')">
          <el-input v-model="ldapForm.bind_dn"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.bindPassword')" :required="!ldapEditingId">
          <el-input
            v-model="ldapForm.bind_password"
            :placeholder="ldapEditingId ? $t('admin.system.integration.passwordKeepHint') : ''"
            show-password
            type="password"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.baseDn')">
          <el-input v-model="ldapForm.base_dn"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.userFilter')">
          <el-input v-model="ldapForm.user_filter" placeholder="(uid={0})"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.useSsl')">
          <el-switch v-model="ldapForm.use_ssl"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.autoSync')">
          <el-switch v-model="ldapForm.auto_sync_users"/>
        </el-form-item>
        <el-form-item v-if="ldapForm.auto_sync_users" :label="$t('admin.system.integration.syncInterval')">
          <el-input-number v-model="ldapForm.sync_interval" :min="60" :step="60"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.integration.defaultRole')">
          <el-input v-model="ldapForm.default_role"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="ldapForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ldapFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="ldapSaving" type="primary" @click="submitLdap">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>
  </AdminPage>
</template>
