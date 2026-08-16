<template>
  <el-dialog
    :model-value="modelValue"
    :title="editing === null ? t('home.addDialogTitle') : t('home.editDialogTitle')"
    width="560px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-width="110px">
      <el-form-item :label="t('home.path')">
        <el-input
          :model-value="folderForm.path"
          readonly
          @click="editing === null ? selectNativeFolder() : undefined"
        >
          <template #append>
            <el-button v-if="editing === null" @click="selectNativeFolder">
              {{ t('home.selectFolder') }}
            </el-button>
          </template>
        </el-input>
      </el-form-item>
      <el-form-item :label="t('home.displayName')">
        <el-input v-model="folderForm.display_name" maxlength="255" />
      </el-form-item>
      <el-form-item :label="t('home.hiddenSwitch')">
        <el-switch v-model="folderForm.hidden" />
      </el-form-item>
      <el-form-item :label="t('home.maskLabel')">
        <el-select v-model="folderForm.mask_id" clearable :placeholder="t('home.noMask')">
          <el-option
            v-for="mask in masks"
            :key="mask.id"
            :label="mask.name + (mask.clsid ? '' : ' *')"
            :value="mask.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ t('common.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import { useI18n } from 'vue-i18n'

import { apiErrorMessage } from '@/api'
import type { FolderItem, FolderPayload, Mask } from '@/types'

const props = defineProps<{
  modelValue: boolean
  masks: Mask[]
  editing: FolderItem | null
  submitting: boolean
  /** 添加模式下预填的路径（拖拽传入）。 */
  initialPath?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit', payload: FolderPayload): void
}>()

const { t } = useI18n()

const folderForm = reactive<{
  path: string
  display_name: string
  hidden: boolean
  mask_id: number | null
}>({
  path: '',
  display_name: '',
  hidden: false,
  mask_id: null,
})

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) initForm()
  },
)

function initForm(): void {
  if (props.editing) {
    Object.assign(folderForm, {
      path: props.editing.path,
      display_name: props.editing.display_name,
      hidden: props.editing.hidden,
      mask_id: props.editing.mask?.id ?? null,
    })
    return
  }
  const dropped = (props.initialPath ?? '').trim()
  const parts = dropped.split(/[\\/]/).filter(Boolean)
  Object.assign(folderForm, {
    path: dropped,
    display_name: parts[parts.length - 1] || dropped,
    hidden: false,
    mask_id: null,
  })
}

async function selectNativeFolder(): Promise<void> {
  const picker = window.pywebview?.api?.select_folder
  if (!picker) {
    const manual = window.prompt(t('home.path'))
    if (manual) {
      folderForm.path = manual.trim()
      folderForm.display_name = manual.trim().split(/[\\/]/).filter(Boolean).pop() || manual.trim()
    }
    return
  }
  try {
    const result = await picker()
    if (!result.ok || !result.path) return
    folderForm.path = result.path
    folderForm.display_name = result.folder || folderForm.path.split(/[\\/]/).pop() || result.path
  } catch (error) {
    ElMessage.error(apiErrorMessage(error))
  }
}

function submit(): void {
  if (!folderForm.path) {
    ElMessage.warning(t('home.dropHint'))
    return
  }
  emit('submit', {
    path: folderForm.path,
    display_name: folderForm.display_name,
    hidden: folderForm.hidden,
    mask_id: folderForm.mask_id,
  })
}
</script>
