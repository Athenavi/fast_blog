<script lang="ts" setup>
/**
 * 支付配置 · 税务报表面板
 *
 * 从 `pages/commerce/payment.vue` 的「税务报表」标签页抽出：按天数与币种汇总
 * 已结算交易的税额，并列出命中的税率配置。
 *
 * 两个细节照旧保留：
 *  - 查询按钮带 `module_commerce:revenue:view` 权限码（比本页的 payment 权限更严）；
 *  - 结果为空时显示 `AdminEmpty` 而不是"没有数据"的空白。
 *
 * 加载由用户点「查询」触发，挂载时不发请求（原实现也没有 `onMounted`）。
 */
import {reactive, ref} from 'vue'

import {paymentApi, type TaxReportResult} from '@/api'

const {t} = useI18n()

const taxReportQuery = reactive({days: 30, currency: ''})
const taxReportLoading = ref(false)
const taxReport = ref<TaxReportResult | null>(null)

async function loadTaxReport(): Promise<void> {
  taxReportLoading.value = true
  try {
    taxReport.value = await paymentApi.taxReport({
      days: taxReportQuery.days,
      ...(taxReportQuery.currency.trim()
        ? {currency: taxReportQuery.currency.trim().toUpperCase()}
        : {}),
    })
  } finally {
    taxReportLoading.value = false
  }
}
</script>

<template>
  <div class="admin-card">
    <el-alert :closable="false" :title="$t('admin.commerce.payment.taxReportHint')" class="mb-3"
              show-icon type="info"/>
    <el-form :inline="true" class="admin-filter">
      <el-form-item :label="$t('admin.commerce.payment.taxReportDays')">
        <el-input-number v-model="taxReportQuery.days" :max="365" :min="1"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.currency')">
        <el-input v-model="taxReportQuery.currency" maxlength="3" placeholder="USD" style="width: 110px"/>
      </el-form-item>
      <el-form-item>
        <el-button v-auth="'module_commerce:revenue:view'" :loading="taxReportLoading" type="primary"
                   @click="loadTaxReport">
          {{ $t('admin.commerce.payment.taxReportLoad') }}
        </el-button>
      </el-form-item>
    </el-form>

    <template v-if="taxReport">
      <div class="admin-toolbar">
        <span>{{ $t('admin.commerce.payment.taxReportPeriod', {n: taxReport.period_days}) }}</span>
        <span class="admin-toolbar__spacer"/>
        <span class="tax-report-statuses">{{ taxReport.settled_statuses.join(', ') }}</span>
      </div>

      <h4 class="tax-report-heading">{{ $t('admin.commerce.payment.taxReportConfigs') }}</h4>
      <el-table :data="taxReport.tax_configs" border stripe>
        <el-table-column :label="$t('admin.commerce.payment.country')" prop="country" width="100"/>
        <el-table-column :label="$t('admin.commerce.payment.region')" min-width="120" prop="region"/>
        <el-table-column :label="$t('admin.commerce.payment.taxType')" min-width="120" prop="tax_type"/>
        <el-table-column :label="$t('admin.commerce.payment.rate')" align="right" prop="rate" width="100"/>
        <el-table-column :label="$t('admin.commerce.payment.taxReportEffectiveFrom')" min-width="170"
                         prop="effective_from"/>
        <el-table-column :label="$t('admin.commerce.payment.taxReportEffectiveTo')" min-width="170"
                         prop="effective_to"/>
      </el-table>

      <h4 class="tax-report-heading">{{ $t('admin.commerce.payment.taxReportSettled') }}</h4>
      <el-table :data="taxReport.settled_transactions" border stripe>
        <el-table-column :label="$t('admin.commerce.payment.currency')" prop="currency" width="110"/>
        <el-table-column :label="$t('admin.commerce.payment.taxReportTransactions')" prop="transactions"
                         width="140"/>
        <el-table-column :label="$t('admin.commerce.payment.amount')" align="right" prop="amount"/>
      </el-table>
    </template>
    <AdminEmpty v-else :desc="$t('admin.commerce.payment.taxReportEmptyDesc')"
                :title="$t('admin.commerce.payment.taxReportEmpty')"/>
  </div>
</template>

<style scoped>
/* 这几个类来自 styles/admin.css（全局），此处只补页面原先 scoped 覆盖的部分 */
.mb-3 {
  margin-bottom: 12px;
}

.tax-report-heading {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.tax-report-statuses {
  color: var(--el-text-color-secondary);
}
</style>
