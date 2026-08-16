<template>
  <section class="home-view">
    <el-alert
      v-if="missingFolders.length > 0"
      :title="t('home.missingTip', { count: missingFolders.length })"
      type="warning"
      show-icon
      closable
      class="missing-alert"
    >
      <template #default>
        <el-button size="small" type="warning" plain @click="removeMissingFolders">
          {{ t('home.removeMissing') }}
        </el-button>
      </template>
    </el-alert>

    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <el-input
          v-model="search"
          :placeholder="t('home.searchPlaceholder')"
          clearable
          class="search-input"
          @keyup.enter="loadFolders"
          @clear="loadFolders"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="sort" class="sort-input" @change="loadFolders">
          <el-option :label="t('home.sortCreated')" value="created_at" />
          <el-option :label="t('home.sortUpdated')" value="updated_at" />
          <el-option :label="t('home.sortName')" value="name" />
          <el-option :label="t('home.sortPath')" value="path" />
          <el-option :label="t('home.sortStatus')" value="status" />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="openAddDialog">
          {{ t('common.add') }}
        </el-button>
        <el-button :icon="Refresh" circle @click="loadFolders" />
      </div>

      <div
        id="drop-zone"
        class="drop-zone"
        :class="{ 'is-dragging': dragDepth > 0 }"
        @dragenter.prevent="dragDepth++"
        @dragleave.prevent="dragDepth--"
        @drop.prevent="dragDepth = 0"
        @dragend="dragDepth = 0"
      >
        <el-icon class="drop-icon"><UploadFilled /></el-icon>
        <span>{{ t('home.dropHint') }}</span>
      </div>

      <div v-if="selection.length > 0" class="batch-bar">
        <span class="batch-text">{{ t('common.selected') }} {{ selection.length }} {{ t('common.items') }}</span>
        <el-button size="small" @click="batchToggle(true)">{{ t('home.batchHide') }}</el-button>
        <el-button size="small" @click="batchToggle(false)">{{ t('home.batchRestore') }}</el-button>
        <el-button size="small" type="danger" plain @click="confirmBatchDelete">
          {{ t('home.batchDelete') }}
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <template v-if="showGuide">
        <el-empty :description="t('home.emptyDesc')" class="guide-empty">
          <el-steps :active="2" finish-status="success" align-center class="guide-steps">
            <el-step :title="t('home.guideStep1')" />
            <el-step :title="t('home.guideStep2')" />
            <el-step :title="t('home.guideStep3')" />
          </el-steps>
          <el-button type="primary" @click="openAddDialog">{{ t('home.startGuide') }}</el-button>
        </el-empty>
      </template>

      <template v-else>
        <el-table
          :data="folders"
          row-key="id"
          border
          stripe
          class="folder-table"
          @selection-change="selection = $event"
        >
          <el-table-column type="selection" width="46" />
          <el-table-column :label="t('home.folder')" min-width="170">
            <template #default="{ row }">
              <span>{{ row.display_name }}</span>
              <span v-if="row.missing" class="missing-name">{{ t('home.missingName') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('home.path')" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">{{ row.path }}</template>
          </el-table-column>
          <el-table-column :label="t('home.status')" width="170">
            <template #default="{ row }">
              <el-tag v-if="row.missing" type="danger" effect="light" round>{{ t('home.missing') }}</el-tag>
              <template v-else>
                <el-tag v-if="row.hidden" type="primary" effect="dark" color="#7c4dff" round>
                  {{ t('home.hiddenBadge') }}
                </el-tag>
                <el-tag v-if="row.mask" type="primary" effect="dark" color="#4d9fff" round>
                  {{ t('home.maskedBadge') }}
                </el-tag>
                <el-tag v-if="!row.hidden && !row.mask" type="success" effect="light" round>
                  {{ t('home.normal') }}
                </el-tag>
              </template>
            </template>
          </el-table-column>
          <el-table-column :label="t('home.mask')" min-width="120">
            <template #default="{ row }">{{ row.mask?.name || '-' }}</template>
          </el-table-column>
          <el-table-column :label="t('home.updatedAt')" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="240" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openEditDialog(row as FolderItem)">
                {{ t('common.edit') }}
              </el-button>
              <el-button size="small" :type="row.hidden ? 'success' : 'warning'" plain @click="toggleHide(row as FolderItem)">
                {{ row.hidden ? t('home.toggleRestore') : t('home.toggleHide') }}
              </el-button>
              <el-popconfirm
                :title="t('home.deleteConfirm', { count: 1 })"
                :confirm-button-text="t('common.confirm')"
                :cancel-button-text="t('common.cancel')"
                @confirm="removeFolder(row as FolderItem)"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>{{ t('common.delete') }}</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :description="t('home.emptyTitle')">
              <el-button type="primary" @click="openAddDialog">{{ t('common.add') }}</el-button>
            </el-empty>
          </template>
        </el-table>
      </template>
    </el-card>

    <FolderDialog
      v-model="dialogVisible"
      :masks="masks"
      :editing="editingRow"
      :submitting="submitting"
      :initial-path="pendingDropPath"
      @submit="submitFolder"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import { Plus, Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

import { api, apiErrorMessage } from '@/api'
import FolderDialog from '@/components/FolderDialog.vue'
import { useMasks } from '@/stores/masks'
import type { FolderItem, FolderPayload } from '@/types'
import { installNativeDropBridge } from '@/utils/native'

const { t } = useI18n()
const folders = ref<FolderItem[]>([])
const loading = ref(false)
const submitting = ref(false)
const search = ref('')
const sort = ref('created_at')
const selection = ref<FolderItem[]>([])
const dialogVisible = ref(false)
const editingRow = ref<FolderItem | null>(null)
const pendingDropPath = ref('')
const dragDepth = ref(0)
let removeNativeBridge: (() => void) | null = null

const { masks, loadMasks: fetchMasks } = useMasks()

const missingFolders = computed(() => folders.value.filter((item) => item.missing))
const showGuide = computed(
  () => folders.value.length === 0 && localStorage.getItem('maskbox.onboarded') !== '1',
)

async function loadFolders(): Promise<void> {
  loading.value = true
  try {
    const envelope = await api.folders(search.value.trim(), sort.value)
    folders.value = envelope.data
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  } finally {
    loading.value = false
  }
}

async function loadMasks(): Promise<void> {
  try {
    await fetchMasks()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  }
}

function openAddDialog(): void {
  editingRow.value = null
  pendingDropPath.value = ''
  dialogVisible.value = true
}

function openEditDialog(row: FolderItem): void {
  editingRow.value = row
  dialogVisible.value = true
}

function applyDroppedPath(path: string): void {
  const trimmed = path.trim()
  if (!trimmed) return
  editingRow.value = null
  pendingDropPath.value = trimmed
  dialogVisible.value = true
  dragDepth.value = 0
}

function onDropPaths(paths: string[]): void {
  if (paths.length > 1) ElMessage.info(t('home.multiDropTip'))
  if (paths[0]) applyDroppedPath(paths[0])
}

function markOnboarded(): void {
  localStorage.setItem('maskbox.onboarded', '1')
}

async function submitFolder(payload: FolderPayload): Promise<void> {
  submitting.value = true
  try {
    if (editingRow.value === null) {
      await api.createFolder(payload)
    } else {
      await api.updateFolder(editingRow.value.id, payload)
    }
    ElMessage.success(t('common.success'))
    dialogVisible.value = false
    markOnboarded()
    await loadFolders()
  } catch (error) {
    const message = apiErrorMessage(error)
    if ((error as { response?: { status?: number } }).response?.status === 409) {
      const detail = (error as { response?: { data?: { data?: { reason?: string } } } }).response?.data?.data
      if (detail?.reason === 'running_program') {
        confirmRunningProgram(payload)
        return
      }
    }
    ElMessage.error(message)
  } finally {
    submitting.value = false
  }
}

async function confirmRunningProgram(payload: FolderPayload): Promise<void> {
  try {
    await ElMessageBox.confirm(t('home.forceConfirmText'), t('home.forceConfirmTitle'), {
      type: 'warning',
      confirmButtonText: t('home.forceConfirmButton'),
      cancelButtonText: t('common.cancel'),
    })
  } catch {
    return
  }
  submitting.value = true
  try {
    const forced = { ...payload, force: true }
    if (editingRow.value === null) {
      await api.createFolder(forced)
    } else {
      await api.updateFolder(editingRow.value.id, forced)
    }
    dialogVisible.value = false
    markOnboarded()
    ElMessage.success(t('common.success'))
    await loadFolders()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function toggleHide(row: FolderItem): Promise<void> {
  try {
    await api.toggleHide(row.id)
    await loadFolders()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  }
}

async function removeFolder(row: FolderItem): Promise<void> {
  try {
    await api.deleteFolder(row.id)
    ElMessage.success(t('common.success'))
    await loadFolders()
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  }
}

async function batchToggle(hidden: boolean): Promise<void> {
  let ok = 0
  let fail = 0
  let skip = 0
  for (const row of selection.value) {
    // 丢失的目标改不了属性；状态已符合的无需请求。
    if (row.missing || row.hidden === hidden) {
      skip++
      continue
    }
    try {
      await api.updateFolder(row.id, { hidden })
      ok++
    } catch {
      fail++
    }
  }
  const summary = t('home.batchSummary', { ok, fail, skip })
  if (fail > 0) ElMessage.warning(summary)
  else ElMessage.success(summary)
  await loadFolders()
}

async function confirmBatchDelete(): Promise<void> {
  try {
    await ElMessageBox.confirm(t('home.deleteConfirm', { count: selection.value.length }), {
      type: 'warning',
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
    })
  } catch {
    return
  }
  for (const row of selection.value) {
    try {
      await api.deleteFolder(row.id)
    } catch (error) {
      ElMessage.error(apiErrorMessage(error))
    }
  }
  await loadFolders()
}

async function removeMissingFolders(): Promise<void> {
  for (const row of missingFolders.value) {
    try {
      await api.deleteFolder(row.id)
    } catch (error) {
      ElMessage.error(apiErrorMessage(error))
    }
  }
  await loadFolders()
}

function formatTime(value: string): string {
  // 后端存的是 UTC ISO 串；必须转成本地时区再显示。
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

onMounted(() => {
  removeNativeBridge = installNativeDropBridge(onDropPaths)
  void loadFolders()
  void loadMasks()
})

onUnmounted(() => {
  removeNativeBridge?.()
})
</script>

<style scoped>
.missing-alert {
  margin-bottom: 14px;
}

.toolbar-card {
  margin-bottom: 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 340px;
}

.sort-input {
  width: 160px;
}

.drop-zone {
  margin-top: 14px;
  border: 1px dashed #c8c9cc;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
  color: #909399;
  background: #fafbfc;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.drop-zone.is-dragging {
  border-color: #7c4dff;
  background: #f4f0ff;
  color: #7c4dff;
}

.drop-icon {
  font-size: 18px;
}

.batch-bar {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-text {
  margin-right: 6px;
  font-weight: 600;
}

.folder-table {
  width: 100%;
}

.guide-empty {
  padding: 26px 0;
}

.guide-steps {
  margin-bottom: 22px;
}

.missing-name {
  color: #f56c6c;
  font-size: 12px;
}
</style>
