/** 支付接口（/api/v3/commerce/payment，commerce 域）
 *
 * 四个资源：gateway / transaction / crypto / tax-config；另有发起支付与（匿名的）网关回调。
 * 网关的 `config_data` **只入不出**：响应只给 `has_config_data` 布尔位，更新时留空即保持原值。
 *
 * 另有**税务计算**子能力（与 `tax-config` CRUD 是两套东西）：
 *   - `POST /commerce/payment/tax/calculate` 税务试算（税率来自 `tax_configs` 真表）
 *   - `GET  /commerce/payment/tax/resolve`   解析适用税率（精确地区 > 国家级；未命中 404）
 *   - `GET  /commerce/payment/tax/report`    周期税务报表（税率配置 + 已结算交易汇总）
 *   calculate / resolve 需 `module_commerce:payment:view`；report 需 `module_commerce:revenue:view`。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface PaymentGatewayItem {
  id: number
  name?: string | null
  provider?: string | null
  is_active: boolean
  supported_currencies?: string | null
  has_config_data: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface PaymentGatewayQuery extends PageQuery {
  provider?: string
  is_active?: boolean
}

export interface PaymentGatewayPayload {
  name?: string
  provider?: string
  /** 仅用于写入；读取永远拿不到明文 */
  config_data?: Record<string, unknown> | null
  is_active?: boolean
  supported_currencies?: string
}

export interface PaymentTransactionItem {
  id: number
  user?: number | null
  order_id?: string | null
  gateway?: number | null
  amount?: number | null
  currency?: string | null
  status?: string | null
  transaction_id?: string | null
  payment_method?: string | null
  extra_metadata?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}

export interface PaymentTransactionQuery extends PageQuery {
  status?: string
  payment_method?: string
  currency?: string
  user?: number
  gateway?: number
}

export interface PaymentTransactionPayload {
  user?: number
  amount?: number
  gateway?: number | null
  order_id?: string | null
  currency?: string
  status?: string
  transaction_id?: string | null
  payment_method?: string | null
  extra_metadata?: Record<string, unknown> | null
}

