<script lang="ts" setup>
/**
 * 多站点管理（T5-11 批次 4）
 *
 * 对齐 v3 `/system/site`：站点 CRUD。slug 创建后锁定；
 * domain 唯一；is_default 全站唯一（后端强制），默认站点不可删除。
 */
import {Plus} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {
  type MySiteItem,
  type MySitesResult,
  quotaApi,
  type QuotaCheckResult,
  type QuotaResource,
  type QuotaSnapshot,
  siteApi,
  type SiteItem,
  type SiteMemberItem
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.site.title',
  permission: 'module_system:site:view',
})

const {t} = useI18n()

interface SiteQueryForm extends PageQuery {
  is_active?: boolean
}

const list = useAdminList<SiteItem, SiteQueryForm>({
  fetcher: (params) => siteApi.list(params),
  defaultQuery: {is_active: undefined},
  syncUrl: true,
})

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive<{
  name: string;
  slug: string;
  domain: string;
  additional_domains: string;
  description: string;
  theme: string;
  language: string;
  timezone: string;
  is_active: boolean;
  is_default: boolean
}>({
  name: '',
  slug: '',
  domain: '',
  additional_domains: '',
  description: '',
  theme: 'default',
  language: 'en',
  timezone: 'UTC',
  is_active: true,
  is_default: false,
})

const formTitle = computed(() => (editingId.value ? t('admin.system.site.editTitle') : t('admin.system.site.createTitle')))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '', slug: '', domain: '', additional_domains: '', description: '',
    theme: 'default', language: 'en', timezone: 'UTC', is_active: true, is_default: false,
  })
  formVisible.value = true
}

function openEdit(row: SiteItem) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    slug: row.slug || '',
    domain: row.domain || '',
    additional_domains: (row.additional_domains || []).join(', '),
    description: row.description || '',
    theme: row.theme || 'default',
    language: row.language || 'en',
    timezone: row.timezone || 'UTC',
    is_active: row.is_active,
    is_default: row.is_default,
  })
  formVisible.value = true
}

