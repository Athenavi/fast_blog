<script lang="ts" setup>
/**
 * 支付配置 · 税务配置面板
 *
 * 从 `pages/commerce/payment.vue` 的「税务配置」标签页抽出：税率配置表
 * （按国家 / 税种筛选）及其新建 / 编辑 / 删除。
 *
 * 注意它与「税务试算」是两套东西：本面板管的是 `tax_configs` 真表的 CRUD，
 * 试算则调用 `tax/calculate` 并**读取**这里配置的税率。
 *
 * 加载时机与原实现一致：`useAdminList` 默认挂载即加载。
 */
import {Delete, EditPen, Plus} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {paymentApi, type TaxConfigItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const {t} = useI18n()

const taxState = useAdminList<TaxConfigItem, PageQuery & { country?: string; tax_type?: string }>({
  fetcher: (params) => paymentApi.listTaxConfigs(params),
  defaultQuery: {keyword: '', country: '', tax_type: ''},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const taxList = taxState.rows
const taxLoading = taxState.loading
const taxTotal = taxState.total
const taxPage = taxState.page
const taxPageSize = taxState.pageSize
const taxQuery = taxState.query
const taxSearch = taxState.search
const taxReset = taxState.reset
const taxLoad = taxState.reload
const onTaxPageChange = taxState.onPageChange
const onTaxSizeChange = taxState.onSizeChange
const taxFailed = taxState.failed

const taxFormVisible = ref(false)
const taxEditingId = ref<number | null>(null)
const taxSaving = ref(false)
const taxForm = reactive({
  country: '',
  region: '',
  tax_type: '',
  rate: undefined as number | undefined,
  description: '',
  is_active: true,
})

const taxFormTitle = computed(() =>
  taxEditingId.value
    ? t('admin.commerce.payment.editTax')
    : t('admin.commerce.payment.createTax'),
)

function openTaxCreate(): void {
  taxEditingId.value = null
  Object.assign(taxForm, {
    country: '',
    region: '',
    tax_type: '',
    rate: undefined,
    description: '',
    is_active: true,
  })
  taxFormVisible.value = true
}

function openTaxEdit(row: TaxConfigItem): void {
  taxEditingId.value = row.id
  Object.assign(taxForm, {
    country: row.country || '',
    region: row.region || '',
    tax_type: row.tax_type || '',
    rate: row.rate ?? undefined,
    description: row.description || '',
    is_active: row.is_active,
  })
  taxFormVisible.value = true
}

async function submitTax(): Promise<void> {
  // 国家是 ISO 3166 的两位码，后端按此匹配，所以前端也卡住长度
  if (taxForm.country.trim().length !== 2 || !taxForm.tax_type.trim() || taxForm.rate === undefined) {
    ElMessage.warning(t('admin.commerce.payment.taxRequired'))
    return
  }
  taxSaving.value = true
  try {
    const payload = {
      country: taxForm.country.trim().toUpperCase(),
      region: taxForm.region.trim() || null,
      tax_type: taxForm.tax_type.trim(),
      rate: taxForm.rate,
      description: taxForm.description.trim() || null,
      is_active: taxForm.is_active,
    }
    if (taxEditingId.value) {
      await paymentApi.updateTaxConfig(taxEditingId.value, payload)
    } else {
      await paymentApi.createTaxConfig(payload)
    }
    ElMessage.success(t('admin.common.save'))
    taxFormVisible.value = false
    await taxLoad()
  } finally {
    taxSaving.value = false
  }
}

async function onDeleteTax(row: TaxConfigItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteTaxConfirm', {
      name: `${row.country || ''} ${row.tax_type || ''}`.trim() || row.id,
    }),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeTaxConfig(row.id)
  ElMessage.success(t('admin.common.delete'))
  await taxLoad()
}
</script>

<template>
  <AdminListShell
    :failed="taxFailed"
    :loading="taxLoading"
    :page="taxPage"
    :page-size="taxPageSize"
    :rows="taxList"
    :selectable="false"
    :total="taxTotal"
    @refresh="taxLoad"
    @reset="taxReset"
    @search="taxSearch"
    @page-change="onTaxPageChange"
    @size-change="onTaxSizeChange"
  >
    <template #filters>
      <el-form-item :label="$t('admin.commerce.payment.country')">
        <el-input v-model="taxQuery.country" clearable style="width: 100px" @keyup.enter="taxSearch()"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.taxType')">
        <el-input v-model="taxQuery.tax_type" clearable style="width: 130px" @keyup.enter="taxSearch()"/>
      </el-form-item>
    </template>

    <template #actions>
      <el-button v-auth="'module_commerce:payment:create'" :icon="Plus" type="primary" @click="openTaxCreate">
        {{ $t('admin.commerce.payment.createTax') }}
      </el-button>
    </template>

    <el-table-column :label="$t('admin.commerce.payment.country')" prop="country" width="100"/>
    <el-table-column :label="$t('admin.commerce.payment.region')" min-width="130" prop="region"/>
    <el-table-column :label="$t('admin.commerce.payment.taxType')" min-width="130" prop="tax_type"/>
    <el-table-column :label="$t('admin.commerce.payment.rate')" align="right" prop="rate" width="100"/>
    <el-table-column :label="$t('admin.common.status')" align="center" width="100">
      <template #default="{ row }">
        <el-tag :type="(row as TaxConfigItem).is_active ? 'success' : 'info'" size="small">
          {{ (row as TaxConfigItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
      <template #default="{ row }">
        <el-button v-auth="'module_commerce:payment:edit'" :icon="EditPen" link type="primary"
                   @click="openTaxEdit(row as TaxConfigItem)">
          {{ $t('admin.common.edit') }}
        </el-button>
        <el-button v-auth="'module_commerce:payment:delete'" :icon="Delete" link type="danger"
                   @click="onDeleteTax(row as TaxConfigItem)">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>
    </el-table-column>
  </AdminListShell>

  <!-- 税务配置表单 -->
  <el-drawer v-model="taxFormVisible" :title="taxFormTitle" destroy-on-close size="480px">
    <el-form :model="taxForm" label-width="120px">
      <el-form-item :label="$t('admin.commerce.payment.country')" required>
        <el-input v-model="taxForm.country" maxlength="2" placeholder="CN"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.region')">
        <el-input v-model="taxForm.region"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.taxType')" required>
        <el-input v-model="taxForm.tax_type" placeholder="VAT / GST / Sales Tax"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.rate')" required>
        <el-input-number v-model="taxForm.rate" :min="0" :precision="2" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.common.description')">
        <el-input v-model="taxForm.description"/>
      </el-form-item>
      <el-form-item :label="$t('admin.common.status')">
        <el-switch v-model="taxForm.is_active"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="taxFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
      <el-button :loading="taxSaving" type="primary" @click="submitTax">
        {{ $t('admin.common.save') }}
      </el-button>
    </template>
  </el-drawer>
</template>