export interface CryptoPaymentItem {
  id: number
  transaction?: number | null
  wallet_address?: string | null
  blockchain?: string | null
  token_symbol?: string | null
  tx_hash?: string | null
  confirmations: number
  required_confirmations: number
  exchange_rate?: number | null
  crypto_amount?: number | null
  status?: string | null
  expires_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface CryptoPaymentQuery extends PageQuery {
  blockchain?: string
  status?: string
  transaction?: number
}

export interface CryptoPaymentPayload {
  transaction?: number
  wallet_address?: string
  blockchain?: string
  token_symbol?: string
  tx_hash?: string | null
  confirmations?: number
  required_confirmations?: number
  exchange_rate?: number | null
  crypto_amount?: number | null
  status?: string
  expires_at?: string | null
}

export interface TaxConfigItem {
  id: number
  country?: string | null
  region?: string | null
  tax_type?: string | null
  rate?: number | null
  description?: string | null
  is_active: boolean
  effective_from?: string | null
  effective_to?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface TaxConfigQuery extends PageQuery {
  country?: string
  region?: string
  tax_type?: string
  is_active?: boolean
}

export interface TaxConfigPayload {
  country?: string
  region?: string | null
  tax_type?: string
  rate?: number
  description?: string | null
  is_active?: boolean
  effective_from?: string | null
  effective_to?: string | null
}

export interface PaymentInitiatePayload {
  order_id: string
  /** 金额单位是**元**（服务端转发插件时转成分） */
  amount: number
  subject?: string
  gateway?: number | null
  return_url?: string | null
  cancel_url?: string | null
  notify_url?: string | null
}

// ---------------------------------------------------------------- 税务计算（真实税率）
/** `POST /commerce/payment/tax/calculate` 请求体（对应后端 `TaxCalculateRequest`） */
export interface TaxCalculatePayload {
  /** 金额；`inclusive=false` 时为净额，`true` 时为含税总额 */
  amount: number
  /** ISO 3166-1 alpha-2 国家码（2 位） */
  country: string
  /** 地区 / 州 / 省 */
  region?: string | null
  /** 税种，如 VAT / GST */
  tax_type?: string | null
  /** 金额是否已含税 */
  inclusive?: boolean
  /** EU VAT 号；合法时按免税处理 */
  vat_number?: string | null
}

/** `calculate` 的响应 `data`（对应后端 `TaxService.calculate` 返回值；`net + tax = total`） */
export interface TaxCalculateResult {
  country: string
  region?: string | null
  tax_type?: string | null
  /** 实际计税税率（免税时为 0） */
  rate: number
  /** 配置表命中的税率（免税时仍回显配置值） */
  configured_rate: number
  inclusive: boolean
  exempt: boolean
  exemption_reason?: string | null
  net: number
  tax: number
  total: number
}

/** `GET /commerce/payment/tax/resolve` 查询参数（`country` 必填，2 位） */
export type TaxResolveQuery = {
  country: string
  region?: string
  tax_type?: string
}

/** `resolve` 的响应 `data`（对应后端 `TaxService.resolve_rate` 返回值） */
export interface TaxRateResult {
  id: number
  country?: string | null
  region?: string | null
  tax_type?: string | null
  rate: number
  description?: string | null
}

/** `GET /commerce/payment/tax/report` 查询参数（后端默认 `days=30`，范围 1~365） */
export type TaxReportQuery = {
  days?: number
  /** ISO 4217 货币码（3 位；缺省汇总全部币种） */
  currency?: string
}

/** 报表里的税率配置项（对应后端 `report()` 的 `tax_configs[]`） */
export interface TaxReportConfigItem {
  id: number
  country?: string | null
  region?: string | null
  tax_type?: string | null
  rate: number
  effective_from?: string | null
  effective_to?: string | null
}

/** 报表里按币种汇总的已结算交易（对应 `settled_transactions[]`） */
export interface TaxReportSettledItem {
  currency?: string | null
  transactions: number
  amount: number
}

/** `GET /commerce/payment/tax/report` 的响应 `data`（对应后端 `TaxService.report` 返回值） */
export interface TaxReportResult {
  period_days: number
  /** 计入报表的交易状态口径（后端 `SETTLED_STATUSES`） */
  settled_statuses: string[]
  tax_configs: TaxReportConfigItem[]
  settled_transactions: TaxReportSettledItem[]
}

export const paymentApi = {
  // ---- 网关 ----
  listGateways: (params?: PaymentGatewayQuery) =>
    http.page<PaymentGatewayItem>('/commerce/payment/gateway', params),

  getGateway: (id: number) => http.get<PaymentGatewayItem>(`/commerce/payment/gateway/${id}`),

  createGateway: (data: PaymentGatewayPayload) =>
    http.post<PaymentGatewayItem>('/commerce/payment/gateway', data),

  updateGateway: (id: number, data: Partial<PaymentGatewayPayload>) =>
    http.put<PaymentGatewayItem>(`/commerce/payment/gateway/${id}`, data),

  removeGateway: (id: number) => http.delete<null>(`/commerce/payment/gateway/${id}`),

  // ---- 交易 ----
  listTransactions: (params?: PaymentTransactionQuery) =>
    http.page<PaymentTransactionItem>('/commerce/payment/transaction', params),

  getTransaction: (id: number) =>
    http.get<PaymentTransactionItem>(`/commerce/payment/transaction/${id}`),

  createTransaction: (data: PaymentTransactionPayload) =>
    http.post<PaymentTransactionItem>('/commerce/payment/transaction', data),

  updateTransaction: (id: number, data: Partial<PaymentTransactionPayload>) =>
    http.put<PaymentTransactionItem>(`/commerce/payment/transaction/${id}`, data),

  removeTransaction: (id: number) => http.delete<null>(`/commerce/payment/transaction/${id}`),

  // ---- 加密货币支付 ----
  listCrypto: (params?: CryptoPaymentQuery) =>
    http.page<CryptoPaymentItem>('/commerce/payment/crypto', params),

  createCrypto: (data: CryptoPaymentPayload) =>
    http.post<CryptoPaymentItem>('/commerce/payment/crypto', data),

  updateCrypto: (id: number, data: Partial<CryptoPaymentPayload>) =>
    http.put<CryptoPaymentItem>(`/commerce/payment/crypto/${id}`, data),

  removeCrypto: (id: number) => http.delete<null>(`/commerce/payment/crypto/${id}`),

  // ---- 税务配置 ----
  listTaxConfigs: (params?: TaxConfigQuery) =>
    http.page<TaxConfigItem>('/commerce/payment/tax-config', params),

  createTaxConfig: (data: TaxConfigPayload) =>
    http.post<TaxConfigItem>('/commerce/payment/tax-config', data),

  updateTaxConfig: (id: number, data: Partial<TaxConfigPayload>) =>
    http.put<TaxConfigItem>(`/commerce/payment/tax-config/${id}`, data),

  removeTaxConfig: (id: number) => http.delete<null>(`/commerce/payment/tax-config/${id}`),

  // ---- 发起支付（委托支付插件） ----
  initiate: (data: PaymentInitiatePayload) =>
    http.post<Record<string, unknown>>('/commerce/payment/initiate', data),

  // ---- 税务计算（税率来自 tax_configs 真表） ----
  /** 试算一笔金额的税额（未配置对应税率时后端返回 404） */
  calculateTax: (data: TaxCalculatePayload) =>
    http.post<TaxCalculateResult>('/commerce/payment/tax/calculate', data),

  /** 解析当前生效税率（精确地区优先，其次国家级；未命中后端返回 404） */
  resolveTaxRate: (params: TaxResolveQuery) =>
    http.get<TaxRateResult>('/commerce/payment/tax/resolve', params),

  /** 周期税务报表（税率配置清单 + 已结算交易按币种汇总） */
  taxReport: (params?: TaxReportQuery) =>
    http.get<TaxReportResult>('/commerce/payment/tax/report', params),
}
