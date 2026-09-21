<script lang="ts" setup>
/**
 * 广告管理（T5-11 批次 1）
 *
 * 对齐 v3 `/marketing/ad`：广告投放统计 + 广告列表 + 广告位管理（双标签）。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {adApi, type AdItem, type AdPlacementItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.marketing.ad.title',
  permission: 'module_marketing:ad:view',
})

const {t} = useI18n()
const activeTab = ref('ads')

// ---- 统计 ----
const stats = reactive({total_ads: 0, active_ads: 0, total_clicks: 0, total_impressions: 0, total_budget: 0})

async function loadStats() {
  const s = await adApi.stats()
  Object.assign(stats, s)
}

onMounted(() => {
  loadStats().catch(() => {
  })
})

// ---- 广告列表 ----
interface AdQueryForm extends PageQuery {
  keyword?: string
  placement_id?: number
  is_active?: boolean
}

const {
  list: adList,
  loading: adLoading,
  total: adTotal,
  page: adPage,
  pageSize: adPageSize,
  query: adQuery,
  search: adSearch,
  reset: adReset,
  load: adLoad,
  onPageChange: onAdPageChange,
  onSizeChange: onAdPageSizeChange,
} = useTable<AdItem, AdQueryForm>({
  fetcher: (params) => adApi.list(params),
  defaultQuery: {keyword: '', placement_id: undefined, is_active: undefined},
  syncUrl: true,
})

// ---- 广告位列表 ----
const {
  list: placementList,
  loading: placementLoading,
  total: placementTotal,
  page: placementPage,
  pageSize: placementPageSize,
  search: placementSearch,
  reset: placementReset,
  load: placementLoad,
  onPageChange: onPlacementPageChange,
} = useTable<AdPlacementItem>({
  fetcher: (params) => adApi.placements(params),
})

onMounted(() => {
  placementLoad().catch(() => {
  })
})

const placementName = (id?: number | null) =>
  placementList.value.find(p => p.id === id)?.name || '-'

// ---- 广告新建 / 编辑 ----
const adFormVisible = ref(false)
const adEditingId = ref<number | null>(null)
const adSaving = ref(false)
const adForm = reactive({
  title: '', image_url: '', link_url: '', alt_text: '', ad_type: 'image',
  placement_id: undefined as number | undefined, start_date: '', end_date: '',
  budget: undefined as number | undefined, is_active: true, priority: 0,
})

const adFormTitle = computed(() =>
  adEditingId.value ? t('admin.marketing.ad.editAd') : t('admin.marketing.ad.createAd'))

function openAdCreate() {
  adEditingId.value = null
  Object.assign(adForm, {
    title: '', image_url: '', link_url: '', alt_text: '', ad_type: 'image',
    placement_id: undefined, start_date: '', end_date: '', budget: undefined,
    is_active: true, priority: 0,
  })
  adFormVisible.value = true
}

function openAdEdit(row: AdItem) {
  adEditingId.value = row.id
  Object.assign(adForm, {
    title: row.title || '',
    image_url: row.image_url || '',
    link_url: row.link_url || '',
    alt_text: row.alt_text || '',
    ad_type: row.ad_type || 'image',
    placement_id: row.placement_id || undefined,
    start_date: (row.start_date || '').slice(0, 16).replace('T', ' '),
    end_date: (row.end_date || '').slice(0, 16).replace('T', ' '),
    budget: row.budget ?? undefined,
    is_active: row.is_active,
    priority: row.priority ?? 0,
  })
  adFormVisible.value = true
}

async function submitAd() {
  if (!adForm.title.trim()) {
    ElMessage.warning(t('admin.marketing.ad.titleRequired'))
    return
  }
  adSaving.value = true
  try {
    const payload = {
      title: adForm.title.trim(),
      image_url: adForm.image_url || null,
      link_url: adForm.link_url || null,
      alt_text: adForm.alt_text || null,
      ad_type: adForm.ad_type,
      placement_id: adForm.placement_id ?? null,
      start_date: adForm.start_date ? new Date(adForm.start_date).toISOString() : null,
      end_date: adForm.end_date ? new Date(adForm.end_date).toISOString() : null,
      budget: adForm.budget ?? null,
      is_active: adForm.is_active,
      priority: adForm.priority,
    }
    if (adEditingId.value) {
      await adApi.update(adEditingId.value, payload)
    } else {
      await adApi.create(payload)
    }
    ElMessage.success(t('admin.common.save'))
    adFormVisible.value = false
    await adLoad()
    await loadStats()
  } finally {
    adSaving.value = false
  }
}

async function deleteAd(row: AdItem) {
  await ElMessageBox.confirm(t('admin.marketing.ad.deleteAdConfirm'), t('admin.common.notice'), {type: 'warning'})
  await adApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await adLoad()
  await loadStats()
}

// ---- 广告位新建 / 编辑 ----
const placementFormVisible = ref(false)
const placementEditingId = ref<number | null>(null)
const placementSaving = ref(false)
const placementForm = reactive({
  name: '', code: '', description: '', position: 'sidebar',
  width: undefined as number | undefined, height: undefined as number | undefined, is_active: true,
})

const placementFormTitle = computed(() =>
  placementEditingId.value ? t('admin.marketing.ad.editPlacement') : t('admin.marketing.ad.createPlacement'))

function openPlacementCreate() {
  placementEditingId.value = null
  Object.assign(placementForm, {
    name: '', code: '', description: '', position: 'sidebar',
    width: undefined, height: undefined, is_active: true,
  })
  placementFormVisible.value = true
}

function openPlacementEdit(row: AdPlacementItem) {
  placementEditingId.value = row.id
  Object.assign(placementForm, {
    name: row.name || '',
    code: row.code || '',
    description: row.description || '',
    position: row.position || 'sidebar',
    width: row.width ?? undefined,
    height: row.height ?? undefined,
    is_active: row.is_active,
  })
  placementFormVisible.value = true
}

async function submitPlacement() {
  if (!placementForm.name.trim() || !placementForm.code.trim()) {
    ElMessage.warning(t('admin.marketing.ad.placementRequired'))
    return
  }
  placementSaving.value = true
  try {
    const payload = {
      name: placementForm.name.trim(),
      code: placementForm.code.trim(),
      description: placementForm.description || null,
      position: placementForm.position,
      width: placementForm.width ?? null,
      height: placementForm.height ?? null,
      is_active: placementForm.is_active,
    }
    if (placementEditingId.value) {
      await adApi.updatePlacement(placementEditingId.value, payload)
    } else {
      await adApi.createPlacement(payload)
    }
    ElMessage.success(t('admin.common.save'))
    placementFormVisible.value = false
    await placementLoad()
  } finally {
    placementSaving.value = false
  }
}

async function deletePlacement(row: AdPlacementItem) {
  await ElMessageBox.confirm(t('admin.marketing.ad.deletePlacementConfirm'), t('admin.common.notice'), {type: 'warning'})
  await adApi.removePlacement(row.id)
  ElMessage.success(t('admin.common.delete'))
  await placementLoad()
}
</script>

<template>
  <div class="page-container">
    <!-- 统计卡 -->
    <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
      <el-card v-for="item in [
        {label: $t('admin.marketing.ad.statTotal'), value: stats.total_ads},
        {label: $t('admin.marketing.ad.statActive'), value: stats.active_ads},
        {label: $t('admin.marketing.ad.statClicks'), value: stats.total_clicks},
        {label: $t('admin.marketing.ad.statImpressions'), value: stats.total_impressions},
        {label: $t('admin.marketing.ad.statBudget'), value: stats.total_budget},
      ]" :key="item.label" shadow="never">
        <div class="text-xs text-fg-subtle">{{ item.label }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ item.value }}</div>
      </el-card>
    </div>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 广告 -->
        <el-tab-pane :label="$t('admin.marketing.ad.tabAds')" name="ads">
          <el-form :inline="true" :model="adQuery" @submit.prevent="adSearch()">
            <el-form-item :label="$t('admin.system.sensitiveWord.keyword')">
              <el-input v-model="adQuery.keyword" clearable style="width: 180px" @keyup.enter="adSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.marketing.ad.placement')">
              <el-select v-model="adQuery.placement_id" clearable style="width: 160px">
                <el-option v-for="p in placementList" :key="p.id" :label="p.name" :value="p.id"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="adSearch()">{{ $t('admin.common.search') }}</el-button>
              <el-button :icon="Refresh" @click="adReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button v-auth="'module_marketing:ad:create'" :icon="Plus" type="primary" @click="openAdCreate">
              {{ $t('admin.marketing.ad.createAd') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: adTotal}) }}</span>
          </div>

          <AdminTableSkeleton v-if="adLoading && !adList.length" :rows="5"/>

          <AdminEmpty v-else-if="!adLoading && !adList.length" :title="$t('admin.common.empty')"/>
          <el-table v-else v-loading="adLoading" :data="adList" border stripe>
            <el-table-column :label="$t('admin.common.name')" min-width="160" prop="title" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.marketing.ad.adType')" prop="ad_type" width="90"/>
            <el-table-column :label="$t('admin.marketing.ad.placement')" width="120">
              <template #default="{ row }">{{ placementName((row as AdItem).placement_id) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.ad.statClicks')" prop="click_count" width="90"/>
            <el-table-column :label="$t('admin.marketing.ad.statImpressions')" prop="impression_count" width="90"/>
            <el-table-column :label="$t('admin.marketing.ad.priority')" prop="priority" width="80"/>
            <el-table-column :label="$t('admin.common.status')" width="90">
              <template #default="{ row }">
                <el-tag :type="(row as AdItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as AdItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
              <template #default="{ row }">
                <el-button v-auth="'module_marketing:ad:edit'" link type="primary" @click="openAdEdit(row as AdItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_marketing:ad:delete'" link type="danger" @click="deleteAd(row as AdItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="adPage" :page-size="adPageSize" :page-sizes="[10, 20, 50]" :total="adTotal"
            background class="table-pagination" layout="total, sizes, prev, pager, next"
            @current-change="onAdPageChange" @size-change="onAdPageSizeChange"
          />
        </el-tab-pane>

        <!-- 广告位 -->
        <el-tab-pane :label="$t('admin.marketing.ad.tabPlacements')" name="placements">
          <div class="table-toolbar">
            <el-button v-auth="'module_marketing:ad:create'" :icon="Plus" type="primary" @click="openPlacementCreate">
              {{ $t('admin.marketing.ad.createPlacement') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: placementTotal}) }}</span>
          </div>

          <el-table v-loading="placementLoading" :data="placementList" border stripe>
            <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name"/>
            <el-table-column :label="$t('admin.marketing.ad.placementCode')" prop="code" width="140"/>
            <el-table-column :label="$t('admin.marketing.ad.placementPosition')" prop="position" width="120"/>
            <el-table-column :label="$t('admin.marketing.ad.placementSize')" width="110">
              <template #default="{ row }">{{ (row as AdPlacementItem).width || '-' }} ×
                {{ (row as AdPlacementItem).height || '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.status')" width="90">
              <template #default="{ row }">
                <el-tag :type="(row as AdPlacementItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as AdPlacementItem).is_active ? $t('admin.system.sensitiveWord.active') : $t('admin.system.sensitiveWord.inactive')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" width="150">
              <template #default="{ row }">
                <el-button v-auth="'module_marketing:ad:edit'" link type="primary"
                           @click="openPlacementEdit(row as AdPlacementItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_marketing:ad:delete'" link type="danger"
                           @click="deletePlacement(row as AdPlacementItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="placementPage" :page-size="placementPageSize" :total="placementTotal"
            background class="table-pagination" layout="total, prev, pager, next"
            @current-change="onPlacementPageChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 广告表单 -->
    <el-drawer v-model="adFormVisible" :title="adFormTitle" destroy-on-close size="480px">
      <el-form :model="adForm" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="adForm.title"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.adType')">
          <el-select v-model="adForm.ad_type" style="width: 100%">
            <el-option :label="$t('admin.marketing.ad.typeImage')" value="image"/>
            <el-option :label="$t('admin.marketing.ad.typeText')" value="text"/>
            <el-option :label="$t('admin.marketing.ad.typeCode')" value="code"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.placement')">
          <el-select v-model="adForm.placement_id" clearable style="width: 100%">
            <el-option v-for="p in placementList" :key="p.id" :label="p.name" :value="p.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.imageUrl')">
          <el-input v-model="adForm.image_url"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.linkUrl')">
          <el-input v-model="adForm.link_url"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.budget')">
          <el-input-number v-model="adForm.budget" :min="0" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.priority')">
          <el-input-number v-model="adForm.priority" :min="0" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="adForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="adSaving" type="primary" @click="submitAd">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 广告位表单 -->
    <el-dialog v-model="placementFormVisible" :title="placementFormTitle" destroy-on-close width="480px">
      <el-form :model="placementForm" label-width="90px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="placementForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.placementCode')" required>
          <el-input v-model="placementForm.code" :disabled="!!placementEditingId"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.placementPosition')">
          <el-select v-model="placementForm.position" style="width: 100%">
            <el-option label="header" value="header"/>
            <el-option label="sidebar" value="sidebar"/>
            <el-option label="footer" value="footer"/>
            <el-option label="content" value="content"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.ad.placementSize')">
          <div class="flex gap-2">
            <el-input-number v-model="placementForm.width" :min="0" placeholder="W"/>
            <el-input-number v-model="placementForm.height" :min="0" placeholder="H"/>
          </div>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="placementForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="placementFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="placementSaving" type="primary" @click="submitPlacement">{{
            $t('admin.common.save')
          }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
