<script lang="ts" setup>
/**
 * 标签管理
 *
 * 标签并不单独建表——它存在 `articles.tags_list`(JSON) 里，
 * 因此后端只提供「聚合列表 / 重命名（可合并）/ 删除」这几种操作。
 */
import {Delete, Edit, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {tagApi, type TagItem} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '标签',
  permission: 'module_content:tag:view',
})

const loading = ref(false)
const list = ref<TagItem[]>([])
const total = ref(0)

const query = reactive({keyword: '', min_count: undefined as number | undefined})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await tagApi.list({
      limit: 200,
      ...(query.keyword ? {keyword: query.keyword} : {}),
      ...(query.min_count === undefined ? {} : {min_count: query.min_count}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------- 重命名
const dialogVisible = ref(false)
const saving = ref(false)
const oldName = ref('')
const newName = ref('')
const mergeHint = ref('')

async function openRename(row: TagItem): Promise<void> {
  oldName.value = row.name
  newName.value = row.name
  mergeHint.value = ''
  dialogVisible.value = true
}

/** 目标标签已存在时后端会合并，这里提前给出提示 */
async function checkMerge(): Promise<void> {
  const target = newName.value.trim()
  if (!target || target === oldName.value) {
    mergeHint.value = ''
    return
  }
  mergeHint.value = list.value.some((item) => item.name === target)
    ? `「${target}」已存在，保存后将与它合并`
    : ''
}

async function submitRename(): Promise<void> {
  const target = newName.value.trim()
  if (!target) {
    ElMessage.warning('请填写新的标签名')
    return
  }
  if (target === oldName.value) {
    dialogVisible.value = false
    return
  }

  saving.value = true
  try {
    const result = await tagApi.rename(oldName.value, target)
    ElMessage.success(result?.merged ? '已合并到同名标签' : '已重命名')
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

async function removeRow(row: TagItem): Promise<void> {
  await ElMessageBox.confirm(
    `确定删除标签「${row.name}」吗？将从 ${row.count} 篇文章上移除该标签。`,
    '提示',
    {type: 'warning'},
  )
  await tagApi.remove(row.name)
  ElMessage.success('已删除')
  await loadList()
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="标签名包含" style="width: 200px"
                    @keyup.enter="loadList"/>
        </el-form-item>
        <el-form-item label="最少文章数">
          <el-input-number v-model="query.min_count" :min="0" controls-position="right" style="width: 130px"/>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" type="primary" @click="loadList">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="list" row-key="name">
        <el-table-column label="标签" min-width="240" prop="name">
          <template #default="{row}">
            <el-tag size="small">{{ row.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文章数" prop="count" width="120"/>
        <el-table-column fixed="right" label="操作" width="180">
          <template #default="{row}">
            <el-button v-auth="'module_content:tag:edit'" :icon="Edit" link type="primary" @click="openRename(row)">
              重命名
            </el-button>
            <el-button v-auth="'module_content:tag:edit'" :icon="Delete" link type="danger" @click="removeRow(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">共 {{ total }} 个标签（最多显示 200 个，可用关键词筛选）</p>
    </el-card>

    <el-dialog v-model="dialogVisible" destroy-on-close title="重命名标签" width="480px">
      <el-form label-width="90px">
        <el-form-item label="原标签">
          <el-tag size="small">{{ oldName }}</el-tag>
        </el-form-item>
        <el-form-item label="新标签" required>
          <el-input v-model="newName" maxlength="100" placeholder="输入新的标签名" @input="checkMerge"/>
        </el-form-item>
        <el-alert v-if="mergeHint" :closable="false" :title="mergeHint" type="warning"/>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitRename">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: #909399;
}
</style>
