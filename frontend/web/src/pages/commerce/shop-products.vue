<script lang="ts" setup>
/**
 * 商品与库存管理（后台独立页，`/commerce/shop/products`）
 *
 * 数据源：v3 `/api/v3/commerce/shop`
 *  - 商品列表 `listProducts`（关键词 / 上架状态筛选，分页）
 *  - 新建 / 更新 / 删除商品（删除时有订单引用由后端改为下架）
 *  - 库存增减 `adjustStock`（`delta` 正负均可，扣成负数被拒）
 *  - 低库存看板 `lowStock`（含售罄；阈值可调）
 *
 * 权限复用 `payment:view|create|edit|delete`。金额单位是「元」，库存 `0` 即售罄。
 */
import {Delete, EditPen, Plus, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'
import {formatMoney} from '@/utils/money'
import {onMounted, reactive, ref} from 'vue'

import {type LowStockResult, type ProductItem, type ProductQuery, shopApi} from '@/api'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.commerce.shop.productsTitle',
  permission: 'module_commerce:payment:view',
})

const {t} = useI18n()

// ---------------------------------------------------------------- 商品列表
const productState = useAdminList<ProductItem, ProductQuery>({
  fetcher: (params) => shopApi.listProducts(params),
  defaultQuery: {keyword: '', is_active: undefined},
  syncUrl: true,
})

const products = productState.rows
const productLoading = productState.loading
const productFailed = productState.failed
const productTotal = productState.total
const productPage = productState.page
const productPageSize = productState.pageSize
const productQuery = productState.query
const productSearch = productState.search
const productReset = productState.reset
const productReload = productState.reload
const onProductPageChange = productState.onPageChange
const onProductSizeChange = productState.onSizeChange

// ---------------------------------------------------------------- 低库存看板
const lowStock = ref<LowStockResult | null>(null)
const lowStockLoading = ref(false)
const lowStockThreshold = ref(5)

async function loadLowStock(): Promise<void> {
  lowStockLoading.value = true
  try {
    lowStock.value = await shopApi.lowStock(lowStockThreshold.value, 50)
  } finally {
    lowStockLoading.value = false
  }
}

// ---------------------------------------------------------------- 商品表单
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  name: '',
  slug: '',
  description: '',
  price: undefined as number | undefined,
  original_price: undefined as number | undefined,
  stock: 0,
  sku: '',
  category_id: undefined as number | undefined,
  is_active: true,
  is_featured: false,
})

function resetForm(): void {
  Object.assign(form, {
    name: '',
    slug: '',
    description: '',
    price: undefined,
    original_price: undefined,
    stock: 0,
    sku: '',
    category_id: undefined,
    is_active: true,
    is_featured: false,
  })
}

function openCreate(): void {
  editingId.value = null
  resetForm()
  formVisible.value = true
}

function openEdit(row: ProductItem): void {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    slug: row.slug || '',
    description: row.description || '',
    price: row.price,
    original_price: row.original_price ?? undefined,
    stock: row.stock,
    sku: row.sku || '',
    category_id: row.category_id ?? undefined,
    is_active: row.is_active,
    is_featured: row.is_featured,
  })
  formVisible.value = true
}

