/**
 * 兼容层：`useTable` 的能力已并入 `@/composables/useAdminList`（超集实现）。
 *
 * 新代码请直接用 `useAdminList`；这里保留旧名，避免一次性改动既有页面
 * （`ai/configs`、`chat/groups`、`commerce/*`、`analytics/report` 等）。
 */

export {useAdminList as useTable} from '@/composables/useAdminList'
export type {UseAdminListOptions as UseTableOptions} from '@/composables/useAdminList'
