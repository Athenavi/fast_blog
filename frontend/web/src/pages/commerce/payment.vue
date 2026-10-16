<script lang="ts" setup>
/**
 * 支付管理（页面壳）
 *
 * 对齐 v3 `/commerce/payment`：支付网关 / 交易 / 加密支付 / 税务配置 / 税务试算 /
 * 税务报表六个标签页。
 *
 * **本文件现在只负责标签容器**：六个标签页的内容（约 1100 行）已各自拆成
 * `components/admin/Payment*Panel.vue`。留在页面上的只有 `activeTab` 一个 ref。
 *
 * 各标签页的加载时机保持原样（原页面既没有 `onMounted` 也没有 `@tab-change`）：
 * 网关 / 交易 / 加密支付 / 税务配置四个列表都由 `useAdminList` **挂载即加载**；
 * 税务试算与税务报表是**手动触发**，挂载不发请求。
 *
 * 迁移时一并搬进各组件的领域知识：
 *  - 网关的 `config_data` **只入不出** —— 响应只有 `has_config_data`，编辑时留空即保持原值；
 *  - 「发起支付」走 `/commerce/payment/initiate`，由 payment-gateway 插件执行
 *    （金额按**元**填写，服务端转发插件时转成分）；
 *  - 税务试算 `tax/calculate`（税率来自 `tax_configs` 真表）与 `tax/resolve`，
 *    和 `tax-config` 的 CRUD 是两套东西；
 *  - 税务报表 `tax/report` 需要更严的权限 `module_commerce:revenue:view`。
 */
import {ref} from 'vue'

import PaymentCryptoPanel from '@/components/admin/PaymentCryptoPanel.vue'
import PaymentGatewayPanel from '@/components/admin/PaymentGatewayPanel.vue'
import PaymentTaxCalcPanel from '@/components/admin/PaymentTaxCalcPanel.vue'
import PaymentTaxConfigPanel from '@/components/admin/PaymentTaxConfigPanel.vue'
import PaymentTaxReportPanel from '@/components/admin/PaymentTaxReportPanel.vue'
import PaymentTransactionPanel from '@/components/admin/PaymentTransactionPanel.vue'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.commerce.payment.title',
  permission: 'module_commerce:payment:view',
})

const activeTab = ref('gateway')


// 支付网关整块搬进了 `PaymentGatewayPanel` —— 连它工具栏上的「发起支付」（联调用）
// 一起搬走了，因为那个按钮本来就在本标签页里，没必要让页面替它保管三个 ref。

// 交易整块搬进了 `PaymentTransactionPanel` —— 连"状态 → el-tag 类型"的映射
// （`STATUS_TAG` / `statusTag`）一起，因为全仓只有那个面板的表格用它。

// 加密支付整块搬进了 `PaymentCryptoPanel`。

// 税务三块各自搬进了组件：配置 → `PaymentTaxConfigPanel`、
// 试算 → `PaymentTaxCalcPanel`、报表 → `PaymentTaxReportPanel`。
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 支付网关 -->
      <el-tab-pane :label="$t('admin.commerce.payment.gateways')" name="gateway">
        <PaymentGatewayPanel/>
      </el-tab-pane>

      <!-- 交易 -->
      <el-tab-pane :label="$t('admin.commerce.payment.transactions')" name="transaction">
        <PaymentTransactionPanel/>
      </el-tab-pane>

      <!-- 加密支付 -->
      <el-tab-pane :label="$t('admin.commerce.payment.crypto')" name="crypto">
        <PaymentCryptoPanel/>
      </el-tab-pane>

      <!-- 税务配置 -->
      <el-tab-pane :label="$t('admin.commerce.payment.taxConfigs')" name="tax">
        <PaymentTaxConfigPanel/>
      </el-tab-pane>

      <!-- 税务试算 -->
      <el-tab-pane :label="$t('admin.commerce.payment.taxCalc')" name="taxCalc">
        <PaymentTaxCalcPanel/>
      </el-tab-pane>

      <!-- 税务报表 -->
      <el-tab-pane :label="$t('admin.commerce.payment.taxReport')" name="taxReport">
        <PaymentTaxReportPanel/>
      </el-tab-pane>
    </el-tabs>

  </div>
</template>
