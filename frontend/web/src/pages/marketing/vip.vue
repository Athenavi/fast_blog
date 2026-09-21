<script lang="ts" setup>
/**
 * VIP 会员管理（T5-11 批次 1）
 *
 * 对齐 v3 `/marketing/vip`：套餐 / 权益 / 订阅（三标签）。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {vipApi, type VipFeatureItem, type VipPlanItem, type VipSubscriptionItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.marketing.vip.title',
  permission: 'module_marketing:vip:view',
})

const {t} = useI18n()
const activeTab = ref('plans')

const statusLabel = (status?: number) =>
  status === 0 ? t('admin.marketing.vip.subActive')
    : status === 2 ? t('admin.marketing.vip.subCancelled')
      : t('admin.marketing.vip.subExpired')
const statusTag = (status?: number) => (status === 0 ? 'success' : status === 2 ? 'warning' : 'info')

// ---- 套餐 ----
const planTable = useAdminList<VipPlanItem>({fetcher: (params) => vipApi.plans(params)})

const planFormVisible = ref(false)
const planEditingId = ref<number | null>(null)
const planSaving = ref(false)
const planForm = reactive({
  name: '', description: '', price: 0, original_price: undefined as number | undefined,
  duration_days: 30, level: 1, features_text: '', is_active: true,
})

const planFormTitle = computed(() =>
  planEditingId.value ? t('admin.marketing.vip.editPlan') : t('admin.marketing.vip.createPlan'))

function openPlanCreate() {
  planEditingId.value = null
  Object.assign(planForm, {
    name: '', description: '', price: 0, original_price: undefined,
    duration_days: 30, level: 1, features_text: '', is_active: true,
  })
  planFormVisible.value = true
}

function openPlanEdit(row: VipPlanItem) {
  planEditingId.value = row.id
  Object.assign(planForm, {
    name: row.name || '',
    description: row.description || '',
    price: row.price ?? 0,
    original_price: row.original_price ?? undefined,
    duration_days: row.duration_days ?? 30,
    level: row.level ?? 1,
    features_text: (row.features || []).join('，'),
    is_active: row.is_active,
  })
  planFormVisible.value = true
}

async function submitPlan() {
  if (!planForm.name.trim()) {
    ElMessage.warning(t('admin.marketing.vip.nameRequired'))
    return
  }
  planSaving.value = true
  try {
    const payload = {
      name: planForm.name.trim(),
      description: planForm.description || null,
      price: planForm.price,
      original_price: planForm.original_price ?? null,
      duration_days: planForm.duration_days,
      level: planForm.level,
      features: planForm.features_text.split(/[,，、\n]/).map(s => s.trim()).filter(Boolean),
      is_active: planForm.is_active,
    }
    if (planEditingId.value) {
      await vipApi.updatePlan(planEditingId.value, payload)
    } else {
      await vipApi.createPlan(payload)
    }
    ElMessage.success(t('admin.common.save'))
    planFormVisible.value = false
    await planTable.reload()
  } finally {
    planSaving.value = false
  }
}

async function deletePlan(row: VipPlanItem) {
  await ElMessageBox.confirm(t('admin.marketing.vip.deletePlanConfirm'), t('admin.common.notice'), {type: 'warning'})
  await vipApi.removePlan(row.id)
  ElMessage.success(t('admin.common.delete'))
  await planTable.reload()
}

// ---- 权益 ----
const featureTable = useAdminList<VipFeatureItem>({fetcher: (params) => vipApi.features(params)})

const featureFormVisible = ref(false)
const featureEditingId = ref<number | null>(null)
const featureSaving = ref(false)
const featureForm = reactive({
  code: '', name: '', description: '', required_level: 1, is_active: true,
})

const featureFormTitle = computed(() =>
  featureEditingId.value ? t('admin.marketing.vip.editFeature') : t('admin.marketing.vip.createFeature'))

function openFeatureCreate() {
  featureEditingId.value = null
  Object.assign(featureForm, {code: '', name: '', description: '', required_level: 1, is_active: true})
  featureFormVisible.value = true
}

function openFeatureEdit(row: VipFeatureItem) {
  featureEditingId.value = row.id
  Object.assign(featureForm, {
    code: row.code || '',
    name: row.name || '',
    description: row.description || '',
    required_level: row.required_level ?? 1,
    is_active: row.is_active,
  })
  featureFormVisible.value = true
}

async function submitFeature() {
  if (!featureForm.code.trim() || !featureForm.name.trim()) {
    ElMessage.warning(t('admin.marketing.vip.featureRequired'))
    return
  }
  featureSaving.value = true
  try {
    const payload = {
      code: featureForm.code.trim(),
      name: featureForm.name.trim(),
      description: featureForm.description || null,
      required_level: featureForm.required_level,
      is_active: featureForm.is_active,
    }
    if (featureEditingId.value) {
      await vipApi.updateFeature(featureEditingId.value, payload)
    } else {
      await vipApi.createFeature(payload)
    }
    ElMessage.success(t('admin.common.save'))
    featureFormVisible.value = false
    await featureTable.reload()
  } finally {
    featureSaving.value = false
  }
}

async function deleteFeature(row: VipFeatureItem) {
  await ElMessageBox.confirm(t('admin.marketing.vip.deleteFeatureConfirm'), t('admin.common.notice'), {type: 'warning'})
  await vipApi.removeFeature(row.id)
  ElMessage.success(t('admin.common.delete'))
  await featureTable.reload()
}

// ---- 订阅 ----
interface SubQueryForm extends PageQuery {
  user_id?: number
  status?: number
}

const subTable = useAdminList<VipSubscriptionItem, SubQueryForm>({
  fetcher: (params) => vipApi.subscriptions(params),
  defaultQuery: {user_id: undefined, status: undefined},
  syncUrl: true,
})
const subQuery = subTable.query

// ---- 手动开通 ----
const grantVisible = ref(false)
const grantSaving = ref(false)
const grantForm = reactive({
  user_id: undefined as number | undefined, plan_id: undefined as number | undefined,
})
const planOptions = ref<VipPlanItem[]>([])

async function openGrant() {
  if (!planOptions.value.length) {
    const {items} = await vipApi.plans({page: 1, page_size: 100})
    planOptions.value = items
  }
  grantForm.user_id = undefined
  grantForm.plan_id = undefined
  grantVisible.value = true
}

async function submitGrant() {
  if (!grantForm.user_id || !grantForm.plan_id) {
    ElMessage.warning(t('admin.marketing.vip.grantRequired'))
    return
  }
  grantSaving.value = true
  try {
    await vipApi.createSubscription({user_id: grantForm.user_id, plan_id: grantForm.plan_id})
    ElMessage.success(t('admin.marketing.vip.grantDone'))
    grantVisible.value = false
    await subTable.reload()
  } finally {
    grantSaving.value = false
  }
}

async function cancelSub(row: VipSubscriptionItem) {
  await ElMessageBox.confirm(t('admin.marketing.vip.cancelConfirm'), t('admin.common.notice'), {type: 'warning'})
  await vipApi.cancelSubscription(row.id)
  ElMessage.success(t('admin.common.save'))
  await subTable.reload()
}

onMounted(() => {
  planTable.reload().catch(() => {
  })
  featureTable.reload().catch(() => {
  })
  subTable.reload().catch(() => {
  })
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 套餐 -->
        <el-tab-pane :label="$t('admin.marketing.vip.tabPlans')" name="plans">
          <div class="table-toolbar">
            <el-button v-auth="'module_marketing:vip:create'" :icon="Plus" type="primary" @click="openPlanCreate">
              {{ $t('admin.marketing.vip.createPlan') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: planTable.total.value}) }}</span>
          </div>
          <AdminTableSkeleton v-if="planTable.loading.value && !planTable.rows.value.length" :rows="5"/>

          <AdminEmpty
            v-else-if="!planTable.loading.value && !planTable.rows.value.length"
            :title="planTable.failed.value ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
            :variant="planTable.failed.value ? 'error' : 'default'"
          >
            <el-button v-if="planTable.failed.value" :icon="Refresh" @click="planTable.reload()">
              {{ $t('admin.common.retry') }}
            </el-button>
          </AdminEmpty>
          <el-table v-else v-loading="planTable.loading.value" :data="planTable.rows.value" border stripe>
            <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name"/>
            <el-table-column :label="$t('admin.marketing.vip.price')" width="100">
              <template #default="{ row }">￥{{ (row as VipPlanItem).price }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.vip.duration')" width="110">
              <template #default="{ row }">{{ (row as VipPlanItem).duration_days }}{{
                  $t('admin.marketing.vip.days')
                }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.vip.level')" width="90">
              <template #default="{ row }">Lv{{ (row as VipPlanItem).level }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.vip.features')" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ ((row as VipPlanItem).features || []).join('、') || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.status')" width="90">
              <template #default="{ row }">
                <el-tag :type="(row as VipPlanItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as VipPlanItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" width="150">
              <template #default="{ row }">
                <el-button v-auth="'module_marketing:vip:edit'" link type="primary"
                           @click="openPlanEdit(row as VipPlanItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_marketing:vip:delete'" link type="danger"
                           @click="deletePlan(row as VipPlanItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            :current-page="planTable.page.value" :page-size="planTable.pageSize.value" :total="planTable.total.value"
            background class="table-pagination" layout="total, prev, pager, next"
            @current-change="planTable.onPageChange"
          />
        </el-tab-pane>

        <!-- 权益 -->
        <el-tab-pane :label="$t('admin.marketing.vip.tabFeatures')" name="features">
          <div class="table-toolbar">
            <el-button v-auth="'module_marketing:vip:create'" :icon="Plus" type="primary" @click="openFeatureCreate">
              {{ $t('admin.marketing.vip.createFeature') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: featureTable.total.value}) }}</span>
          </div>
          <el-table v-loading="featureTable.loading.value" :data="featureTable.rows.value" border stripe>
            <el-table-column label="Code" prop="code" width="160"/>
            <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name"/>
            <el-table-column :label="$t('admin.common.description')" min-width="200" prop="description"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.marketing.vip.level')" width="90">
              <template #default="{ row }">Lv{{ (row as VipFeatureItem).required_level }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" width="150">
              <template #default="{ row }">
                <el-button v-auth="'module_marketing:vip:edit'" link type="primary"
                           @click="openFeatureEdit(row as VipFeatureItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_marketing:vip:delete'" link type="danger"
                           @click="deleteFeature(row as VipFeatureItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            :current-page="featureTable.page.value" :page-size="featureTable.pageSize.value"
            :total="featureTable.total.value"
            background class="table-pagination" layout="total, prev, pager, next"
            @current-change="featureTable.onPageChange"
          />
        </el-tab-pane>

        <!-- 订阅 -->
        <el-tab-pane :label="$t('admin.marketing.vip.tabSubscriptions')" name="subscriptions">
          <el-form :inline="true" @submit.prevent="subTable.search()">
            <el-form-item :label="$t('admin.marketing.vip.userId')">
              <el-input-number v-model="subQuery.user_id" :min="1" style="width: 140px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.common.status')">
              <el-select v-model="subQuery.status" clearable style="width: 130px">
                <el-option :label="$t('admin.marketing.vip.subActive')" :value="0"/>
                <el-option :label="$t('admin.marketing.vip.subExpired')" :value="1"/>
                <el-option :label="$t('admin.marketing.vip.subCancelled')" :value="2"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="subTable.search()">{{
                  $t('admin.common.search')
                }}
              </el-button>
              <el-button :icon="Refresh" @click="subTable.reset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>
          <div class="table-toolbar">
            <el-button v-auth="'module_marketing:vip:create'" :icon="Plus" type="primary" @click="openGrant">
              {{ $t('admin.marketing.vip.grant') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: subTable.total.value}) }}</span>
          </div>
          <el-table v-loading="subTable.loading.value" :data="subTable.rows.value" border stripe>
            <el-table-column :label="$t('admin.marketing.vip.userId')" prop="user_id" width="90"/>
            <el-table-column :label="$t('admin.marketing.vip.planId')" prop="plan_id" width="90"/>
            <el-table-column :label="$t('admin.marketing.vip.startsAt')" width="170">
              <template #default="{ row }">{{ (row as VipSubscriptionItem).starts_at || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.vip.expiresAt')" width="170">
              <template #default="{ row }">{{ (row as VipSubscriptionItem).expires_at || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.vip.payment')" prop="payment_amount" width="110"/>
            <el-table-column :label="$t('admin.common.status')" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTag((row as VipSubscriptionItem).status)" size="small">
                  {{ statusLabel((row as VipSubscriptionItem).status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" width="110">
              <template #default="{ row }">
                <el-button
                  v-if="(row as VipSubscriptionItem).status === 0"
                  v-auth="'module_marketing:vip:edit'" link type="warning"
                  @click="cancelSub(row as VipSubscriptionItem)"
                >
                  {{ $t('admin.marketing.vip.cancelSub') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            :current-page="subTable.page.value" :page-size="subTable.pageSize.value" :total="subTable.total.value"
            background class="table-pagination" layout="total, prev, pager, next"
            @current-change="subTable.onPageChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 套餐表单 -->
    <el-drawer v-model="planFormVisible" :title="planFormTitle" destroy-on-close size="480px">
      <el-form :model="planForm" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="planForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="planForm.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.price')">
          <el-input-number v-model="planForm.price" :min="0" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.originalPrice')">
          <el-input-number v-model="planForm.original_price" :min="0" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.duration')">
          <el-input-number v-model="planForm.duration_days" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.level')">
          <el-input-number v-model="planForm.level" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.features')">
          <el-input v-model="planForm.features_text" :placeholder="$t('admin.marketing.vip.featuresHint')"
                    type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="planForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="planSaving" type="primary" @click="submitPlan">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 权益表单 -->
    <el-dialog v-model="featureFormVisible" :title="featureFormTitle" destroy-on-close width="480px">
      <el-form :model="featureForm" label-width="90px">
        <el-form-item label="Code" required>
          <el-input v-model="featureForm.code" :disabled="!!featureEditingId"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="featureForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="featureForm.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.level')">
          <el-input-number v-model="featureForm.required_level" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="featureForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="featureFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="featureSaving" type="primary" @click="submitFeature">{{
            $t('admin.common.save')
          }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 手动开通 -->
    <el-dialog v-model="grantVisible" :title="$t('admin.marketing.vip.grant')" width="420px">
      <el-form :model="grantForm" label-width="90px">
        <el-form-item :label="$t('admin.marketing.vip.userId')" required>
          <el-input-number v-model="grantForm.user_id" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.vip.planName')" required>
          <el-select v-model="grantForm.plan_id" style="width: 100%">
            <el-option v-for="p in planOptions" :key="p.id" :label="`${p.name}（￥${p.price}）`" :value="p.id"/>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grantVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="grantSaving" type="primary" @click="submitGrant">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>
