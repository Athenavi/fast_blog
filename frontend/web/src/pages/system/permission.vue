<script lang="ts" setup>
const {t} = useI18n()
/**
 * 权限码总览
 *
 * 权威来源是后端 `core/permission/codes.py` 的 `CODE_LABELS`，
 * 这里只做只读展示（按 `resource_type` 分组）与权限缓存运维。
 */
import {Delete, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {ref} from 'vue'

import {type CapabilityGroup, permissionApi} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.permission.title',
  permission: 'module_system:permission:view',
})

const loading = ref(false)
const groups = ref<CapabilityGroup[]>([])
const cacheStats = ref<Record<string, unknown> | null>(null)
const keyword = ref('')

async function load(): Promise<void> {
  loading.value = true
  try {
    const [grouped, stats] = await Promise.all([
      permissionApi.grouped(),
      permissionApi.cacheStats().catch(() => null),
    ])
    groups.value = grouped
    cacheStats.value = stats
  } finally {
    loading.value = false
  }
}

/** 关键词过滤（前端过滤：权限码总量有限，不必增加后端参数） */
const filteredGroups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return groups.value
  return groups.value
    .map((group) => ({
      ...group,
      capabilities: group.capabilities.filter(
        (item) =>
          item.code.toLowerCase().includes(kw) || (item.name || '').toLowerCase().includes(kw),
      ),
    }))
    .filter((group) => group.capabilities.length > 0)
})

const totalCount = computed(() =>
  groups.value.reduce((sum, group) => sum + group.capabilities.length, 0),
)

async function invalidateCache(): Promise<void> {
  await ElMessageBox.confirm(t('admin.system.permission.clearConfirm'), t('admin.common.notice'), {type: 'warning'})
  await permissionApi.invalidateCache()
  ElMessage.success(t('admin.system.permission.cacheCleared'))
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" :placeholder="$t('admin.system.permission.filterPlaceholder')" clearable
                  style="width: 260px"/>
        <el-button :icon="Refresh" circle @click="load"/>
        <span class="count">{{
            $t('admin.system.permission.totalSummary', {count: totalCount, groups: groups.length})
          }}</span>
        <el-button
          v-auth="'module_system:permission:edit'"
          :icon="Delete"
          class="ml-auto"
          plain
          type="warning"
          @click="invalidateCache"
        >
          {{ $t('admin.system.permission.clearCache') }}
        </el-button>
      </div>

      <el-alert v-if="cacheStats" :closable="false" class="stats" type="info">
        <template #title>{{ $t('admin.system.permission.cacheTitle', {stats: JSON.stringify(cacheStats)}) }}</template>
      </el-alert>

      <el-collapse v-loading="loading" class="groups">
        <el-collapse-item v-for="group in filteredGroups" :key="group.resource_type" :name="group.resource_type">
          <template #title>
            <span class="group-title">{{ group.resource_type }}</span>
            <el-tag class="ml-2" size="small">{{ group.capabilities.length }}</el-tag>
          </template>

          <el-table :data="group.capabilities" border size="small">
            <el-table-column :label="$t('admin.system.permission.code')" min-width="280" prop="code"/>
            <el-table-column :label="$t('admin.common.name')" min-width="160" prop="name"/>
            <el-table-column :label="$t('admin.system.permission.action')" prop="action" width="130"/>
            <el-table-column :label="$t('admin.common.status')" width="90">
              <template #default="{row}">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? t('admin.common.enabled') : t('admin.common.disabled') }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>

      <el-empty v-if="!loading && !filteredGroups.length" :description="$t('admin.system.permission.empty')"/>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.ml-auto {
  margin-left: auto;
}

.ml-2 {
  margin-left: 8px;
}

.count {
  font-size: 13px;
  color: #909399;
}

.stats {
  margin-bottom: 12px;
}

.group-title {
  font-weight: 600;
}
</style>
