<script lang="ts" setup>
/**
 * 权限码总览
 *
 * 权威来源是后端 `core/permission/codes.py` 的 `CODE_LABELS`，
 * 这里只做只读展示（按 `resource_type` 分组）与权限缓存运维。
 */
import {Delete, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {ref} from 'vue'

import {permissionApi, type CapabilityGroup} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '权限码',
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
  await ElMessageBox.confirm('确定清空全部用户的权限缓存吗？', '提示', {type: 'warning'})
  await permissionApi.invalidateCache()
  ElMessage.success('缓存已失效，将在下次请求时重建')
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="按权限码或名称过滤" style="width: 260px"/>
        <el-button :icon="Refresh" circle @click="load"/>
        <span class="count">共 {{ totalCount }} 个权限码，{{ groups.length }} 个资源域</span>
        <el-button
          v-auth="'module_system:permission:edit'"
          :icon="Delete"
          class="ml-auto"
          plain
          type="warning"
          @click="invalidateCache"
        >
          清空权限缓存
        </el-button>
      </div>

      <el-alert v-if="cacheStats" :closable="false" class="stats" type="info">
        <template #title>权限缓存：{{ JSON.stringify(cacheStats) }}</template>
      </el-alert>

      <el-collapse v-loading="loading" class="groups">
        <el-collapse-item v-for="group in filteredGroups" :key="group.resource_type" :name="group.resource_type">
          <template #title>
            <span class="group-title">{{ group.resource_type }}</span>
            <el-tag class="ml-2" size="small">{{ group.capabilities.length }}</el-tag>
          </template>

          <el-table :data="group.capabilities" border size="small">
            <el-table-column label="权限码" min-width="280" prop="code"/>
            <el-table-column label="名称" min-width="160" prop="name"/>
            <el-table-column label="动作" prop="action" width="130"/>
            <el-table-column label="状态" width="90">
              <template #default="{row}">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>

      <el-empty v-if="!loading && !filteredGroups.length" description="没有匹配的权限码"/>
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
