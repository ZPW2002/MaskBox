<template>
  <section class="masks-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <div class="title">{{ t('masks.title') }}</div>
            <div class="desc">{{ t('masks.desc') }}</div>
          </div>
          <el-button type="primary" :icon="Plus" @click="openCreate">
            {{ t('masks.addMask') }}
          </el-button>
        </div>
      </template>

      <el-table :data="masks" v-loading="loading" border stripe>
        <el-table-column :label="t('masks.name')" min-width="160">
          <template #default="{ row }">{{ row.name }}</template>
        </el-table-column>
        <el-table-column :label="t('masks.clsid')" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">{{ row.clsid || '—' }}</template>
        </el-table-column>
        <el-table-column :label="t('common.sort')" width="120">
          <template #default="{ row }">
            <el-tag :type="row.builtin ? 'info' : 'success'" effect="plain" round>
              {{ row.builtin ? t('common.builtin') : t('common.custom') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="200">
          <template #default="{ row }">
            <template v-if="!row.builtin">
              <el-button size="small" @click="openEdit(row as Mask)">{{ t('common.edit') }}</el-button>
              <el-popconfirm
                :title="t('masks.deleteConfirm', { name: row.name })"
                :confirm-button-text="t('common.confirm')"
                :cancel-button-text="t('common.cancel')"
                @confirm="removeMask(row as Mask)"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>{{ t('common.delete') }}</el-button>
                </template>
              </el-popconfirm>
            </template>
            <span v-else class="builtin-tip">{{ t('masks.builtinTip') }}</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('masks.empty')" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? t('masks.addMask') : t('masks.editMask')"
      width="520px"
      destroy-on-close
    >
      <el-form label-width="90px">
        <el-form-item :label="t('masks.name')" required>
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item :label="t('masks.clsid')">
          <el-input
            v-model="form.clsid"
            :placeholder="t('masks.clsidPlaceholder')"
            @blur="normalizeGuid"
          />
          <div class="guid-hint">{{ t('masks.clsidHint') }}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import { Plus } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

import { api, apiErrorMessage } from '@/api'
import { useMasks } from '@/stores/masks'
import type { Mask } from '@/types'

const { t } = useI18n()
const { masks, loading, loadMasks: fetchMasks } = useMasks()
const submitting = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<{ name: string; clsid: string }>({ name: '', clsid: '' })

async function loadMasks(): Promise<void> {
  try {
    await fetchMasks()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  }
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, { name: '', clsid: '' })
  dialogVisible.value = true
}

function openEdit(row: Mask): void {
  editingId.value = row.id
  Object.assign(form, { name: row.name, clsid: row.clsid || '' })
  dialogVisible.value = true
}

function normalizeGuid(): void {
  const value = form.clsid.trim()
  if (!value) return
  const pattern = /^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$/
  if (pattern.test(value)) {
    form.clsid = value.startsWith('{') ? value : `{${value}}`
  }
}

async function submit(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.warning(t('masks.name'))
    return
  }
  const clsid = form.clsid.trim()
  if (clsid) {
    const pattern = /^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$/
    if (!pattern.test(clsid)) {
      ElMessage.error(t('masks.invalidGuid'))
      return
    }
  }
  submitting.value = true
  try {
    if (editingId.value === null) {
      await api.createMask({ name: form.name.trim(), clsid: clsid || null })
    } else {
      await api.updateMask(editingId.value, { name: form.name.trim(), clsid: clsid || null })
    }
    ElMessage.success(t('common.success'))
    dialogVisible.value = false
    await loadMasks()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function removeMask(row: Mask): Promise<void> {
  try {
    await api.deleteMask(row.id)
    ElMessage.success(t('common.success'))
    await loadMasks()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  }
}

onMounted(() => {
  void loadMasks()
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 16px;
  font-weight: 700;
}

.desc {
  margin-top: 4px;
  color: #909399;
  font-size: 13px;
}

.builtin-tip {
  color: #909399;
  font-size: 12px;
}

.guid-hint {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}
</style>
