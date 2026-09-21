<script lang="ts" setup>
/**
 * 社交账号绑定管理（T5-11 批次 3）
 *
 * 对齐 v3 `/system/social`：OAuthAccount 绑定档案列表 + 解绑。
 * 令牌字段脱敏（响应只有 has_token 布尔位）；OAuth 登录流程本身在 auth 体系。
 */
import {ElMessage, ElMessageBox} from '@/utils/feedback'

import {type SocialAccountItem, socialApi} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.social.title',
  permission: 'module_system:social:view',
})

const {t} = useI18n()

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
</script>

<template>
  <AdminPage :desc="$t('admin.system.social.desc')" :title="$t('admin.system.social.title')">
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
            clearable
            :placeholder="$t('admin.system.social.providerPlaceholder')"
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
      <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at" show-overflow-tooltip/>
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
  </AdminPage>
</template>