async function submitProduct(): Promise<void> {
  if (!form.name.trim() || form.price === undefined) {
    ElMessage.warning(t('admin.commerce.shop.productRequired'))
    return
  }
  saving.value = true
  try {
    const base = {
      name: form.name.trim(),
      slug: form.slug.trim() || null,
      description: form.description.trim() || null,
      price: form.price,
      stock: form.stock,
      sku: form.sku.trim() || null,
      category_id: form.category_id ?? null,
      is_active: form.is_active,
      is_featured: form.is_featured,
    }
    if (editingId.value) {
      // 更新接口不接受 original_price，故不下发该字段（保持原值）
      await shopApi.updateProduct(editingId.value, base)
    } else {
      await shopApi.createProduct({...base, original_price: form.original_price ?? null})
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await productReload()
  } finally {
    saving.value = false
  }
}

async function onDeleteProduct(row: ProductItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.commerce.shop.deleteProductConfirm', {name: row.name}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await shopApi.removeProduct(row.id)
  ElMessage.success(t('admin.common.delete'))
  await productReload()
}

// ---------------------------------------------------------------- 库存调整
const stockVisible = ref(false)
const stockSaving = ref(false)
const stockTarget = ref<ProductItem | null>(null)
const stockForm = reactive({delta: 0})

function openStock(row: ProductItem): void {
  stockTarget.value = row
  stockForm.delta = 0
  stockVisible.value = true
}

async function submitStock(): Promise<void> {
  if (!stockTarget.value) return
  if (!stockForm.delta) {
    ElMessage.warning(t('admin.commerce.shop.stockRequired'))
    return
  }
  stockSaving.value = true
  try {
    const result = await shopApi.adjustStock(stockTarget.value.id, stockForm.delta)
    ElMessage.success(t('admin.commerce.shop.stockAdjusted', {stock: result.stock}))
    stockVisible.value = false
    await Promise.all([productReload(), loadLowStock()])
  } finally {
    stockSaving.value = false
  }
}

onMounted(loadLowStock)
</script>

<template>
  <AdminPage
    :desc="$t('admin.commerce.shop.productsDesc')"
    :title="$t('admin.commerce.shop.productsTitle')"
  >
    <template #actions>
      <el-button
        v-auth="'module_commerce:payment:create'"
        :icon="Plus"
        type="primary"
        @click="openCreate"
      >
        {{ $t('admin.commerce.shop.createProduct') }}
      </el-button>
    </template>

    <!-- 低库存 / 售罄看板 -->
    <el-card class="mb-4" shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>{{ $t('admin.commerce.shop.lowStockTitle') }}</span>
          <div class="flex items-center gap-2">
            <el-input-number
              v-model="lowStockThreshold"
              :max="1000"
              :min="0"
              controls-position="right"
              size="small"
              style="width: 120px"
            />
            <el-button
              :icon="Refresh"
              :loading="lowStockLoading"
              size="small"
              @click="loadLowStock()"
            >
              {{ $t('admin.common.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <p class="mb-2 text-xs text-fg-muted">{{ $t('admin.commerce.shop.lowStockHint') }}</p>

      <AdminEmpty
        v-if="!lowStockLoading && !(lowStock?.items?.length)"
        :title="$t('admin.commerce.shop.lowStockEmpty')"
      />
      <el-table v-else v-loading="lowStockLoading" :data="lowStock?.items ?? []" border stripe>
        <el-table-column
          :label="$t('admin.common.name')"
          min-width="160"
          prop="name"
          show-overflow-tooltip
        />
        <el-table-column :label="$t('admin.commerce.shop.sku')" min-width="120" prop="sku"/>
        <el-table-column :label="$t('admin.commerce.shop.stock')" align="center" width="110">
          <template #default="{ row }">
            <el-tag :type="row.stock <= 0 ? 'danger' : 'warning'" size="small">{{ row.stock }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 商品列表 -->
    <AdminListShell
      :failed="productFailed"
      :loading="productLoading"
      :page="productPage"
      :page-size="productPageSize"
      :rows="products"
      :selectable="false"
      :total="productTotal"
      @refresh="productReload"
      @reset="productReset"
      @search="productSearch"
      @page-change="onProductPageChange"
      @size-change="onProductSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.commerce.shop.keyword')">
          <el-input
            v-model="productQuery.keyword"
            clearable
            style="width: 200px"
            @keyup.enter="productSearch()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select
            v-model="productQuery.is_active"
            :placeholder="$t('admin.common.all')"
            clearable
            style="width: 140px"
            @change="productSearch()"
          >
            <el-option :label="$t('admin.common.enabled')" :value="true"/>
            <el-option :label="$t('admin.common.disabled')" :value="false"/>
          </el-select>
        </el-form-item>
      </template>

      <el-table-column
        :label="$t('admin.common.name')"
        min-width="180"
        prop="name"
        show-overflow-tooltip
      />
      <el-table-column
        :label="$t('admin.commerce.shop.sku')"
        min-width="120"
        prop="sku"
        show-overflow-tooltip
      />
      <el-table-column :label="$t('admin.commerce.shop.price')" align="right" width="120">
        <template #default="{ row }">{{ formatMoney((row as ProductItem).price) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.commerce.shop.originalPrice')" align="right" width="120">
        <template #default="{ row }">{{ formatMoney((row as ProductItem).original_price) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.commerce.shop.stock')" align="center" width="110">
        <template #default="{ row }">
          <el-tag v-if="(row as ProductItem).stock <= 0" size="small" type="danger">
            {{ $t('admin.commerce.shop.soldOut') }}
          </el-tag>
          <span v-else>{{ (row as ProductItem).stock }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.commerce.shop.featured')" align="center" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as ProductItem).is_featured ? 'success' : 'info'" size="small">
            {{ (row as ProductItem).is_featured ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.status')" align="center" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as ProductItem).is_active ? 'success' : 'info'" size="small">
            {{ (row as ProductItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.createdAt')" width="170">
        <template #default="{ row }">{{ formatDateTime((row as ProductItem).created_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="240">
        <template #default="{ row }">
          <el-button
            v-auth="'module_commerce:payment:edit'"
            :icon="EditPen"
            link
            type="primary"
            @click="openEdit(row as ProductItem)"
          >
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button
            v-auth="'module_commerce:payment:edit'"
            link
            type="primary"
            @click="openStock(row as ProductItem)"
          >
            {{ $t('admin.commerce.shop.adjustStock') }}
          </el-button>
          <el-button
            v-auth="'module_commerce:payment:delete'"
            :icon="Delete"
            link
            type="danger"
            @click="onDeleteProduct(row as ProductItem)"
          >
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 商品新建 / 编辑 -->
    <AdminFormDrawer
      v-model="formVisible"
      :loading="saving"
      :title="editingId ? $t('admin.commerce.shop.editProduct') : $t('admin.commerce.shop.createProduct')"
      @confirm="submitProduct"
    >
      <el-form label-width="110px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.slug')">
          <el-input v-model="form.slug" :placeholder="$t('admin.commerce.shop.slugPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.price')" required>
          <el-input-number
            v-model="form.price"
            :min="0"
            :precision="2"
            :step="1"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item v-if="!editingId" :label="$t('admin.commerce.shop.originalPrice')">
          <el-input-number
            v-model="form.original_price"
            :min="0"
            :precision="2"
            :step="1"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.stock')">
          <el-input-number v-model="form.stock" :min="0" controls-position="right"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.sku')">
          <el-input v-model="form.sku"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.categoryId')">
          <el-input-number v-model="form.category_id" :min="1" controls-position="right"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.featured')">
          <el-switch v-model="form.is_featured"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" :rows="3" type="textarea"/>
        </el-form-item>
      </el-form>
    </AdminFormDrawer>

    <!-- 库存调整 -->
    <el-dialog v-model="stockVisible" :title="$t('admin.commerce.shop.adjustStockTitle')" width="420px">
      <el-form label-width="110px">
        <el-form-item :label="$t('admin.common.name')">
          <span>{{ stockTarget?.name }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.stock')">
          <span>{{ stockTarget?.stock ?? 0 }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.stockDelta')" required>
          <el-input-number v-model="stockForm.delta" controls-position="right"/>
        </el-form-item>
      </el-form>
      <p class="text-xs text-fg-muted">{{ $t('admin.commerce.shop.stockDeltaHint') }}</p>
      <template #footer>
        <el-button @click="stockVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="stockSaving" type="primary" @click="submitStock()">
          {{ $t('admin.common.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>
