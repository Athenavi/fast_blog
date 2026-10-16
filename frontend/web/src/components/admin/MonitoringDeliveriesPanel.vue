<script lang="ts" setup>
/**
 * 监控中心 · 通知投递记录面板
 *
 * 从 `pages/system/monitoring.vue` 的「通知投递记录」标签页抽出：按告警 id 查投递结果，
 * 并可强制重新派发一次（`dispatchAlert`）。
 *
 * 加载时机与原实现一致：本面板是**手动触发**，挂载不发请求（原页面亦如此）。
 */
import {Promotion, Search} from '@element-plus/icons-vue'
import {ref} from 'vue'

import type {AlertDeliveriesResult} from '@/api'
import {monitoringApi} from '@/api'
import {ElMessage} from '@/utils/feedback'

const {t} = useI18n()

const deliveryAlertId = ref<number | undefined>(undefined)
const deliveryLoading = ref(false)
const deliveries = ref<AlertDeliveriesResult | null>(null)
const dispatchForce = ref(false)
const dispatchLoading = ref(false)

async function loadDeliveries() {
  if (deliveryAlertId.value === undefined) {
    ElMessage.warning(t('admin.system.monitoring.deliveryAlertIdRequired'))
    return
  }
  deliveryLoading.value = true
  try {
    deliveries.value = await monitoringApi.alertDeliveries(deliveryAlertId.value)
  } finally {
    deliveryLoading.value = false
  }
}

async function onDispatchAlert() {
  if (deliveryAlertId.value === undefined) {
    ElMessage.warning(t('admin.system.monitoring.deliveryAlertIdRequired'))
    return
  }
  dispatchLoading.value = true
  try {
    const result = await monitoringApi.dispatchAlert(deliveryAlertId.value, dispatchForce.value)
    ElMessage.success(
      t('admin.system.monitoring.deliveryDispatched', {sent: result.sent, failed: result.failed}),
    )
    await loadDeliveries()
  } finally {
    dispatchLoading.value = false
  }
}
</script>

<template>
  <div class="table-toolbar">
    <span class="table-toolbar__title">{{ $t('admin.system.monitoring.deliveryAlertId') }}</span>
    <el-input-number v-model="deliveryAlertId" :min="1" style="width: 160px"/>
    <el-button :icon="Search" :loading="deliveryLoading" @click="loadDeliveries">
      {{ $t('admin.system.monitoring.deliveryQuery') }}
    </el-button>
    <el-button v-auth="'module_system:monitor:manage'" :icon="Promotion" :loading="dispatchLoading"
               type="primary" @click="onDispatchAlert">
      {{ $t('admin.system.monitoring.deliveryDispatch') }}
    </el-button>
    <el-checkbox v-model="dispatchForce" v-auth="'module_system:monitor:manage'">
      {{ $t('admin.system.monitoring.deliveryForce') }}
    </el-checkbox>
  </div>

  <el-descriptions v-if="deliveries" :border="true" :column="3" class="mt-3">
    <el-descriptions-item :label="$t('admin.system.monitoring.deliveryAlertId')">
      {{ deliveries.alert_id }}
    </el-descriptions-item>
    <el-descriptions-item :label="$t('admin.system.monitoring.deliveryTotal')">
      {{ deliveries.total }}
    </el-descriptions-item>
    <el-descriptions-item :label="$t('admin.system.monitoring.deliverySent')">
      {{ deliveries.sent }}
    </el-descriptions-item>
  </el-descriptions>

  <el-table v-if="deliveries" :data="deliveries.items" border class="mt-3" size="small" stripe>
    <el-table-column :label="$t('admin.system.monitoring.deliveryPlatform')" prop="platform"
                     width="120"/>
    <el-table-column :label="$t('admin.system.monitoring.deliveryStatus')" align="center" width="100">
      <template #default="{ row }">
        <el-tag :type="row.sent ? 'success' : 'danger'" size="small">
          {{ row.sent ? $t('admin.common.yes') : $t('admin.common.no') }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.system.monitoring.deliveryStatusCode')" align="center"
                     prop="status_code" width="100"/>
    <el-table-column :label="$t('admin.system.monitoring.deliveryDetail')" min-width="260"
                     prop="detail" show-overflow-tooltip/>
    <el-table-column :label="$t('admin.system.monitoring.deliveryAt')" min-width="180" prop="at"/>
  </el-table>
  <el-empty v-else :description="$t('admin.system.monitoring.deliveryEmpty')"/>
</template>

<style scoped>
.mt-3 {
  margin-top: 12px;
}
</style>
