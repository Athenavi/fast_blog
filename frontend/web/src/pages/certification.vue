<script lang="ts" setup>
/**
 * 我的专家认证（`/certification`）
 *
 * 对齐 v3 `/api/v3/gamification/certification`：
 *  - 未申请过 → 显示申请表单；`rejected` / `revoked` 后可**重新申请**（后端只挡 pending 与 approved）；
 *  - `pending` → 可修改基本资料（材料不可改，后端 `CertificationUpdateRequest` 没有該字段）与撤回；
 *  - `approved` → 展示签发与到期时间（有效期两年，到期后自动从专家列表消失）；
 *  - `id_number`（证件号）只提交、**永不回显**，因此表单在已有申请时不预填该字段。
 *
 * 需登录：`middleware: 'auth'`，`/certification` 在 nuxt.config.ts 里为 `ssr: false`。
 */
import {certificationApi, type CertificationApplyPayload, type CertificationItem, type CertTypeItem,} from '@/api'
import {formatDate} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: 'certification.title'})

const {t} = useI18n()

const MAX_DOCUMENTS = 10

const mine = ref<CertificationItem | null>(null)
const types = ref<CertTypeItem[]>([])

const loading = ref(true)
const failed = ref(false)
const saving = ref(false)
const withdrawing = ref(false)
const notice = ref('')
const error = ref('')

const pickerOpen = ref(false)

/** 表单（`id_number` 上传后不预填：后端不回显） */
const form = reactive({
  cert_type: '',
  real_name: '',
  id_number: '',
  phone: '',
  email: '',
  organization: '',
  position: '',
  department: '',
  work_years: 0,
  intro: '',
  achievements: '',
  portfolio_url: '',
})

/** 材料编辑态：本地用非空字符串，提交时再映射成后端 payload（可空字段转 null） */
interface DocumentDraft {
  file_url: string
  file_name: string
  file_type: string
  file_size: number
}

const documents = ref<DocumentDraft[]>([])

const isPending = computed(() => mine.value?.status === 'pending')
const canApply = computed(() => !mine.value || ['rejected', 'revoked'].includes(String(mine.value.status)))

const STATUS_LABELS: Record<string, string> = {
  pending: 'certification.statusPending',
  approved: 'certification.statusApproved',
  rejected: 'certification.statusRejected',
  revoked: 'certification.statusRevoked',
}

function statusLabel(status?: string | null): string {
  return t(STATUS_LABELS[String(status)] ?? 'certification.statusUnknown')
}

function statusVariant(status?: string | null): 'default' | 'success' | 'secondary' | 'danger' {
  if (status === 'approved') return 'success'
  if (status === 'pending') return 'default'
  if (status === 'rejected') return 'danger'
  return 'secondary'
}

function statusHint(item: CertificationItem): string {
  if (item.status === 'pending') return t('certification.hintPending')
  if (item.status === 'approved') {
    return item.is_expired
      ? t('certification.hintExpired')
      : t('certification.hintApproved', {date: formatDate(item.expires_at)})
  }
  if (item.status === 'rejected') return t('certification.hintRejected')
  return t('certification.hintRevoked')
}

function fillForm(item: CertificationItem): void {
  form.cert_type = item.cert_type || ''
  form.real_name = item.real_name || ''
  form.id_number = ''
  form.phone = ''
  form.email = ''
  form.organization = item.organization || ''
  form.position = item.position || ''
  form.department = item.department || ''
  form.work_years = item.work_years || 0
  form.intro = item.intro || ''
  form.achievements = item.achievements || ''
  form.portfolio_url = item.portfolio_url || ''
}

