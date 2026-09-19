<script lang="ts" setup>
/**
 * 表单构建器（T5-11 批次 2）
 *
 * 对齐 v3 `/marketing/form`：表单 + 字段 + 提交（三标签）。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {formApi, type FormFieldItem, type FormItem, type FormSubmissionItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.marketing.form.title',
  permission: 'module_marketing:form:view',
})

const {t} = useI18n()
const activeTab = ref('forms')

// ---- 表单 ----
const formTable = useTable<FormItem>({fetcher: (params) => formApi.list(params)})

const formFormVisible = ref(false)
const formEditingId = ref<number | null>(null)
const formSaving = ref(false)
const formForm = reactive({
  title: '', slug: '', description: '', status: 'draft',
  submit_message: '', email_notification: false, notification_email: '', store_submissions: true,
})

const formFormTitle = computed(() =>
  formEditingId.value ? t('admin.marketing.form.editForm') : t('admin.marketing.form.createForm'))

function openFormCreate() {
  formEditingId.value = null
  Object.assign(formForm, {
    title: '', slug: '', description: '', status: 'draft',
    submit_message: '', email_notification: false, notification_email: '', store_submissions: true,
  })
  formFormVisible.value = true
}

function openFormEdit(row: FormItem) {
  formEditingId.value = row.id
  Object.assign(formForm, {
    title: row.title || '',
    slug: row.slug || '',
    description: row.description || '',
    status: row.status || 'draft',
    submit_message: row.submit_message || '',
    email_notification: row.email_notification,
    notification_email: row.notification_email || '',
    store_submissions: row.store_submissions,
  })
  formFormVisible.value = true
}

async function submitForm() {
  if (!formForm.title.trim() || !formForm.slug.trim()) {
    ElMessage.warning(t('admin.marketing.form.formRequired'))
    return
  }
  formSaving.value = true
  try {
    if (formEditingId.value) {
      await formApi.update(formEditingId.value, {
        title: formForm.title.trim(),
        description: formForm.description || null,
        status: formForm.status,
        submit_message: formForm.submit_message || null,
        email_notification: formForm.email_notification,
        notification_email: formForm.notification_email || null,
        store_submissions: formForm.store_submissions,
      })
    } else {
      await formApi.create({title: formForm.title.trim(), slug: formForm.slug.trim()})
      // 新建后仅写基本字段；其余随编辑保存
      const list = formTable.list.value
      const created = list[list.length - 1]
      if (created) {
        await formApi.update(created.id, {
          description: formForm.description || null,
          status: formForm.status,
          submit_message: formForm.submit_message || null,
          email_notification: formForm.email_notification,
          notification_email: formForm.notification_email || null,
          store_submissions: formForm.store_submissions,
        })
      }
    }
    ElMessage.success(t('admin.common.save'))
    formFormVisible.value = false
    await formTable.load()
  } finally {
    formSaving.value = false
  }
}

async function deleteForm(row: FormItem) {
  await ElMessageBox.confirm(t('admin.marketing.form.deleteFormConfirm'), t('admin.common.notice'), {type: 'warning'})
  await formApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await formTable.load()
}

// ---- 字段 ----
const fieldsVisible = ref(false)
const fieldsFormId = ref<number | null>(null)
const fieldsTitle = ref('')
const fieldList = ref<FormFieldItem[]>([])
const fieldsLoading = ref(false)

const fieldFormVisible = ref(false)
const fieldEditingId = ref<number | null>(null)
const fieldSaving = ref(false)
const fieldForm = reactive({
  label: '', field_type: 'text', placeholder: '', help_text: '',
  required: false, options: '', default_value: '', order_index: 0, is_active: true,
})

async function openFields(row: FormItem) {
  fieldsFormId.value = row.id
  fieldsTitle.value = `${t('admin.marketing.form.fields')} - ${row.title}`
  fieldFormVisible.value = false
  fieldsVisible.value = true
  await reloadFields()
}

async function reloadFields() {
  if (!fieldsFormId.value) return
  fieldsLoading.value = true
  try {
    fieldList.value = await formApi.fields(fieldsFormId.value)
  } finally {
    fieldsLoading.value = false
  }
}

function openFieldCreate() {
  fieldEditingId.value = null
  Object.assign(fieldForm, {
    label: '', field_type: 'text', placeholder: '', help_text: '',
    required: false, options: '', default_value: '', order_index: fieldList.value.length, is_active: true,
  })
  fieldFormVisible.value = true
}

function openFieldEdit(row: FormFieldItem) {
  fieldEditingId.value = row.id
  Object.assign(fieldForm, {
    label: row.label || '',
    field_type: row.field_type || 'text',
    placeholder: row.placeholder || '',
    help_text: row.help_text || '',
    required: row.required,
    options: row.options || '',
    default_value: row.default_value || '',
    order_index: row.order_index ?? 0,
    is_active: row.is_active,
  })
  fieldFormVisible.value = true
}

async function submitField() {
  if (!fieldsFormId.value || !fieldForm.label.trim()) {
    ElMessage.warning(t('admin.marketing.form.fieldRequired'))
    return
  }
  fieldSaving.value = true
  try {
    const payload = {
      label: fieldForm.label.trim(),
      field_type: fieldForm.field_type,
      placeholder: fieldForm.placeholder || null,
      help_text: fieldForm.help_text || null,
      required: fieldForm.required,
      options: fieldForm.options || null,
      default_value: fieldForm.default_value || null,
      order_index: fieldForm.order_index,
      is_active: fieldForm.is_active,
    }
    if (fieldEditingId.value) {
      await formApi.updateField(fieldEditingId.value, payload)
    } else {
      await formApi.createField(fieldsFormId.value, payload)
    }
    ElMessage.success(t('admin.common.save'))
    fieldFormVisible.value = false
    await reloadFields()
  } finally {
    fieldSaving.value = false
  }
}

async function deleteField(row: FormFieldItem) {
  await ElMessageBox.confirm(t('admin.marketing.form.deleteFieldConfirm'), t('admin.common.notice'), {type: 'warning'})
  await formApi.removeField(row.id)
  ElMessage.success(t('admin.common.delete'))
  await reloadFields()
}

// ---- 提交 ----
interface SubQueryForm extends PageQuery {
  form_id?: number
}

const subTable = useTable<FormSubmissionItem, SubQueryForm>({
  fetcher: (params) => formApi.submissions(params),
  defaultQuery: {form_id: undefined},
})
const subQuery = subTable.query

async function deleteSubmission(row: FormSubmissionItem) {
  await ElMessageBox.confirm(t('admin.marketing.form.deleteSubmissionConfirm'), t('admin.common.notice'), {type: 'warning'})
  await formApi.removeSubmission(row.id)
  ElMessage.success(t('admin.common.delete'))
  await subTable.load()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 表单 -->
        <el-tab-pane :label="$t('admin.marketing.form.tabForms')" name="forms">
          <div class="table-toolbar">
            <el-button v-auth="'module_marketing:form:create'" :icon="Plus" type="primary" @click="openFormCreate">
              {{ $t('admin.marketing.form.createForm') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: formTable.total.value}) }}</span>
          </div>
          <el-table v-loading="formTable.loading.value" :data="formTable.list.value" border stripe>
            <el-table-column :label="$t('admin.common.name')" min-width="140" prop="title"/>
            <el-table-column label="Slug" prop="slug" width="140"/>
            <el-table-column :label="$t('admin.common.status')" width="110">
              <template #default="{ row }">
                <el-tag :type="(row as FormItem).status === 'published' ? 'success' : 'info'" size="small">
                  {{
                    (row as FormItem).status === 'published' ? $t('admin.marketing.form.statusPublished') : (row as FormItem).status === 'closed' ? $t('admin.marketing.form.statusClosed') : $t('admin.marketing.form.statusDraft')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.customPostType.hasArchive')" width="110">
              <template #default="{ row }">
                {{ (row as FormItem).store_submissions ? $t('admin.common.yes') : $t('admin.common.no') }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" width="200">
              <template #default="{ row }">
                <el-button link type="primary" @click="openFields(row as FormItem)">
                  {{ $t('admin.marketing.form.fields') }}
                </el-button>
                <el-button v-auth="'module_marketing:form:edit'" link type="primary"
                           @click="openFormEdit(row as FormItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_marketing:form:delete'" link type="danger"
                           @click="deleteForm(row as FormItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            :current-page="formTable.page.value" :page-size="formTable.pageSize.value" :total="formTable.total.value"
            background class="table-pagination" layout="total, prev, pager, next"
            @current-change="formTable.onPageChange"
          />
        </el-tab-pane>

        <!-- 提交 -->
        <el-tab-pane :label="$t('admin.marketing.form.tabSubmissions')" name="submissions">
          <el-form :inline="true" @submit.prevent="subTable.search()">
            <el-form-item :label="$t('admin.marketing.form.formId')">
              <el-input-number v-model="subQuery.form_id" :min="1" style="width: 140px"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="subTable.search()">{{
                  $t('admin.common.search')
                }}
              </el-button>
              <el-button :icon="Refresh" @click="subTable.reset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>
          <el-table v-loading="subTable.loading.value" :data="subTable.list.value" border stripe>
            <el-table-column :label="$t('admin.marketing.form.formId')" prop="form_id" width="90"/>
            <el-table-column :label="$t('admin.marketing.form.submissionData')" min-width="260" show-overflow-tooltip>
              <template #default="{ row }">
                {{ JSON.stringify((row as FormSubmissionItem).data || {}) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.marketing.vip.startsAt')" prop="created_at" width="170"/>
            <el-table-column :label="$t('admin.common.actions')" width="110">
              <template #default="{ row }">
                <el-button v-auth="'module_marketing:form:delete'" link type="danger"
                           @click="deleteSubmission(row as FormSubmissionItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            :current-page="subTable.page.value" :page-size="subTable.pageSize.value" :total="subTable.total.value"
            background class="table-pagination" layout="total, prev, pager, next"
            @current-change="subTable.onPageChange"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 表单编辑 -->
    <el-drawer v-model="formFormVisible" :title="formFormTitle" destroy-on-close size="460px">
      <el-form :model="formForm" label-width="100px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="formForm.title" :disabled="!!formEditingId"/>
        </el-form-item>
        <el-form-item label="Slug" required>
          <el-input v-model="formForm.slug" :disabled="!!formEditingId"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="formForm.status" style="width: 100%">
            <el-option :label="$t('admin.marketing.form.statusDraft')" value="draft"/>
            <el-option :label="$t('admin.marketing.form.statusPublished')" value="published"/>
            <el-option :label="$t('admin.marketing.form.statusClosed')" value="closed"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="formForm.description" :rows="2" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.form.submitMessage')">
          <el-input v-model="formForm.submit_message"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.form.storeSubmissions')">
          <el-switch v-model="formForm.store_submissions"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.form.emailNotify')">
          <el-switch v-model="formForm.email_notification"/>
        </el-form-item>
        <el-form-item v-if="formForm.email_notification" :label="$t('admin.marketing.form.notifyEmail')">
          <el-input v-model="formForm.notification_email"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="formSaving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 字段管理 -->
    <el-dialog v-model="fieldsVisible" :title="fieldsTitle" destroy-on-close width="720px">
      <div class="mb-2">
        <el-button v-auth="'module_marketing:form:edit'" :icon="Plus" size="small" type="primary"
                   @click="openFieldCreate">
          {{ $t('admin.marketing.form.createField') }}
        </el-button>
      </div>
      <el-table v-loading="fieldsLoading" :data="fieldList" border size="small">
        <el-table-column :label="$t('admin.common.name')" min-width="120" prop="label"/>
        <el-table-column :label="$t('admin.marketing.form.fieldType')" prop="field_type" width="100"/>
        <el-table-column :label="$t('admin.marketing.form.fieldRequired')" width="80">
          <template #default="{ row }">
            {{ (row as FormFieldItem).required ? $t('admin.common.yes') : $t('admin.common.no') }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.marketing.form.fieldOrder')" prop="order_index" width="80"/>
        <el-table-column :label="$t('admin.common.actions')" width="140">
          <template #default="{ row }">
            <el-button link size="small" type="primary" @click="openFieldEdit(row as FormFieldItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button link size="small" type="danger" @click="deleteField(row as FormFieldItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 字段编辑 -->
    <el-dialog v-model="fieldFormVisible"
               :title="fieldEditingId ? $t('admin.marketing.form.editField') : $t('admin.marketing.form.createField')"
               append-to-body width="440px">
      <el-form :model="fieldForm" label-width="90px">
        <el-form-item :label="$t('admin.marketing.form.fieldLabel')" required>
          <el-input v-model="fieldForm.label"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.form.fieldType')">
          <el-select v-model="fieldForm.field_type" style="width: 100%">
            <el-option v-for="tp in ['text', 'textarea', 'email', 'number', 'select', 'checkbox', 'radio', 'date']"
                       :key="tp" :label="tp" :value="tp"/>
          </el-select>
        </el-form-item>
        <el-form-item v-if="['select', 'checkbox', 'radio'].includes(fieldForm.field_type)"
                      :label="$t('admin.marketing.form.fieldOptions')">
          <el-input v-model="fieldForm.options"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.form.fieldRequired')">
          <el-switch v-model="fieldForm.required"/>
        </el-form-item>
        <el-form-item :label="$t('admin.marketing.form.fieldOrder')">
          <el-input-number v-model="fieldForm.order_index" :min="0" style="width: 100%"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fieldFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="fieldSaving" type="primary" @click="submitField">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>
