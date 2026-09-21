<script lang="ts" setup>
/**
 * GDPR 合规同意记录（T5-11 批次 3）
 *
 * 对齐 v3 `/system/gdpr`：同意记录列表 / 统计 / 删除。
 * 同意记录由前台授权动作写入，本页只读 + 治理（删除过期记录）。
 */
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {onMounted, ref} from 'vue'

import {gdprApi, type GdprConsentItem, type GdprStats} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.gdpr.title',
  permission: 'module_system:gdpr:view',
})

const {t} = useI18n()

interface GdprQueryForm extends PageQuery {
  user_id?: number
  consent_type?: string
  granted?: boolean
}

const list = useAdminList<GdprConsentItem, GdprQueryForm>({
  fetcher: (params) => gdprApi.list(params),
  defaultQuery: {consent_type: '', granted: undefined},
  syncUrl: true,
})

const stats = ref<GdprStats | null>(null)

async function loadStats(): Promise<void> {
  try {
    stats.value = await gdprApi.stats()
  } catch {
    stats.value = null
  }
}

onMounted(loadStats)

async function onDelete(row: GdprConsentItem) {
  await ElMessageBox.confirm(t('admin.system.gdpr.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await gdprApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await loadStats()
  await list.reload()
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.gdpr.desc')" :title="$t('admin.system.gdpr.title')">
    <!-- 统计卡：属于页面级信息，放在列表壳之外 -->
    <div v-if="stats" class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statTotal') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ stats.total }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statGranted') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ stats.granted }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statRevoked') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ stats.revoked }}</div>
      </el-card>
      <el-card shadow="never">
        <div class="text-xs text-fg-subtle">{{ $t('admin.system.gdpr.statTypes') }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ Object.keys(stats.by_type || {}).length }}</div>
      </el-card>
    </div>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.system.gdpr.emptyFiltered') : $t('admin.system.gdpr.emptyDesc')"
      :empty-title="$t('admin.system.gdpr.emptyTitle')"
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
        <el-form-item :label="$t('admin.system.gdpr.consentType')">
          <el-input
            v-model="list.query.consent_type"
            clearable
            :placeholder="$t('admin.system.gdpr.consentTypePlaceholder')"
            style="width: 180px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.gdpr.granted')">
          <el-select v-model="list.query.granted" :placeholder="$t('admin.common.all')" clearable style="width: 110px">
            <el-option :label="$t('admin.system.gdpr.grantedYes')" :value="true"/>
            <el-option :label="$t('admin.system.gdpr.grantedNo')" :value="false"/>
          </el-select>
        </el-form-item>
      </template>

      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column :label="$t('admin.system.gdpr.userId')" prop="user_id" width="100"/>
      <el-table-column :label="$t('admin.system.gdpr.consentType')" min-width="140" prop="consent_type"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.gdpr.granted')" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as GdprConsentItem).granted ? 'success' : 'info'" size="small">
            {{
              (row as GdprConsentItem).granted ? $t('admin.system.gdpr.grantedYes') : $t('admin.system.gdpr.grantedNo')
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.gdpr.details')" min-width="160" prop="details"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.gdpr.ipAddress')" min-width="130" prop="ip_address"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
        <template #default="{ row }">
          <el-button
            v-auth="'module_system:gdpr:delete'"
            link
            type="danger"
            @click="onDelete(row as GdprConsentItem)"
          >
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>
  </AdminPage>
</template>
