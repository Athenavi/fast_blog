# commerce/shop 前端接线报告

对接后端 v3 模块 `src/api/v3/modules/commerce/shop`（商品 / 购物车 / 订单），
产出全部位于 `frontend/web/.gen/commerce_shop/`：

- `api/shop.ts` —— `shopApi` + 全部 interface/type（合并目标 `src/api/modules/shop.ts`）
- `pages/shop-products.vue`（合并目标 `src/pages/commerce/shop-products.vue`）
- `pages/shop-orders.vue`（合并目标 `src/pages/commerce/shop-orders.vue`）
- `i18n.json` —— 仅新增键（zh-CN / en 对称）

---

## ① 端点 → 函数 → 页面位置映射

| #  | 方法与路径                                             | shopApi 函数       | 页面位置                                                  | 权限码                              |
|----|---------------------------------------------------|------------------|-------------------------------------------------------|----------------------------------|
| 1  | `GET /commerce/shop/products`                     | `listProducts`   | `shop-products.vue` 商品列表主表（关键词 / 上架筛选 + 分页）           | `module_commerce:payment:view`   |
| 2  | `POST /commerce/shop/products`                    | `createProduct`  | `shop-products.vue` 新建抽屉 `submitProduct`              | `module_commerce:payment:create` |
| 3  | `GET /commerce/shop/products/{product_id}`        | `getProduct`     | 已封装；管理端未直接调用（见 ③）                                     | `module_commerce:payment:view`   |
| 4  | `PUT /commerce/shop/products/{product_id}`        | `updateProduct`  | `shop-products.vue` 编辑抽屉 `submitProduct`              | `module_commerce:payment:edit`   |
| 5  | `DELETE /commerce/shop/products/{product_id}`     | `removeProduct`  | `shop-products.vue` 行内删除 `onDeleteProduct`            | `module_commerce:payment:delete` |
| 6  | `POST /commerce/shop/products/{product_id}/stock` | `adjustStock`    | `shop-products.vue` 库存调整对话框 `submitStock`             | `module_commerce:payment:edit`   |
| 7  | `GET /commerce/shop/products/low-stock`           | `lowStock`       | `shop-products.vue` 低库存看板 `loadLowStock`              | `module_commerce:payment:view`   |
| 8  | `GET /commerce/shop/cart`                         | `getCart`        | 已封装；前台购物车流程，非管理端页面（见 ③）                               | 仅需登录                             |
| 9  | `POST /commerce/shop/cart/items`                  | `addCartItem`    | 同上                                                    | 仅需登录                             |
| 10 | `PUT /commerce/shop/cart/items/{item_id}`         | `updateCartItem` | 同上                                                    | 仅需登录                             |
| 11 | `DELETE /commerce/shop/cart/items/{item_id}`      | `removeCartItem` | 同上                                                    | 仅需登录                             |
| 12 | `DELETE /commerce/shop/cart`                      | `clearCart`      | 同上                                                    | 仅需登录                             |
| 13 | `POST /commerce/shop/orders`                      | `createOrder`    | 已封装；下单属前台流程（见 ③）                                      | 仅需登录                             |
| 14 | `GET /commerce/shop/orders`                       | `listOrders`     | `shop-orders.vue` 订单列表主表（状态 / 用户筛选 + 分页）              | `module_commerce:payment:view`   |
| 15 | `GET /commerce/shop/orders/stats`                 | `orderStats`     | `shop-orders.vue` 统计卡片 `loadStats`                    | `module_commerce:payment:view`   |
| 16 | `GET /commerce/shop/orders/{order_id}`            | `getOrder`       | `shop-orders.vue` 订单详情抽屉 `openDetail`                 | `module_commerce:payment:view`   |
| 17 | `POST /commerce/shop/orders/{order_id}/pay`       | `markPaid`       | `shop-orders.vue` 行内「标记支付」→ `submitAction`            | `module_commerce:payment:edit`   |
| 18 | `POST /commerce/shop/orders/{order_id}/ship`      | `markShipped`    | `shop-orders.vue` 行内「发货」→ `submitAction`              | `module_commerce:payment:edit`   |
| 19 | `POST /commerce/shop/orders/{order_id}/deliver`   | `markDelivered`  | `shop-orders.vue` 行内「收货」→ `submitAction`              | `module_commerce:payment:edit`   |
| 20 | `POST /commerce/shop/orders/{order_id}/cancel`    | `cancelOrder`    | `shop-orders.vue` 行内「取消」→ `submitAction`（带二次确认）       | `module_commerce:payment:edit`   |
| 21 | `POST /commerce/shop/orders/{order_id}/refund`    | `refundOrder`    | `shop-orders.vue` 行内「退款」→ `submitAction`（原因 + 回滚库存开关） | `module_commerce:revenue:edit`   |

