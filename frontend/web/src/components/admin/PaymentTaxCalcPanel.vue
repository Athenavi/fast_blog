<script lang="ts" setup>
/**
 * 支付配置 · 税务试算面板
 *
 * 从 `pages/commerce/payment.vue` 的「税务试算」标签页抽出：按金额 + 国家（可选地区 /
 * 税种 / 含税 / VAT 号）试算税额，并可先「解析税率」看看后端会取到哪条 `tax_configs`。
 *
 * 与「税务配置」面板共用同一份税率数据，但这里是只读消费方 —— 两个按钮都是手动触发，
 * 挂载时不发请求（原实现也没有 `onMounted`）。
 */
import {Search} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {paymentApi, type TaxCalculateResult, type TaxRateResult} from '@/api'
import {ElMessage} from '@/utils/feedback'

const {t} = useI18n()

const taxCalcForm = reactive({
  amount: undefined as number | undefined,
  country: '',
  region: '',
  tax_type: '',
  inclusive: false,
  vat_number: '',
})
const taxCalcSaving = ref(false)
const taxRateLoading = ref(false)
const taxCalcResult = ref<TaxCalculateResult | null>(null)
const taxRateResult = ref<TaxRateResult | null>(null)

/** 只解析税率、不计算：用来回答"这个国家/税种到底命中哪条配置" */
async function resolveTaxRate(): Promise<void> {
  if (taxCalcForm.country.trim().length !== 2) {
    ElMessage.warning(t('admin.commerce.payment.taxCalcCountryRequired'))
    return
  }
  taxRateLoading.value = true
  try {
    taxRateResult.value = await paymentApi.resolveTaxRate({
      country: taxCalcForm.country.trim().toUpperCase(),
      ...(taxCalcForm.region.trim() ? {region: taxCalcForm.region.trim()} : {}),
      ...(taxCalcForm.tax_type.trim() ? {tax_type: taxCalcForm.tax_type.trim()} : {}),
    })
  } finally {
    taxRateLoading.value = false
  }
}

async function submitTaxCalc(): Promise<void> {
  if (!taxCalcForm.amount || taxCalcForm.amount <= 0 || taxCalcForm.country.trim().length !== 2) {
    ElMessage.warning(t('admin.commerce.payment.taxCalcRequired'))
    return
  }
  taxCalcSaving.value = true
  try {
    taxCalcResult.value = await paymentApi.calculateTax({
      amount: taxCalcForm.amount,
      country: taxCalcForm.country.trim().toUpperCase(),
      region: taxCalcForm.region.trim() || null,
      tax_type: taxCalcForm.tax_type.trim() || null,
      inclusive: taxCalcForm.inclusive,
      vat_number: taxCalcForm.vat_number.trim() || null,
    })
  } finally {
    taxCalcSaving.value = false
  }
}
</script>

<template>
  <div class="admin-card tax-calc">
    <el-alert :closable="false" :title="$t('admin.commerce.payment.taxCalcHint')" class="mb-3"
              show-icon type="info"/>
    <el-form :model="taxCalcForm" label-width="150px" style="max-width: 620px">
      <el-form-item :label="$t('admin.commerce.payment.amount')" required>
        <el-input-number v-model="taxCalcForm.amount" :min="0.01" :precision="2" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.country')" required>
        <el-input v-model="taxCalcForm.country" maxlength="2" placeholder="CN"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.region')">
        <el-input v-model="taxCalcForm.region"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.taxType')">
        <el-input v-model="taxCalcForm.tax_type" placeholder="VAT / GST / Sales Tax"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.taxCalcInclusive')">
        <el-switch v-model="taxCalcForm.inclusive"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.taxCalcVat')">
        <el-input v-model="taxCalcForm.vat_number"
                  :placeholder="$t('admin.commerce.payment.taxCalcVatPlaceholder')"/>
      </el-form-item>
      <el-form-item>
        <el-button :icon="Search" :loading="taxRateLoading" @click="resolveTaxRate">
          {{ $t('admin.commerce.payment.taxCalcResolve') }}
        </el-button>
        <el-button :loading="taxCalcSaving" type="primary" @click="submitTaxCalc">
          {{ $t('admin.commerce.payment.taxCalc') }}
        </el-button>
      </el-form-item>
    </el-form>

    <el-descriptions v-if="taxRateResult" :column="3" :title="$t('admin.commerce.payment.taxCalcResolved')" border
                     class="mb-3">
      <el-descriptions-item :label="$t('admin.commerce.payment.country')">
        {{ taxRateResult.country || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.region')">
        {{ taxRateResult.region || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxType')">
        {{ taxRateResult.tax_type || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.rate')">
        {{ taxRateResult.rate }}
      </el-descriptions-item>
    </el-descriptions>

    <el-descriptions v-if="taxCalcResult" :column="3" :title="$t('admin.commerce.payment.taxCalcResult')"
                     border>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcRate')">
        {{ taxCalcResult.rate }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcConfiguredRate')">
        {{ taxCalcResult.configured_rate }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcExempt')">
        {{ taxCalcResult.exempt ? $t('admin.common.yes') : $t('admin.common.no') }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcNet')">
        {{ taxCalcResult.net }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcTax')">
        {{ taxCalcResult.tax }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcTotal')">
        {{ taxCalcResult.total }}
      </el-descriptions-item>
      <el-descriptions-item v-if="taxCalcResult.exemption_reason"
                            :label="$t('admin.commerce.payment.taxCalcExemptReason')"
                            :span="3">
        {{ taxCalcResult.exemption_reason }}
      </el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<style scoped>
/* 这两个类来自 styles/admin.css（全局），此处只补页面原先 scoped 覆盖的部分 */
.mb-3 {
  margin-bottom: 12px;
}

.tax-calc {
  padding: var(--admin-gap-lg);
}
</style>