function resetForm(): void {
  Object.assign(form, {
    cert_type: types.value[0]?.code || '',
    real_name: '',
    id_number: '',
    phone: '',
    email: '',
    organization: '',
    position: '',
    department: '',
    work_years: 0,
    intro: '',
    achievements: '',
    portfolio_url: '',
  })
  documents.value = []
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const [detail, typeRows] = await Promise.all([
      certificationApi.mine(),
      certificationApi.types().catch(() => [] as CertTypeItem[]),
    ])
    mine.value = detail
    types.value = typeRows ?? []
    if (detail && detail.status !== 'pending') {
      // 已通过 / 已驳回 / 已撤回：表单不预填（重新申请时从空白开始，避免误用旧材料）
      resetForm()
    } else if (detail) {
      fillForm(detail)
      documents.value = []
    } else {
      resetForm()
    }
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

function addDocument(): void {
  if (documents.value.length >= MAX_DOCUMENTS) {
    error.value = t('certification.documentsLimit', {n: MAX_DOCUMENTS})
    return
  }
  documents.value.push({file_url: '', file_name: '', file_type: '', file_size: 0})
}

function removeDocument(index: number): void {
  documents.value.splice(index, 1)
}

function onPicked(url: string): void {
  if (!url) return
  if (documents.value.length >= MAX_DOCUMENTS) {
    error.value = t('certification.documentsLimit', {n: MAX_DOCUMENTS})
    return
  }
  documents.value.push({file_url: url, file_name: '', file_type: '', file_size: 0})
}

async function submit(): Promise<void> {
  notice.value = ''
  error.value = ''
  if (!form.cert_type) {
    error.value = t('certification.requiredType')
    return
  }
  if (!form.real_name.trim()) {
    error.value = t('certification.requiredRealName')
    return
  }

  const payload: CertificationApplyPayload = {
    cert_type: form.cert_type,
    real_name: form.real_name.trim(),
    id_number: form.id_number.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
    organization: form.organization.trim() || null,
    position: form.position.trim() || null,
    department: form.department.trim() || null,
    work_years: Number(form.work_years) || 0,
    intro: form.intro.trim() || null,
    achievements: form.achievements.trim() || null,
    portfolio_url: form.portfolio_url.trim() || null,
  }

  saving.value = true
  try {
    if (isPending.value) {
      await certificationApi.updateMine(payload)
      notice.value = t('certification.updateSuccess')
    } else {
      const cleaned = documents.value
        .filter((item) => (item.file_url || '').trim())
        .map((item) => ({
          file_url: (item.file_url || '').trim(),
          file_name: item.file_name || null,
          file_type: item.file_type || null,
          file_size: Number(item.file_size) || 0,
        }))
      await certificationApi.apply({...payload, documents: cleaned})
      notice.value = t('certification.applySuccess')
    }
    await load()
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    saving.value = false
  }
}

async function withdraw(): Promise<void> {
  notice.value = ''
  error.value = ''
  withdrawing.value = true
  try {
    mine.value = await certificationApi.withdraw()
    notice.value = t('certification.withdrawSuccess')
    await load()
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    withdrawing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('certification.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('certification.subtitle') }}</p>
      </div>
      <NuxtLink class="text-sm text-primary hover:underline" to="/experts">
        {{ $t('certification.browseExperts') }}
      </NuxtLink>
    </div>

    <p v-if="notice" class="mt-5 rounded-card border border-line bg-surface-soft px-4 py-2.5 text-sm text-fg">
      {{ notice }}
    </p>
    <p v-if="error" class="mt-5 rounded-card border border-danger/40 bg-surface-soft px-4 py-2.5 text-sm text-danger">
      {{ error }}
    </p>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton class="h-24 w-full"/>
      <Skeleton class="h-64 w-full"/>
    </div>

    <EmptyState
      v-else-if="failed"
      :description="$t('common.networkError')"
      :title="$t('certification.loadFailed')"
    >
      <Button class="mt-3" size="sm" variant="outline" @click="load()">{{ $t('common.retry') }}</Button>
    </EmptyState>

    <template v-else>
      <!-- 当前状态 -->
      <section v-if="mine" class="mt-6 rounded-card border border-line bg-surface p-5">
        <div class="flex flex-wrap items-center gap-2">
          <Badge :variant="statusVariant(mine.status)">{{ statusLabel(mine.status) }}</Badge>
          <span class="text-sm font-medium text-fg">{{ mine.cert_type_name || mine.cert_type }}</span>
        </div>
        <p class="mt-2 text-sm text-fg-muted">{{ statusHint(mine) }}</p>

        <dl class="mt-3 grid grid-cols-1 gap-2 text-xs text-fg-subtle sm:grid-cols-3">
          <div>
            <dt>{{ $t('certification.appliedAt') }}</dt>
            <dd class="text-fg-muted">{{ formatDate(mine.applied_at) }}</dd>
          </div>
          <div v-if="mine.reviewed_at">
            <dt>{{ $t('certification.reviewedAt') }}</dt>
            <dd class="text-fg-muted">{{ formatDate(mine.reviewed_at) }}</dd>
          </div>
          <div v-if="mine.issued_at">
            <dt>{{ $t('certification.issuedAt') }}</dt>
            <dd class="text-fg-muted">{{ formatDate(mine.issued_at) }}</dd>
          </div>
          <div v-if="mine.expires_at">
            <dt>{{ $t('certification.expiresAt') }}</dt>
            <dd class="text-fg-muted">{{ formatDate(mine.expires_at) }}</dd>
          </div>
        </dl>

        <p v-if="mine.review_comment" class="mt-3 rounded-control bg-surface-soft px-3 py-2 text-sm text-fg">
          {{ $t('certification.reviewComment') }}：{{ mine.review_comment }}
        </p>

        <ul v-if="mine.documents?.length" class="mt-3 space-y-1 text-sm">
          <li v-for="doc in mine.documents" :key="doc.id" class="truncate text-fg-muted">
            <a :href="doc.file_url" class="hover:underline" rel="noopener noreferrer nofollow" target="_blank">
              {{ doc.file_name || doc.file_url }}
            </a>
          </li>
        </ul>

        <div v-if="isPending" class="mt-4">
          <Button :disabled="withdrawing" size="sm" variant="outline" @click="withdraw">
            <Icon v-if="withdrawing" class="h-4 w-4 animate-spin" name="loader-circle"/>
            <Icon v-else class="h-4 w-4" name="rotate-ccw"/>
            {{ $t('certification.withdraw') }}
          </Button>
        </div>
      </section>

      <!-- 申请 / 修改表单 -->
      <section v-if="canApply || isPending" class="mt-6 rounded-card border border-line bg-surface p-5">
        <h2 class="text-base font-semibold text-fg">
          {{ isPending ? $t('certification.editTitle') : $t('certification.applyTitle') }}
        </h2>
        <p class="mt-1 text-xs text-fg-subtle">{{ $t('certification.formHint') }}</p>

        <div class="mt-4 space-y-4">
          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldCertType') }}</label>
              <select
                v-model="form.cert_type"
                class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg"
              >
                <option v-for="item in types" :key="item.code" :value="item.code">{{ item.name }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldRealName') }}</label>
              <Input v-model="form.real_name" :placeholder="$t('certification.fieldRealNamePlaceholder')"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldIdNumber') }}</label>
              <Input v-model="form.id_number" :placeholder="$t('certification.fieldIdNumberPlaceholder')"/>
              <p class="mt-1 text-xs text-fg-subtle">{{ $t('certification.fieldIdNumberHint') }}</p>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldPhone') }}</label>
              <Input v-model="form.phone"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldEmail') }}</label>
              <Input v-model="form.email"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{
                  $t('certification.fieldOrganization')
                }}</label>
              <Input v-model="form.organization"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldPosition') }}</label>
              <Input v-model="form.position"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldDepartment') }}</label>
              <Input v-model="form.department"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldWorkYears') }}</label>
              <Input v-model="form.work_years" inputmode="numeric" type="number"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldPortfolio') }}</label>
              <Input v-model="form.portfolio_url" :placeholder="$t('certification.fieldPortfolioPlaceholder')"/>
            </div>
          </div>

          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldIntro') }}</label>
            <textarea
              v-model="form.intro"
              class="w-full rounded-control border border-line px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              maxlength="2000"
              rows="3"
            />
          </div>

          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('certification.fieldAchievements') }}</label>
            <textarea
              v-model="form.achievements"
              class="w-full rounded-control border border-line px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              maxlength="4000"
              rows="4"
            />
          </div>

          <!-- 材料：仅申请时可提交（后端修改接口没有材料字段） -->
          <div v-if="!isPending">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <label class="text-sm font-medium text-fg">{{ $t('certification.documentsTitle') }}</label>
              <div class="flex items-center gap-2">
                <Button size="sm" type="button" variant="outline" @click="pickerOpen = true">
                  <Icon class="h-4 w-4" name="image"/>
                  {{ $t('certification.pickFromMedia') }}
                </Button>
                <Button :disabled="documents.length >= MAX_DOCUMENTS" size="sm" type="button" variant="outline"
                        @click="addDocument">
                  <Icon class="h-4 w-4" name="plus"/>
                  {{ $t('certification.addDocument') }}
                </Button>
              </div>
            </div>
            <p class="mt-1 text-xs text-fg-subtle">{{ $t('certification.documentsHint', {n: MAX_DOCUMENTS}) }}</p>

            <ul v-if="documents.length" class="mt-2 space-y-2">
              <li v-for="(doc, index) in documents" :key="index" class="flex items-center gap-2">
                <Input v-model="doc.file_url" :placeholder="$t('certification.documentUrlPlaceholder')" class="flex-1"/>
                <Input v-model="doc.file_name" :placeholder="$t('certification.documentNamePlaceholder')" class="w-40"/>
                <button
                  class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-danger"
                  type="button"
                  @click="removeDocument(index)"
                >
                  <Icon class="h-4 w-4" name="trash-2"/>
                </button>
              </li>
            </ul>
            <p v-else class="mt-2 text-sm text-fg-muted">{{ $t('certification.documentsEmpty') }}</p>
          </div>
          <p v-else class="rounded-control bg-surface-soft px-3 py-2 text-xs text-fg-subtle">
            {{ $t('certification.documentsLocked') }}
          </p>

          <div class="flex items-center justify-end gap-2 pt-1">
            <Button :disabled="saving" type="button" @click="submit">
              <Icon v-if="saving" class="h-4 w-4 animate-spin" name="loader-circle"/>
              <Icon v-else class="h-4 w-4" name="send"/>
              {{ isPending ? $t('certification.submitUpdate') : $t('certification.submitApply') }}
            </Button>
          </div>
        </div>
      </section>

      <MediaPickerDialog v-model="pickerOpen" @select="onPicked"/>
    </template>
  </div>
</template>