共 21 个「方法 × 路径」组合（对应 controller 全量路由）。`/list`、`/detail/{id}` 等别名未接。

权限码字符串（取自 `src/api/v3/core/permission/codes.py:247-254`）：

- `PAYMENT_VIEW` = `module_commerce:payment:view`
- `PAYMENT_CREATE` = `module_commerce:payment:create`
- `PAYMENT_EDIT` = `module_commerce:payment:edit`
- `PAYMENT_DELETE` = `module_commerce:payment:delete`
- `REVENUE_EDIT` = `module_commerce:revenue:edit`

`definePageMeta.permission` 两页均为 `module_commerce:payment:view`；按钮级权限用 `v-auth`。

---

## ② 字段来源逐条对照

所有金额字段单位是「**元**」（`service.ShopService._money` 将 `str(value)` 量化到分后返回 `float`），
与 `tipping` 的「分」不同 —— 页面直接交给 `formatMoney`，不再做 `/100`。

### ProductItem（`service._product_out`）

| 前端字段                                        | 后端字段                                            | 说明                    |
|---------------------------------------------|-------------------------------------------------|-----------------------|
| `id` / `name` / `slug`                      | `row.id` / `row.name` / `row.slug`              | —                     |
| `price`                                     | `float(_money(row.price))`                      | 现价（元）                 |
| `original_price`                            | 有值才 `float(_money(...))`，否则 `null`              | 无原价返回 `null`，与 `0` 不同 |
| `stock`                                     | `int(row.stock or 0)`                           | 库存；`0` = 售罄           |
| `sku` / `category_id`                       | `row.sku` / `row.category_id`                   | —                     |
| `is_active` / `is_featured`                 | `bool(row.is_active)` / `bool(row.is_featured)` | —                     |
| `description` / `created_at` / `updated_at` | 同名                                              | —                     |

`ProductCreatePayload` 对应 `schema.ProductCreate`（`name`/`price` 必填，`stock` 默认 0）。
`ProductUpdatePayload` 对应 `schema.ProductUpdate`（**无 `original_price`**）。
`StockAdjustResult` 对应 `adjust_stock` 返回体 `{product_id, name, stock}`。

### LowStockItem / LowStockResult（`service.low_stock`）

`{threshold, items:[{id, name, sku, stock}]}`；仅取在售且 `stock <= threshold`，默认阈值 5、上限 50 条。

### CartLineItem / CartResult（`service._cart_out`）

`items[] = {id, product_id, name, unit_price, quantity, subtotal, stock, available}`；
外层 `{cart_id, user_id, session_id, items, total, count}`。
`name` 在商品被删时为 `null`；`available` = 商品存在且上架。

### OrderItem（`service._order_out`）

`id` / `order_number` / `user_id` / `status` / `payment_status` / `total_amount` /
`shipping_amount` / `discount_amount` / `payment_method` / `transaction_id` /
`shipping_address` / `notes` / `created_at` / `paid_at` / `shipped_at` / `delivered_at`，
逐项与后端同名。`total_amount` 单位元 = 商品合计 + 运费 − 优惠。

### OrderDetail（`service.get_order`）

`OrderItem` 全部字段 + `items[] = {id, product_id, product_name, quantity, unit_price, total_price}`。

### OrderStats（`service.order_stats`）

`{period_days, total_orders, by_status: Record<string, number>, settled_amount}`。
`by_status` 键是订单状态字符串；`settled_amount` = `status ∈ {paid, shipped, delivered}` 的 `total_amount` 之和。

### 请求体字段

- `OrderCreatePayload` ← `schema.OrderCreateRequest`
- `OrderPaidPayload` ← `schema.OrderPaidRequest`
- `OrderRefundPayload` ← `schema.OrderRefundRequest`
- `CartAddPayload` ← `schema.CartAddRequest`

`OrderQuery.status` 对应 controller 的 `Query(alias="status")`；`user_id` 对应同名查询参数。

---

## ③ 未接线及原因

| 端点                                                               | 状态                                                                               | 原因                                                                                     |
|------------------------------------------------------------------|----------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| `GET /products/{product_id}`                                     | 已封装 `getProduct`，页面未调用                                                           | 管理端列表接口 `listProducts` 已返回完整字段，编辑直接吃行数据，无需再拉详情                                         |
| `GET/POST /cart`、`/cart/items`、`/cart/items/{id}`、`DELETE /cart` | 已封装（`getCart`/`addCartItem`/`updateCartItem`/`removeCartItem`/`clearCart`），页面未承载 | 购物车是**前台普通用户**流程（controller 仅 `CurrentUser`，无 `AuthControl`），不属于本批「管理端列表页」范式；本批只交付后台两页 |
| `POST /orders`（下单）                                               | 已封装 `createOrder`，页面未承载                                                          | 同上，下单属前台流程；管理端只读订单                                                                     |

