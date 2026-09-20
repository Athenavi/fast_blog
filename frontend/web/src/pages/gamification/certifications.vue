<script lang="ts" setup>
/**
 * 专家认证审核（后台独立页，`/gamification/certifications`）
 *
 * 数据源：v3 `/api/v3/gamification/certification`
 *  - 待审队列 `pending`（分页）→ 审核 `review`（通过 / 驳回，带意见）
 *  - 已通过专家 `experts`（公开端点，**自动排除已过期**）→ 撤销 `revoke`
 *  - 统计 `stats`（含 30 天内到期 `expiring_soon` 与已过期 `expired`）
 *
 * 说明：后端只有「待审队列」列表端点，已通过的认证通过公开专家列表拿到 `id` 后再撤销，
 * 因此**已过期的认证不在这里出现**（它们已自动从专家列表消失，也无需撤销）。
 * 每次审核 / 撤销都会往 `certification_reviews` 追加一条流水，可追溯。
 */
import {Refresh} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {onMounted, reactive, ref} from 'vue'

import {certificationApi, type CertificationItem, type CertificationStats, type ExpertQuery} from '@/api'
import type {PageQuery} from '@/api/types'
import {formatDateTime} from '@/utils/format'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.gamification.certifications.title',
  permission: 'module_gamification:certification:view',
})

const {t} = useI18n()

const tab = ref<'pending' | 'approved'>('pending')
const stats = ref<CertificationStats | null>(null)
const loading = ref(false)

/** 两张表都手动触发加载（切 tab 时只拉当前那张） */
const {
  list: pendingList,
  loading: pendingLoading,
  total: pendingTotal,
  page: pendingPage,
  pageSize: pendingPageSize,
  load: loadPending,
  onPageChange: onPendingPageChange,
  onSizeChange: onPendingSizeChange,
} = useTable<CertificationItem, PageQuery>({
  fetcher: (params) => certificationApi.pending(params),
  immediate: false,
})

const {
  list: approvedList,
  loading: approvedLoading,
  total: approvedTotal,
  page: approvedPage,
  pageSize: approvedPageSize,
  load: loadApproved,
  onPageChange: onApprovedPageChange,
  onSizeChange: onApprovedSizeChange,
} = useTable<CertificationItem, ExpertQuery>({
  fetcher: (params) => certificationApi.experts(params),
  immediate: false,
})

const reviewDialog = ref(false)
const reviewTarget = ref<CertificationItem | null>(null)
const reviewForm = reactive<{ approve: boolean; comment: string }>({approve: true, comment: ''})
const submitting = ref(false)

const revokeDialog = ref(false)
const revokeTarget = ref<CertificationItem | null>(null)
const revokeComment = ref('')

async function loadStats(): Promise<void> {
  stats.value = await certificationApi.stats().catch(() => null)
}

async function load(): Promise<void> {
  loading.value = true
  try {
    await loadStats()
    if (tab.value === 'pending') await loadPending()
    else await loadApproved()
  } finally {
    loading.value = false
  }
}

async function switchTab(): Promise<void> {
  if (tab.value === 'approved' && !approvedList.value.length) {
    await loadApproved()
  } else if (tab.value === 'pending' && !pendingList.value.length) {
    await loadPending()
  }
}

function openReview(row: CertificationItem, approve: boolean): void {
  reviewTarget.value = row
  reviewForm.approve = approve
  reviewForm.comment = ''
  reviewDialog.value = true
}

