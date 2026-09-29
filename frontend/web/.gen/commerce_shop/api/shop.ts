/** 商城接口（`/api/v3/commerce/shop`，commerce 域）
 *
 * 三个资源：商品 products / 购物车 cart / 订单 orders（对齐 v3 `commerce/shop` 路由）。
 * 权限码**不新增**：商品与订单读写复用 `payment:view|create|edit|delete`，
 * 退款走 `revenue:edit`；购物车与下单仅需登录（普通用户即可），管理端订单列表
 * 由后端按当前用户 `data_scope` 过滤。
 *
 * **金额字段（`price` / `original_price` / `total_amount` / `unit_price` / `subtotal` …）
 * 单位统一是「元」**（service._money 量化到分后的浮点数），与 tipping 的「分」不同——
 * 展示时**不要再除以 100**。
 *
 * 字段来源均标注到本次对接的 service 输出：`_product_out` / `_cart_out` / `_order_out` /
 * `get_order.items` / `low_stock` / `order_stats`。
 */

import http from '../request'
import type {PageQuery} from '../types'

// ---------------------------------------------------------------- 商品

/** 商品行（来源：`ShopService._product_out`） */
export interface ProductItem {
  id: number
  name: string
  slug?: string | null
  /** 现价（元） */
  price: number
  /** 划线原价（元）；无原价时后端返回 `null`，与 `0` 含义不同 */
  original_price?: number | null
  /** 库存；`0` 表示售罄（后端 `stock` 非空，`_product_out` 用 `int(row.stock or 0)`） */
  stock: number
  sku?: string | null
  category_id?: number | null
  is_active: boolean
  is_featured: boolean
  description?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** 商品列表查询（来源：`list_products` 的 `keyword` / `is_active` + 分页） */
export interface ProductQuery extends PageQuery {
  /** 关键词，匹配 name 或 sku */
  keyword?: string
  /** 是否上架；`undefined` 表示不限 */
  is_active?: boolean
}

/** 新建商品（来源：`ProductCreate`；`name` 必填，其余可选） */
export interface ProductCreatePayload {
  name: string
  slug?: string | null
  description?: string | null
  price: number
  original_price?: number | null
  stock?: number
  sku?: string | null
  category_id?: number | null
  is_active?: boolean
  is_featured?: boolean
}

/** 更新商品（来源：`ProductUpdate`；**不含 `original_price`**——后端更新不入该字段） */
export interface ProductUpdatePayload {
  name?: string | null
  slug?: string | null
  description?: string | null
  price?: number | null
  stock?: number | null
  sku?: string | null
  category_id?: number | null
  is_active?: boolean | null
  is_featured?: boolean | null
}

/** 库存增减结果（来源：`adjust_stock` 返回体） */
export interface StockAdjustResult {
  product_id: number
  name: string
  stock: number
}

/** 低库存行（来源：`low_stock` → `items[]`） */
export interface LowStockItem {
  id: number
  name: string
  sku?: string | null
  stock: number
}

/** 低库存结果（来源：`low_stock` 返回体） */
export interface LowStockResult {
  threshold: number
  items: LowStockItem[]
}

// ---------------------------------------------------------------- 购物车

/** 购物车明细行（来源：`_cart_out` → `items[]`） */
export interface CartLineItem {
  /** 购物车项 id（`cart_items.id`），用于改数量 / 移除 */
  id: number
  product_id: number
  /** 商品名；商品被删时为 `null` */
  name?: string | null
  /** 单价（元） */
  unit_price: number
  quantity: number
  /** 小计（元） */
  subtotal: number
  /** 该商品当前库存 */
  stock: number
  /** 商品是否可购（存在且上架） */
  available: boolean
}

/** 购物车（来源：`_cart_out` 返回体；view / add / update / remove / clear 全部返回此结构） */
export interface CartResult {
  cart_id: number
  user_id?: number | null
  session_id?: string | null
  items: CartLineItem[]
  /** 合计（元） */
  total: number
  /** 商品件数合计（`sum(quantity)`） */
  count: number
}

/** 加入购物车（来源：`CartAddRequest`） */
export interface CartAddPayload {
  product_id: number
  quantity?: number
}

// ---------------------------------------------------------------- 订单

export type OrderStatus =
  | 'pending'
  | 'paid'
  | 'shipped'
  | 'delivered'
  | 'cancelled'
  | 'refunded'

/** 订单主行（来源：`_order_out`） */
export interface OrderItem {
  id: number
  order_number: string
  user_id?: number | null
  status: OrderStatus | string
  payment_status?: string | null
  /** 订单总额（元）= 商品合计 + 运费 − 优惠 */
  total_amount: number
  /** 运费（元） */
  shipping_amount: number
  /** 优惠（元） */
  discount_amount: number
  payment_method?: string | null
  transaction_id?: string | null
  shipping_address?: string | null
  notes?: string | null
  created_at?: string | null
  paid_at?: string | null
  shipped_at?: string | null
  delivered_at?: string | null
}

/** 订单明细行（来源：`get_order` → `items[]`） */
export interface OrderLineItem {
  id: number
  product_id: number
  product_name?: string | null
  quantity: number
  /** 下单时单价（元） */
  unit_price: number
  /** 行小计（元） */
  total_price: number
}

/** 订单详情（来源：`get_order`：订单主行 + `items` 明细） */
export interface OrderDetail extends OrderItem {
  items: OrderLineItem[]
}

/** 订单列表查询（来源：`list_orders` 的 `status` / `user_id` + 分页） */
export interface OrderQuery extends PageQuery {
  /** 订单状态；对应后端 query 别名 `status` */
  status?: string
  /** 按用户过滤 */
  user_id?: number
}

/** 下单明细项（来源：`OrderItemRequest`） */
export interface OrderItemRequest {
  product_id: number
  quantity?: number
}

/** 下单请求（来源：`OrderCreateRequest`） */
export interface OrderCreatePayload {
  /** true=结算购物车（需登录或带 session_id），false/缺省=用 items 直接下单 */
  from_cart?: boolean
  /** 直接下单的商品明细 */
  items?: OrderItemRequest[]
  /** 匿名购物车会话 ID */
  session_id?: string | null
  shipping_amount?: number
  discount_amount?: number
  payment_method?: string | null
  shipping_address?: string | null
  billing_address?: string | null
  notes?: string | null
}

/** 标记已支付（来源：`OrderPaidRequest`） */
export interface OrderPaidPayload {
  transaction_id?: string | null
}

/** 退款（来源：`OrderRefundRequest`） */
export interface OrderRefundPayload {
  /** 退货退款时同时回滚库存 */
  restore_stock?: boolean
  reason?: string | null
}

/** 订单统计（来源：`order_stats` 返回体） */
export interface OrderStats {
  period_days: number
  total_orders: number
  /** 各状态计数，键为订单状态字符串 */
  by_status: Record<string, number>
  /** 已结算金额（元）；已结算状态 = paid / shipped / delivered */
  settled_amount: number
}

// ---------------------------------------------------------------- 接口
export const shopApi = {
  // ---- 商品 / 库存 ----
  /** 商品列表（分页；权限 payment:view） */
  listProducts: (params?: ProductQuery) =>
    http.page<ProductItem>('/commerce/shop/products', params),

  /** 商品详情（权限 payment:view） */
  getProduct: (id: number) => http.get<ProductItem>(`/commerce/shop/products/${id}`),

  /** 新建商品（权限 payment:create） */
  createProduct: (data: ProductCreatePayload) =>
    http.post<ProductItem>('/commerce/shop/products', data),

  /** 更新商品（权限 payment:edit） */
  updateProduct: (id: number, data: ProductUpdatePayload) =>
    http.put<ProductItem>(`/commerce/shop/products/${id}`, data),

  /** 删除商品：有订单引用时后端改为下架而非物理删除（权限 payment:delete） */
  removeProduct: (id: number) => http.delete<null>(`/commerce/shop/products/${id}`),

  /** 库存增减：`delta` 正数入库、负数出库，扣到负数会被拒绝（权限 payment:edit） */
  adjustStock: (id: number, delta: number) =>
    http.post<StockAdjustResult>(`/commerce/shop/products/${id}/stock`, {delta}),

  /** 低库存 / 售罄商品（权限 payment:view）；默认阈值 5、最多 50 条 */
  lowStock: (threshold = 5, limit = 50) =>
    http.get<LowStockResult>('/commerce/shop/products/low-stock', {threshold, limit}),

  // ---- 购物车（登录用户；也支持匿名 session_id） ----
  /** 查看购物车；未登录时传 `sessionId` */
  getCart: (sessionId?: string) =>
    http.get<CartResult>('/commerce/shop/cart', sessionId ? {session_id: sessionId} : undefined),

  /** 加入购物车（同商品累加；库存不足直接拒绝） */
  addCartItem: (data: CartAddPayload, sessionId?: string) =>
    http.post<CartResult>(
      '/commerce/shop/cart/items',
      data,
      sessionId ? {session_id: sessionId} : undefined,
    ),

  /** 修改购物车项数量 */
  updateCartItem: (itemId: number, quantity: number, sessionId?: string) =>
    http.put<CartResult>(
      `/commerce/shop/cart/items/${itemId}`,
      {quantity},
      sessionId ? {session_id: sessionId} : undefined,
    ),

  /** 移除购物车项 */
  removeCartItem: (itemId: number, sessionId?: string) =>
    http.delete<CartResult>(
      `/commerce/shop/cart/items/${itemId}`,
      sessionId ? {session_id: sessionId} : undefined,
    ),

  /** 清空购物车 */
  clearCart: (sessionId?: string) =>
    http.delete<CartResult>('/commerce/shop/cart', sessionId ? {session_id: sessionId} : undefined),

  // ---- 订单 ----
  /** 订单列表（分页；后端按 data_scope 过滤，权限 payment:view） */
  listOrders: (params?: OrderQuery) => http.page<OrderItem>('/commerce/shop/orders', params),

  /** 订单详情（含明细；权限 payment:view） */
  getOrder: (id: number) => http.get<OrderDetail>(`/commerce/shop/orders/${id}`),

  /** 下单：真实扣减库存；`from_cart=true` 结算购物车 */
  createOrder: (data: OrderCreatePayload) => http.post<OrderDetail>('/commerce/shop/orders', data),

  /** 订单统计（权限 payment:view）；`days` 统计窗口，默认 30，范围 1–365 */
  orderStats: (days = 30) => http.get<OrderStats>('/commerce/shop/orders/stats', {days}),

  /** 标记已支付（权限 payment:edit）；可带第三方流水号 */
  markPaid: (id: number, transactionId?: string) =>
    http.post<OrderDetail>(`/commerce/shop/orders/${id}/pay`, {
      transaction_id: transactionId ?? null,
    }),

  /** 标记发货（权限 payment:edit） */
  markShipped: (id: number) => http.post<OrderDetail>(`/commerce/shop/orders/${id}/ship`),

  /** 标记收货（权限 payment:edit） */
  markDelivered: (id: number) => http.post<OrderDetail>(`/commerce/shop/orders/${id}/deliver`),

  /** 取消订单并回滚库存（仅未发货订单；权限 payment:edit） */
  cancelOrder: (id: number) => http.post<OrderDetail>(`/commerce/shop/orders/${id}/cancel`),

  /** 退款（权限 revenue:edit）；可选回滚库存 */
  refundOrder: (id: number, data?: OrderRefundPayload) =>
    http.post<OrderDetail>(`/commerce/shop/orders/${id}/refund`, data ?? {}),
}