function parseAdditionalDomains(): string[] {
  return form.additional_domains
    .split(/[,，;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

async function submitForm() {
  if (!form.name.trim() || !form.domain.trim()) {
    ElMessage.warning(t('admin.system.site.required'))
    return
  }
  if (!editingId.value && !form.slug.trim()) {
    ElMessage.warning(t('admin.system.site.slugRequired'))
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      domain: form.domain.trim(),
      additional_domains: parseAdditionalDomains(),
      description: form.description || null,
      theme: form.theme || 'default',
      language: form.language || 'en',
      timezone: form.timezone || 'UTC',
      is_active: form.is_active,
      is_default: form.is_default,
    }
    if (editingId.value) {
      await siteApi.update(editingId.value, payload)
    } else {
      await siteApi.create({...payload, slug: form.slug.trim()})
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await list.reload()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: SiteItem) {
  await ElMessageBox.confirm(t('admin.system.site.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await siteApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await list.reload()
}

// ═══════════════════════════════════════════════════════════════════════════
// 以下为追加内容（多站点：默认站点 / 域名 / 成员 / 我的站点 / 配额）。
// 既有逻辑未被修改；新增 import 与新增列 / 弹窗均为旁路追加。
// ═══════════════════════════════════════════════════════════════════════════

/** 站内角色文案映射（后端 role 为 owner / admin / member，未知值原样返回） */
function roleLabel(role: string): string {
  const map: Record<string, string> = {
    owner: 'admin.system.site.roleOwner',
    admin: 'admin.system.site.roleAdmin',
    member: 'admin.system.site.roleMember',
  }
  return map[role] ? t(map[role]) : role
}

/** 配额资源文案（后端 RESOURCE_TYPES: articles / media / users / storage_mb） */
function quotaResourceLabel(resource: string): string {
  return t(`admin.system.site.quotaResource.${resource}`)
}

// ---- 设为默认站点（POST /system/site/{site_id}/default） ----
async function onSetDefault(row: SiteItem) {
  await ElMessageBox.confirm(
    t('admin.system.site.setDefaultConfirm', {name: row.name || row.slug || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await siteApi.setDefault(row.id)
  ElMessage.success(t('admin.system.site.defaultSaved'))
  await list.reload()
}

// ---- 域名设置（PUT /system/site/{site_id}/domains） ----
const domainsVisible = ref(false)
const domainsSiteId = ref<number | null>(null)
const domainsSaving = ref(false)
const domainsForm = reactive<{ domain: string; additional_domains: string }>({
  domain: '',
  additional_domains: '',
})

function openDomains(row: SiteItem) {
  domainsSiteId.value = row.id
  domainsForm.domain = row.domain || ''
  domainsForm.additional_domains = (row.additional_domains || []).join(', ')
  domainsVisible.value = true
}

async function submitDomains() {
  if (!domainsSiteId.value) return
  if (!domainsForm.domain.trim()) {
    ElMessage.warning(t('admin.system.site.domainsRequired'))
    return
  }
  domainsSaving.value = true
  try {
    await siteApi.setDomains(domainsSiteId.value, {
      domain: domainsForm.domain.trim(),
      additional_domains: domainsForm.additional_domains
        .split(/[,，;\s]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    })
    ElMessage.success(t('admin.system.site.domainsSaved'))
    domainsVisible.value = false
    await list.reload()
  } finally {
    domainsSaving.value = false
  }
}

// ---- 站点成员（GET / POST /{site_id}/members、DELETE /{site_id}/members/{user_id}） ----
const membersVisible = ref(false)
const membersSite = ref<SiteItem | null>(null)
const membersLoading = ref(false)
const members = ref<SiteMemberItem[]>([])
const memberPage = ref(1)
const memberPageSize = ref(20)
const memberTotal = ref(0)
const memberSaving = ref(false)
const memberRemoving = ref<number | null>(null)
const memberForm = reactive<{ user_id: number | undefined; role: string; is_active: boolean }>({
  user_id: undefined,
  role: 'member',
  is_active: true,
})

async function openMembers(row: SiteItem) {
  membersSite.value = row
  memberPage.value = 1
  memberForm.user_id = undefined
  memberForm.role = 'member'
  memberForm.is_active = true
  membersVisible.value = true
  await loadMembers()
}

async function loadMembers() {
  if (!membersSite.value) return
  membersLoading.value = true
  try {
    const res = await siteApi.members(membersSite.value.id, {
      page: memberPage.value,
      page_size: memberPageSize.value,
    })
    members.value = res.items
    memberTotal.value = res.total
  } catch {
    members.value = []
    memberTotal.value = 0
  } finally {
    membersLoading.value = false
  }
}

async function onMemberPageChange(next: number) {
  memberPage.value = next
  await loadMembers()
}

async function addMember() {
  if (!membersSite.value) return
  const userId = Number(memberForm.user_id)
  if (!userId || userId < 1) {
    ElMessage.warning(t('admin.system.site.memberUserIdRequired'))
    return
  }
  memberSaving.value = true
  try {
    const res = await siteApi.addMember(membersSite.value.id, {
      user_id: userId,
      role: memberForm.role,
      is_active: memberForm.is_active,
    })
    ElMessage.success(
      t(res.created ? 'admin.system.site.memberAdded' : 'admin.system.site.memberUpdated'),
    )
    memberForm.user_id = undefined
    await loadMembers()
  } finally {
    memberSaving.value = false
  }
}

async function removeMember(row: SiteMemberItem) {
  if (!membersSite.value) return
  await ElMessageBox.confirm(
    t('admin.system.site.memberRemoveConfirm', {userId: row.user_id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  memberRemoving.value = row.user_id
  try {
    await siteApi.removeMember(membersSite.value.id, row.user_id)
    ElMessage.success(t('admin.system.site.memberRemoved'))
    await loadMembers()
  } finally {
    memberRemoving.value = null
  }
}

// ---- 我的站点（GET /system/site/mine） ----
const myVisible = ref(false)
const myLoading = ref(false)
const myFailed = ref(false)
const myItems = ref<MySiteItem[]>([])

async function openMySites() {
  myVisible.value = true
  myLoading.value = true
  myFailed.value = false
  try {
    const res: MySitesResult = await siteApi.mine()
    myItems.value = res.items
  } catch {
    myItems.value = []
    myFailed.value = true
  } finally {
    myLoading.value = false
  }
}

// ---- 站点配额（GET / POST check / PUT /system/quota/{site_id}） ----
const QUOTA_RESOURCES: QuotaResource[] = ['articles', 'media', 'users', 'storage_mb']

interface QuotaRow {
  resource: QuotaResource
  limit: number | null
  usage: number | null
  remaining: number | null
  percent: number | null
  exceeded: boolean
}

const quotaVisible = ref(false)
const quotaSite = ref<SiteItem | null>(null)
const quotaLoading = ref(false)
const quotaFailed = ref(false)
const quota = ref<QuotaSnapshot | null>(null)
const quotaSaving = ref(false)
const quotaForm = reactive<Record<QuotaResource, number | undefined>>({
  articles: undefined,
  media: undefined,
  users: undefined,
  storage_mb: undefined,
})

const checkForm = reactive<{ resource_type: QuotaResource; requested_amount: number }>({
  resource_type: 'articles',
  requested_amount: 1,
})
const checkLoading = ref(false)
const checkResult = ref<QuotaCheckResult | null>(null)

const quotaRows = computed<QuotaRow[]>(() => {
  const snap = quota.value
  if (!snap) return []
  return QUOTA_RESOURCES.map((resource) => ({
    resource,
    limit: snap.quota[resource] ?? null,
    usage: snap.usage[resource] ?? null,
    remaining: snap.remaining[resource] ?? null,
    percent: snap.usage_percent[resource] ?? null,
    exceeded: snap.exceeded.includes(resource),
  }))
})

async function openQuota(row: SiteItem) {
  quotaSite.value = row
  checkResult.value = null
  checkForm.resource_type = 'articles'
  checkForm.requested_amount = 1
  quotaVisible.value = true
  await loadQuota()
}

async function loadQuota() {
  if (!quotaSite.value) return
  quotaLoading.value = true
  quotaFailed.value = false
  try {
    const res = await quotaApi.get(quotaSite.value.id)
    quota.value = res
    for (const key of QUOTA_RESOURCES) {
      // 0 是合法值（表示不限），只有 null / undefined 才回退为空
      quotaForm[key] = res.quota[key] ?? undefined
    }
  } catch {
    quota.value = null
    quotaFailed.value = true
  } finally {
    quotaLoading.value = false
  }
}

async function saveQuota() {
  if (!quotaSite.value) return
  quotaSaving.value = true
  try {
    const payload: Partial<Record<QuotaResource, number | null>> = {}
    for (const key of QUOTA_RESOURCES) {
      const value = quotaForm[key]
      payload[key] = value === undefined || Number.isNaN(value) ? null : Number(value)
    }
    await quotaApi.update(quotaSite.value.id, payload)
    ElMessage.success(t('admin.system.site.quotaSaved'))
    await loadQuota()
  } finally {
    quotaSaving.value = false
  }
}

async function runCheck() {
  if (!quotaSite.value) return
  checkLoading.value = true
  try {
    checkResult.value = await quotaApi.check(quotaSite.value.id, {
      resource_type: checkForm.resource_type,
      requested_amount: Number(checkForm.requested_amount) || 0,
    })
  } finally {
    checkLoading.value = false
  }
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.site.desc')" :title="$t('admin.system.site.title')">
    <template #actions>
      <el-button v-auth="'module_system:site:create'" :icon="Plus" type="primary" @click="openCreate">
        {{ $t('admin.system.site.createTitle') }}
      </el-button>
      <!-- 追加：我的站点 -->
      <el-button v-auth="'module_system:site:view'" @click="openMySites">
        {{ $t('admin.system.site.mySites') }}
      </el-button>
    </template>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.system.site.emptyFiltered') : $t('admin.system.site.emptyDesc')"
      :empty-title="$t('admin.system.site.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.system.site.keyword')">
          <el-input
            v-model="list.query.keyword"
            :placeholder="$t('admin.system.site.keywordPlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="list.query.is_active" :placeholder="$t('admin.common.all')" clearable
                     style="width: 110px">
            <el-option :label="$t('admin.system.site.active')" :value="true"/>
            <el-option :label="$t('admin.system.site.inactive')" :value="false"/>
          </el-select>
        </el-form-item>
      </template>

      <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.site.slug')" prop="slug" width="120"/>
      <el-table-column :label="$t('admin.system.site.domain')" min-width="160" prop="domain" show-overflow-tooltip/>
      <el-table-column :label="$t('admin.system.site.additionalDomains')" min-width="160">
        <template #default="{ row }">
          {{ ((row as SiteItem).additional_domains || []).join(', ') || '—' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.site.theme')" prop="theme" width="110"/>
      <el-table-column :label="$t('admin.system.site.isDefault')" width="90">
        <template #default="{ row }">
          <el-tag v-if="(row as SiteItem).is_default" size="small" type="warning">
            {{ $t('admin.system.site.defaultTag') }}
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.status')" width="90">
        <template #default="{ row }">
          <el-tag :type="(row as SiteItem).is_active ? 'success' : 'info'" size="small">
            {{
              (row as SiteItem).is_active ? $t('admin.system.site.active') : $t('admin.system.site.inactive')
            }}
          </el-tag>
        </template>
      </el-table-column>
      <!-- 追加：管理操作列（成员 / 域名 / 配额 / 设为默认） -->
      <el-table-column :label="$t('admin.system.site.manageTitle')" fixed="right" width="300">
        <template #default="{ row }">
          <el-button v-auth="'module_system:site:view'" link type="primary"
                     @click="openMembers(row as SiteItem)">
            {{ $t('admin.system.site.memberBtn') }}
          </el-button>
          <el-button v-auth="'module_system:site:edit'" link type="primary"
                     @click="openDomains(row as SiteItem)">
            {{ $t('admin.system.site.domainsBtn') }}
          </el-button>
          <el-button v-auth="'module_system:site:view'" link type="primary"
                     @click="openQuota(row as SiteItem)">
            {{ $t('admin.system.site.quotaBtn') }}
          </el-button>
          <el-button
            v-auth="'module_system:site:edit'"
            :disabled="(row as SiteItem).is_default"
            link
            type="warning"
            @click="onSetDefault(row as SiteItem)"
          >
            {{ $t('admin.system.site.setDefault') }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
        <template #default="{ row }">
          <el-button v-auth="'module_system:site:edit'" link type="primary"
                     @click="openEdit(row as SiteItem)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_system:site:delete'" link type="danger"
                     @click="onDelete(row as SiteItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 新建 / 编辑 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="520px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.slug')" :required="!editingId">
          <el-input v-model="form.slug" :disabled="!!editingId"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.domain')" required>
          <el-input v-model="form.domain" placeholder="blog.example.com"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.additionalDomains')">
          <el-input v-model="form.additional_domains" :placeholder="$t('admin.system.site.additionalDomainsHint')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.theme')">
          <el-input v-model="form.theme"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.language')">
          <el-input v-model="form.language" placeholder="zh-CN"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.timezone')">
          <el-input v-model="form.timezone" placeholder="Asia/Shanghai"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.isDefault')">
          <el-switch v-model="form.is_default"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- ═════ 追加：我的站点（GET /system/site/mine） ═════ -->
    <el-dialog v-model="myVisible" :title="$t('admin.system.site.mySites')" width="640px">
      <p class="sq-hint">{{ $t('admin.system.site.mySitesHint') }}</p>
      <el-alert
        v-if="myFailed"
        :closable="false"
        :title="$t('admin.common.loadFailed')"
        class="sq-mb"
        show-icon
        type="error"
      />
      <el-table v-loading="myLoading" :data="myItems" border size="small">
        <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.site.domain')" min-width="160" prop="domain" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.site.myRole')" width="110">
          <template #default="{ row }">{{ roleLabel((row as MySiteItem).role) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as MySiteItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as MySiteItem).is_active ? $t('admin.system.site.active') : $t('admin.system.site.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.site.joinedAt')" prop="joined_at" width="170"/>
      </el-table>
      <el-empty
        v-if="!myLoading && !myItems.length"
        :description="$t('admin.system.site.mySitesEmpty')"
        :image-size="60"
      />
    </el-dialog>

    <!-- ═════ 追加：站点成员（GET / POST /{site_id}/members、DELETE members/{user_id}） ═════ -->
    <el-drawer v-model="membersVisible" :title="$t('admin.system.site.membersTitle')" destroy-on-close size="620px">
      <p class="sq-hint">{{ $t('admin.system.site.membersHint') }}</p>
      <el-form :inline="true" :model="memberForm">
        <el-form-item :label="$t('admin.system.site.memberUserId')">
          <el-input-number
            v-model="memberForm.user_id"
            :controls="false"
            :min="1"
            :precision="0"
            style="width: 120px"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.memberRole')">
          <el-select v-model="memberForm.role" style="width: 120px">
            <el-option :label="$t('admin.system.site.roleOwner')" value="owner"/>
            <el-option :label="$t('admin.system.site.roleAdmin')" value="admin"/>
            <el-option :label="$t('admin.system.site.roleMember')" value="member"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.memberActive')">
          <el-switch v-model="memberForm.is_active"/>
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_system:site:edit'"
            :loading="memberSaving"
            type="primary"
            @click="addMember"
          >
            {{ $t('admin.system.site.memberAdd') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="membersLoading" :data="members" border size="small">
        <el-table-column :label="$t('admin.system.site.memberUserId')" prop="user_id" width="100"/>
        <el-table-column :label="$t('admin.system.site.memberRole')" width="120">
          <template #default="{ row }">{{ roleLabel((row as SiteMemberItem).role) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="(row as SiteMemberItem).is_active ? 'success' : 'info'" size="small">
              {{
                (row as SiteMemberItem).is_active
                  ? $t('admin.system.site.active')
                  : $t('admin.system.site.inactive')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.site.joinedAt')" prop="joined_at" width="170"/>
        <el-table-column :label="$t('admin.common.actions')" width="100">
          <template #default="{ row }">
            <el-button
              v-auth="'module_system:site:edit'"
              :loading="memberRemoving === (row as SiteMemberItem).user_id"
              link
              type="danger"
              @click="removeMember(row as SiteMemberItem)"
            >
              {{ $t('admin.system.site.memberRemove') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-if="!membersLoading && !members.length"
        :description="$t('admin.system.site.membersEmpty')"
        :image-size="60"
      />
      <div v-if="memberTotal > memberPageSize" class="sq-pager">
        <el-pagination
          :current-page="memberPage"
          :page-size="memberPageSize"
          :total="memberTotal"
          layout="prev, pager, next"
          @current-change="onMemberPageChange"
        />
      </div>
    </el-drawer>

    <!-- ═════ 追加：域名设置（PUT /system/site/{site_id}/domains） ═════ -->
    <el-dialog v-model="domainsVisible" :title="$t('admin.system.site.domainsTitle')" width="480px">
      <p class="sq-hint">{{ $t('admin.system.site.domainsHint') }}</p>
      <el-form :model="domainsForm" label-width="110px">
        <el-form-item :label="$t('admin.system.site.domain')" required>
          <el-input v-model="domainsForm.domain" placeholder="blog.example.com"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.site.additionalDomains')">
          <el-input
            v-model="domainsForm.additional_domains"
            :placeholder="$t('admin.system.site.additionalDomainsHint')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="domainsVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="domainsSaving" type="primary" @click="submitDomains">
          {{ $t('admin.system.site.saveDomains') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ═════ 追加：站点配额（GET / PUT /system/quota/{site_id}、POST check） ═════ -->
    <el-drawer v-model="quotaVisible" :title="$t('admin.system.site.quotaTitle')" destroy-on-close size="660px">
      <p class="sq-hint">{{ $t('admin.system.site.quotaDesc') }}</p>
      <el-alert
        v-if="quotaFailed"
        :closable="false"
        :title="$t('admin.common.loadFailed')"
        class="sq-mb"
        show-icon
        type="error"
      />

      <el-table v-loading="quotaLoading" :data="quotaRows" border size="small">
        <el-table-column :label="$t('admin.system.site.quotaResourceLabel')" min-width="140">
          <template #default="{ row }">
            {{ quotaResourceLabel((row as QuotaRow).resource) }}
            <el-tag v-if="(row as QuotaRow).exceeded" size="small" type="danger">
              {{ $t('admin.system.site.quotaExceeded') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.site.quotaLimit')" width="110">
          <template #default="{ row }">
            {{
              ((row as QuotaRow).limit === null || (row as QuotaRow).limit === 0)
                ? $t('admin.system.site.quotaUnlimited')
                : (row as QuotaRow).limit
            }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.site.quotaUsage')" prop="usage" width="100"/>
        <el-table-column :label="$t('admin.system.site.quotaRemaining')" width="100">
          <template #default="{ row }">
            {{ (row as QuotaRow).remaining === null ? '—' : (row as QuotaRow).remaining }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.site.quotaPercent')" width="100">
          <template #default="{ row }">
            {{ (row as QuotaRow).percent === null ? '—' : ((row as QuotaRow).percent + '%') }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 用量口径（后端 usage_scope 如实标注，直接展示后端文案） -->
      <details v-if="quota" class="sq-scope">
        <summary>{{ $t('admin.system.site.quotaUsageScope') }}</summary>
        <ul>
          <li v-for="(scopeText, scopeKey) in quota.usage_scope" :key="scopeKey">
            <strong>{{ quotaResourceLabel(scopeKey) }}：</strong>{{ scopeText }}
          </li>
        </ul>
      </details>

      <!-- 编辑配额（PUT /system/quota/{site_id}） -->
      <div class="sq-block">
        <div class="sq-block__title">{{ $t('admin.system.site.quotaSaveTitle') }}</div>
        <p class="sq-hint">{{ $t('admin.system.site.quotaLimitHint') }}</p>
        <el-form :model="quotaForm" label-width="120px">
          <el-form-item v-for="res in QUOTA_RESOURCES" :key="res" :label="quotaResourceLabel(res)">
            <el-input-number
              v-model="quotaForm[res]"
              :min="0"
              :precision="0"
              :step="1"
              controls-position="right"
              style="width: 180px"
            />
          </el-form-item>
        </el-form>
        <el-button v-auth="'module_system:site:edit'" :loading="quotaSaving" type="primary" @click="saveQuota">
          {{ $t('admin.system.site.quotaSave') }}
        </el-button>
      </div>

      <!-- 配额校验（POST /system/quota/{site_id}/check） -->
      <div class="sq-block">
        <div class="sq-block__title">{{ $t('admin.system.site.quotaCheckTitle') }}</div>
        <p class="sq-hint">{{ $t('admin.system.site.quotaCheckHint') }}</p>
        <el-form :inline="true" :model="checkForm">
          <el-form-item :label="$t('admin.system.site.quotaCheckResource')">
            <el-select v-model="checkForm.resource_type" style="width: 140px">
              <el-option v-for="res in QUOTA_RESOURCES" :key="res" :label="quotaResourceLabel(res)" :value="res"/>
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('admin.system.site.quotaCheckAmount')">
            <el-input-number
              v-model="checkForm.requested_amount"
              :controls="false"
              :min="0"
              :precision="0"
              style="width: 120px"
            />
          </el-form-item>
          <el-form-item>
            <el-button v-auth="'module_system:site:view'" :loading="checkLoading" @click="runCheck">
              {{ $t('admin.system.site.quotaCheckRun') }}
            </el-button>
          </el-form-item>
        </el-form>
        <el-alert
          v-if="checkResult"
          :closable="false"
          :title="checkResult.allowed
            ? $t('admin.system.site.quotaCheckAllowed')
            : $t('admin.system.site.quotaCheckDenied')"
          :type="checkResult.allowed ? 'success' : 'error'"
          show-icon
        />
        <div v-if="checkResult" class="sq-check">
          <span>{{ $t('admin.system.site.quotaCheckReason') }}：{{ checkResult.reason }}</span>
          <span>{{ $t('admin.system.site.quotaUsage') }}：{{ checkResult.current ?? '—' }}</span>
          <span>
            {{ $t('admin.system.site.quotaLimit') }}：{{
              (checkResult.limit === null || checkResult.limit === 0)
                ? $t('admin.system.site.quotaUnlimited')
                : checkResult.limit
            }}
          </span>
          <span>{{ $t('admin.system.site.quotaRemaining') }}：{{ checkResult.remaining ?? '—' }}</span>
        </div>
      </div>
    </el-drawer>
  </AdminPage>
</template>

<style scoped>
.sq-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.sq-mb {
  margin-bottom: 10px;
}

.sq-block {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--color-line, #e5e7eb);
}

.sq-block__title {
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
}

.sq-pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.sq-scope {
  margin: 12px 0;
  font-size: 12px;
  color: var(--color-fg-muted, #606266);
}

.sq-scope ul {
  margin: 6px 0 0;
  padding-left: 18px;
}

.sq-check {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-fg-muted, #606266);
}
</style>