async function submitReview(): Promise<void> {
  if (!reviewTarget.value) return
  submitting.value = true
  try {
    await certificationApi.review(
      reviewTarget.value.id,
      reviewForm.approve,
      reviewForm.comment || undefined,
    )
    ElMessage.success(t('admin.gamification.certifications.reviewDone'))
    reviewDialog.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

function openRevoke(row: CertificationItem): void {
  revokeTarget.value = row
  revokeComment.value = ''
  revokeDialog.value = true
}

async function submitRevoke(): Promise<void> {
  if (!revokeTarget.value) return
  submitting.value = true
  try {
    await certificationApi.revoke(revokeTarget.value.id, revokeComment.value || undefined)
    ElMessage.success(t('admin.gamification.certifications.revoked'))
    revokeDialog.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

function affiliation(row: CertificationItem): string {
  return [row.organization, row.position, row.department].filter(Boolean).join(' · ') || '-'
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__total">{{ $t('admin.gamification.certifications.statsTitle') }}</span>
        <el-button :icon="Refresh" @click="load()">{{ $t('admin.common.refresh') }}</el-button>
      </div>

      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.total') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.pending') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.pending ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.approved') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.approved ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.expiringSoon') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.expiring_soon ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.rejected') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.rejected ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.revoked') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.revoked ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.certifications.expired') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.expired ?? 0 }}</p>
        </el-card>
      </div>

      <el-table v-if="stats?.by_type?.length" :data="stats?.by_type ?? []" border class="mt-3" stripe>
        <el-table-column :label="$t('admin.gamification.certifications.certType')" min-width="160">
          <template #default="{ row }">{{ row.cert_type_name || row.cert_type }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.certifications.count')" prop="count" width="140"/>
      </el-table>
    </el-card>

    <el-card class="mt-4" shadow="never">
      <el-tabs v-model="tab" @tab-change="switchTab">
        <el-tab-pane :label="$t('admin.gamification.certifications.tabPending')" name="pending">
          <el-table v-loading="loading || pendingLoading" :data="pendingList" border stripe>
            <el-table-column :label="$t('admin.gamification.certifications.applicant')" min-width="120">
              <template #default="{ row }">{{ row.username || `#${row.user_id}` }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.certType')" width="120">
              <template #default="{ row }">{{ row.cert_type_name || row.cert_type }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.realName')" prop="real_name" width="120"/>
            <el-table-column :label="$t('admin.gamification.certifications.affiliation')" min-width="180">
              <template #default="{ row }">{{ affiliation(row as CertificationItem) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.workYears')" prop="work_years"
                             width="100"/>
            <el-table-column :label="$t('admin.gamification.certifications.intro')" min-width="200"
                             prop="intro" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.gamification.certifications.documents')" min-width="160">
              <template #default="{ row }">
                <div v-if="row.documents?.length" class="flex flex-col gap-0.5">
                  <a
                    v-for="doc in row.documents"
                    :key="doc.id"
                    :href="doc.file_url"
                    class="text-blue-600 hover:underline"
                    rel="noopener noreferrer nofollow"
                    target="_blank"
                  >{{ doc.file_name || doc.file_url }}</a>
                </div>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.createdAt')" width="170">
              <template #default="{ row }">{{ formatDateTime(row.applied_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="170">
              <template #default="{ row }">
                <el-button v-auth="'module_gamification:certification:review'" link type="success"
                           @click="openReview(row as CertificationItem, true)">
                  {{ $t('admin.gamification.certifications.approve') }}
                </el-button>
                <el-button v-auth="'module_gamification:certification:review'" link type="danger"
                           @click="openReview(row as CertificationItem, false)">
                  {{ $t('admin.gamification.certifications.reject') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="pendingPage"
            :page-size="pendingPageSize"
            :page-sizes="[10, 20, 50]"
            :total="pendingTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onPendingPageChange"
            @size-change="onPendingSizeChange"
          />
        </el-tab-pane>

        <el-tab-pane :label="$t('admin.gamification.certifications.tabApproved')" name="approved">
          <el-table v-loading="loading || approvedLoading" :data="approvedList" border stripe>
            <el-table-column :label="$t('admin.gamification.certifications.expert')" min-width="140">
              <template #default="{ row }">{{ row.username || `#${row.user_id}` }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.certType')" width="120">
              <template #default="{ row }">{{ row.cert_type_name || row.cert_type }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.affiliation')" min-width="180">
              <template #default="{ row }">{{ affiliation(row as CertificationItem) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.issuedAt')" width="170">
              <template #default="{ row }">{{ formatDateTime(row.issued_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.gamification.certifications.expiresAt')" width="170">
              <template #default="{ row }">{{ formatDateTime(row.expires_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="110">
              <template #default="{ row }">
                <el-button v-auth="'module_gamification:certification:review'" link type="danger"
                           @click="openRevoke(row as CertificationItem)">
                  {{ $t('admin.gamification.certifications.revoke') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="approvedPage"
            :page-size="approvedPageSize"
            :page-sizes="[10, 20, 50]"
            :total="approvedTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onApprovedPageChange"
            @size-change="onApprovedSizeChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 审核 -->
    <el-dialog v-model="reviewDialog" :title="$t('admin.gamification.certifications.reviewTitle')" width="520px">
      <el-form label-width="90px">
        <el-form-item :label="$t('admin.gamification.certifications.applicant')">
          <span>{{ reviewTarget?.username || `#${reviewTarget?.user_id}` }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.certifications.result')">
          <el-radio-group v-model="reviewForm.approve">
            <el-radio :value="true">{{ $t('admin.gamification.certifications.approve') }}</el-radio>
            <el-radio :value="false">{{ $t('admin.gamification.certifications.reject') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.certifications.comment')">
          <el-input v-model="reviewForm.comment" :rows="3" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialog = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="submitting" type="primary" @click="submitReview()">
          {{ $t('admin.common.submit') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 撤销 -->
    <el-dialog v-model="revokeDialog" :title="$t('admin.gamification.certifications.revokeTitle')" width="480px">
      <el-form label-width="90px">
        <el-form-item :label="$t('admin.gamification.certifications.expert')">
          <span>{{ revokeTarget?.username || `#${revokeTarget?.user_id}` }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.certifications.comment')">
          <el-input v-model="revokeComment" :rows="3" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="revokeDialog = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="submitting" type="danger" @click="submitRevoke()">
          {{ $t('admin.gamification.certifications.revoke') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
