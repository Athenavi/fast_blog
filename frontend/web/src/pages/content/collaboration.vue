<script lang="ts" setup>
/**
 * 协作管理（页面壳）
 *
 * 对齐 v3 `/content/collaboration`：工作区 / 成员与任务 / 团队评论 / 协作邀请 /
 * 协同文档（yjs）五个标签页。角色层级 `viewer < editor < admin < owner` 由后端强制
 * （页面按钮只做提示性禁用）。实时协同的 WebSocket 通道不在此页 —— 那是文章编辑器的
 * 能力，用原生 WebSocket 直连。
 *
 * **本文件现在只负责标签容器与跨标签联动**：五个标签页的内容（合计约 1200 行）已各自
 * 拆成 `components/admin/Collab*Panel.vue`。留在页面上的只有两块跨标签共享的状态：
 *
 *  - `currentWorkspaceId` / `currentWorkspaceName`：工作区标签页选中之后，「成员与任务」
 *    标签页要靠它们决定加载谁、以及显示「当前工作区: xxx」；
 *  - `workspacePanel`：邀请标签页里"接受邀请"成功可能让你加入一个新工作区，而工作区
 *    面板在另一个标签页里，只能通过模板 ref 请它重新拉一次列表。
 *
 * 各标签页的加载时机保持原样：工作区挂载即拉；成员与任务、yjs 切到该标签才拉；
 * 团队评论只在点「搜索」时拉；邀请挂载即拉（它原本就没有按需加载）。
 */
import {ref} from 'vue'

import CollabCommentPanel from '@/components/admin/CollabCommentPanel.vue'
import CollabInvitePanel from '@/components/admin/CollabInvitePanel.vue'
import CollabMemberTaskPanel from '@/components/admin/CollabMemberTaskPanel.vue'
import CollabWorkspacePanel from '@/components/admin/CollabWorkspacePanel.vue'
import CollabYjsPanel from '@/components/admin/CollabYjsPanel.vue'


definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.collaboration.title',
  permission: 'module_content:collaboration:view',
})

/** 当前标签页（五个标签页的内容各自独立成组件，见文件头说明） */
const activeTab = ref('workspace')


// ---------------------------------------------------------------- 工作区
/**
 * 当前选中的工作区（id 与名字）。
 *
 * 它们是**跨标签页共享的状态**，所以留在页面而不是工作区面板里：「成员与任务」
 * 标签页要靠 id 决定加载哪个工作区的成员与任务、靠 name 显示「当前工作区: xxx」。
 * 工作区列表本身（含新建 / 编辑 / 删除）已整块搬进 `CollabWorkspacePanel`。
 */
const currentWorkspaceId = ref<number | null>(null)
const currentWorkspaceName = ref<string | null>(null)

/** 接受邀请后要让工作区面板重新拉一次列表 —— 那个动作发生在「邀请」标签页里 */
const workspacePanel = ref<{ reload: () => Promise<void> } | null>(null)

/**
 * 工作区面板请求切到「成员与任务」。
 *
 * 先同步选中、再切标签 —— 顺序不能反：切标签会触发 `onTabChange`，
 * 那里要读 `currentWorkspaceId` 决定是否加载成员，读早一步就会拿到旧值。
 */
function onOpenMembers(id: number): void {
  currentWorkspaceId.value = id
  activeTab.value = 'member'
}

// 成员与任务整块搬进了 `CollabMemberTaskPanel`：它内部按 `active`（是否切到本标签）
// 决定何时拉取，与原 `onTabChange` 的时机一致；创建任务/成员所需的角色、状态、优先级
// 常量也随之搬走（顺带删掉了原先定义了却从未被引用的 `TASK_TAG`）。

// 团队评论整块搬进了 `CollabCommentPanel`：它完全自包含，连加载都由用户点「搜索」触发。

// ---------------------------------------------------------------- 邀请
// 协作邀请整块搬进了 `CollabInvitePanel`。唯一必须留在页面的是"接受邀请后刷新工作区
// 列表"—— 工作区列表住在 `CollabWorkspacePanel` 里，邀请面板够不到它，只能回抛事件。
function onInviteAccepted(): void {
  void workspacePanel.value?.reload()
}

// 工作区列表的首次加载由 `CollabWorkspacePanel` 自己的 onMounted 负责

// 协同文档（yjs）整块搬进了 `CollabYjsPanel`，它同样靠 `active` 属性决定何时拉房间列表。
// 至此五个标签页各自独立成组件，页面只负责标签容器与两处跨标签联动（见上）。
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 工作区 -->
      <el-tab-pane :label="$t('admin.content.collaboration.workspaces')" name="workspace">
        <CollabWorkspacePanel
          ref="workspacePanel"
          v-model:current-workspace-id="currentWorkspaceId"
          v-model:current-workspace-name="currentWorkspaceName"
          @open-members="onOpenMembers"
        />
      </el-tab-pane>

      <!-- 成员与任务 -->
      <el-tab-pane :label="$t('admin.content.collaboration.membersAndTasks')" name="member">
        <CollabMemberTaskPanel
          :active="activeTab === 'member'"
          :workspace-id="currentWorkspaceId"
          :workspace-name="currentWorkspaceName"
        />
      </el-tab-pane>

      <!-- 团队评论 -->
      <el-tab-pane :label="$t('admin.content.collaboration.comments')" name="comment">
        <CollabCommentPanel/>
      </el-tab-pane>

      <!-- 协作邀请 -->
      <el-tab-pane :label="$t('admin.content.collaboration.invites')" name="invite">
        <CollabInvitePanel :workspace-id="currentWorkspaceId" @accepted="onInviteAccepted"/>
      </el-tab-pane>

      <!-- 协同文档（yjs） -->
      <el-tab-pane :label="$t('admin.content.collaboration.yjs')" name="yjs">
        <CollabYjsPanel :active="activeTab === 'yjs'"/>
      </el-tab-pane>
    </el-tabs>

    <!-- 版本详情 -->
  </div>
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}

.table-toolbar__title {
  margin-right: 12px;
  font-weight: 600;
}

.hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.yjs-content {
  max-height: 360px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
