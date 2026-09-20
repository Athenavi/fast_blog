/** 支付接口（/api/v3/commerce/payment，commerce 域）
 *
 * 四个资源：gateway / transaction / crypto / tax-config；另有发起支付与（匿名的）网关回调。
 * 网关的 `config_data` **只入不出**：响应只给 `has_config_data` 布尔位，更新时留空即保持原值。
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
}