以上函数均已按契约完整实现，待需要时可直接在前台页面调用，无需再改 `api/shop.ts`。

---

## ④ 存疑项

1. **币种**：商品表 / 订单表均**无 `currency` 字段**，后端金额只给数值。页面用 `formatMoney(value)`
   默认走 `DEFAULT_CURRENCY`（`utils/money.ts` 中为 `'USD'`）。若商城实际以人民币计价，需
   改为传入 `'CNY'`（或待后端补 `currency` 字段）。**未编造币种**，仅沿用既有默认。
2. **`original_price` 不可更新**：`schema.ProductUpdate` 无该字段，故编辑抽屉在「编辑」态隐藏原价输入，
   更新请求也不下发 `original_price`（保持原值）。新建态可填。
3. **退款按钮可见条件**：后端 `refund_order` 以 `order.payment_status === 'paid'` 为前置。页面按
   `status ∈ {paid, shipped, delivered}` 展示退款按钮（与该前置等价），未直接读 `payment_status`。
4. **`by_status` 动态键**：状态枚举取自 `service.ORDER_STATUSES`，页面 `STATUS_ORDER` 与之对齐；
   若后端新增状态，统计卡片需同步。
5. **`user_id` 筛选**：用 `el-input-number`（整数）。后端 `Query(int)` 可解析，空值不下发。
6. **删除语义**：`DELETE /products/{id}` 在有订单引用时后端改为**下架**而非物理删除，页面提示文案已说明。

---

## ⑤ 未经编译验证声明

本批产出**未经 `vue-tsc` / `nuxt build` 编译验证**（子代理无 shell 权限）。已做的人工核对：

- 页面每个标识符均来自显式 `import` 或 Nuxt 自动导入（`AdminPage` / `AdminListShell` /
  `AdminFormDrawer` / `AdminEmpty` / `useI18n` / `definePageMeta`）；
- `import {...} from '@/api'` 仅导入合并后将存在的 `shopApi` 与已存在类型（`index.ts` 现无冲突名）；
- 未使用 `as` 断言掩盖类型错误；模板中对 `el-table` scope `row`(any) 的 `as XxxItem` 为既有约定
  （与 `payment.vue` 一致）；
- `http.get` 的动态参数以字面量传入（`{threshold, limit}` 等），避免 interface 缺 index signature 的类型不兼容；
- i18n 键两语言完全对称，行尾 LF；接口返回的 `null` 与 `0` 在展示上分别处理（`original_price`、`stock`）。

父代理合并后**必须跑一次**：`pnpm -C frontend/web typecheck`（或 `nuxt build`）确认无编译错误。

---

## ⑥ 需父代理在 `src/api/index.ts` 追加的 re-export 代码块

放在文件末尾（commerce 相关分节旁即可）：

```ts
// ---------------------------------------------------------------- 批次 19（commerce 商城：商品 / 购物车 / 订单）
export {shopApi} from './modules/shop'
export type {
  CartAddPayload,
  CartLineItem,
  CartResult,
  LowStockItem,
  LowStockResult,
  OrderCreatePayload,
  OrderDetail,
  OrderItem,
  OrderItemRequest,
  OrderLineItem,
  OrderPaidPayload,
  OrderQuery,
  OrderRefundPayload,
  OrderStats,
  OrderStatus,
  ProductCreatePayload,
  ProductItem,
  ProductQuery,
  ProductUpdatePayload,
  StockAdjustResult,
} from './modules/shop'
```

---

## 菜单项建议（`utils/menus.ts` 的 `Commerce.children`）

在现有 `Commerce`（`name: 'Commerce'`）的 `children` 中追加：

```ts
{name: 'ShopProducts', path: '/commerce/shop/products', title: '商品管理', permission: 'module_commerce:payment:view'},
{name: 'ShopOrders', path: '/commerce/shop/orders', title: '订单管理', permission: 'module_commerce:payment:view'},
```

对应 i18n 菜单键（已含在 `i18n.json`）：`menu.ShopProducts`、`menu.ShopOrders`。

## 合并清单

| 产物                        | 目标路径                                                       |
|---------------------------|------------------------------------------------------------|
| `api/shop.ts`             | `frontend/web/src/api/modules/shop.ts`                     |
| `pages/shop-products.vue` | `frontend/web/src/pages/commerce/shop-products.vue`        |
| `pages/shop-orders.vue`   | `frontend/web/src/pages/commerce/shop-orders.vue`          |
| `i18n.json` 的键            | 合并进 `frontend/web/i18n/locales/zh-CN.json` 与 `.../en.json` |
| `index.ts` re-export      | 见 ⑥                                                        |
| 菜单项                       | 见上（`utils/menus.ts`）                                       |
