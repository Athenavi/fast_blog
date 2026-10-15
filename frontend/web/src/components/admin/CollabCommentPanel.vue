<script lang="ts" setup>
/**
 * 协作管理 · 团队评论面板
 *
 * 从 `pages/content/collaboration.vue` 的「团队评论」标签页抽出。
 *
 * 它**完全自包含**：筛选条件（内容类型 + 内容 ID）、评论列表、以及底部的"发表评论"
 * 表单都在这里，与其他标签页没有任何共享状态；加载时机也照旧 ——
 * 由用户点「搜索」触发，原页面的 `onTabChange` 并没有为它做过任何事，
 * 所以这里不需要 `active` 属性。
 */
import {Delete, Search} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {collaborationApi, type TeamCommentItem} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

/** 团队评论类型（与内容评论的 `CommentItem` 区分：挂在任意内容对象上，带 mentions / is_resolved） */
type CommentItem = TeamCommentItem

const {t} = useI18n()

const commentForm = reactive({content_type: 'article', content_id: undefined as number | undefined})
const comments = ref<CommentItem[]>([])
const commentLoading = ref(false)
const commentPage = ref(1)
const commentTotal = ref(0)
const commentPageSize = ref(20)
const commentSearching = ref(false)
const newComment = reactive({text: '', parent_id: undefined as number | undefined, mentionsText: ''})

async function loadComments(): Promise<void> {
  if (commentForm.content_id === undefined) {
    ElMessage.warning(t('admin.content.collaboration.contentIdRequired'))
    return
  }
  commentLoading.value = true
  commentSearching.value = true
  try {
    const result = await collaborationApi.listComments({
      content_type: commentForm.content_type,
      content_id: commentForm.content_id,
      page: commentPage.value,
      page_size: commentPageSize.value,
    })
    comments.value = result.items ?? []
    commentTotal.value = result.total ?? 0
  } finally {
    commentLoading.value = false
    commentSearching.value = false
  }
}

/** 逗号/空格分隔的用户 id 串 → 去重前的正整数数组（非法项直接丢弃） */
function parseMentions(text: string): number[] | null {
  const items = text
    .split(/[,\s]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => Number(part))
    .filter((value) => Number.isInteger(value) && value > 0)
  return items.length ? items : null
}

async function submitComment(): Promise<void> {
  if (commentForm.content_id === undefined || !newComment.text.trim()) {
    ElMessage.warning(t('admin.content.collaboration.commentRequired'))
    return
  }
  await collaborationApi.createComment({
    content_type: commentForm.content_type,
    content_id: commentForm.content_id,
    text: newComment.text.trim(),
    parent_id: newComment.parent_id ?? null,
    mentions: parseMentions(newComment.mentionsText),
  })
  ElMessage.success(t('admin.content.collaboration.commented'))
  Object.assign(newComment, {text: '', parent_id: undefined, mentionsText: ''})
  await loadComments()
}

async function onResolveComment(row: CommentItem): Promise<void> {
  await collaborationApi.resolveComment(row.id)
  ElMessage.success(t('admin.content.collaboration.resolved'))
  await loadComments()
}

async function onDeleteComment(row: CommentItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.deleteCommentConfirm', {name: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeComment(row.id)
  ElMessage.success(t('admin.common.delete'))
  await loadComments()
}

async function onPageComments(next: number): Promise<void> {
  commentPage.value = next
  await loadComments()
}
</script>

<template>
  <el-card shadow="never">
    <el-form :inline="true" @submit.prevent="loadComments()">
      <el-form-item :label="$t('admin.content.collaboration.contentType')">
        <el-input v-model="commentForm.content_type" style="width: 130px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.contentId')">
        <el-input-number v-model="commentForm.content_id" :min="1" style="width: 130px"/>
      </el-form-item>
      <el-form-item>
        <el-button :icon="Search" type="primary" @click="loadComments()">
          {{ $t('admin.common.search') }}
        </el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="commentLoading" :data="comments" border size="small" stripe>
      <el-table-column :label="$t('admin.content.collaboration.author')" prop="author_name" width="140"/>
      <el-table-column :label="$t('admin.content.collaboration.text')" min-width="240" prop="text"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.content.collaboration.mentions')" min-width="120">
        <template #default="{ row }">
          {{ ((row as CommentItem).mentions ?? []).join(', ') || '-' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.collaboration.resolved')" align="center" width="100">
        <template #default="{ row }">
          <el-tag :type="(row as CommentItem).is_resolved ? 'success' : 'info'" size="small">
            {{ (row as CommentItem).is_resolved ? $t('admin.common.yes') : $t('admin.common.no') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="160">
        <template #default="{ row }">
          <el-button v-auth="'module_content:collaboration:edit'"
                     :disabled="(row as CommentItem).is_resolved" link type="success"
                     @click="onResolveComment(row as CommentItem)">
            {{ $t('admin.content.collaboration.resolve') }}
          </el-button>
          <el-button v-auth="'module_content:collaboration:delete'" :icon="Delete" link type="danger"
                     @click="onDeleteComment(row as CommentItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination :current-page="commentPage" :page-size="commentPageSize" :total="commentTotal"
                   background class="table-pagination" layout="total, prev, pager, next"
                   @current-change="onPageComments"/>

    <el-divider/>
    <el-form :model="newComment" label-width="110px">
      <el-form-item :label="$t('admin.content.collaboration.text')">
        <el-input v-model="newComment.text" :autosize="{minRows: 3, maxRows: 8}" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.parentId')">
        <el-input-number v-model="newComment.parent_id" :min="1" style="width: 160px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.content.collaboration.mentions')">
        <el-input v-model="newComment.mentionsText"
                  :placeholder="$t('admin.content.collaboration.mentionsPlaceholder')"/>
      </el-form-item>
      <el-form-item>
        <el-button v-auth="'module_content:collaboration:create'" type="primary"
                   @click="submitComment">
          {{ $t('admin.content.collaboration.comment') }}
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>
