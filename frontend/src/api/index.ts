import axios, { AxiosError } from 'axios'

import type { ApiEnvelope, FolderItem, FolderPayload, Mask, MaskPayload } from '@/types'
import { i18n } from '@/i18n'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  config.headers['X-Lang'] = i18n.global.locale.value
  config.headers['Content-Type'] = 'application/json;charset=utf-8'
  return config
})

function unwrap<T>(response: { data: ApiEnvelope<T> }): ApiEnvelope<T> {
  return response.data
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as { msg?: string; detail?: string } | undefined
    if (data?.msg) return data.msg
    if (data?.detail) return data.detail
    if (error.code === 'ECONNABORTED' || !error.response) {
      return i18n.global.t('api.network')
    }
  }
  if (error instanceof Error && error.message) return error.message
  return i18n.global.t('api.badRequest')
}

export const api = {
  folders: (search = '', sort = 'created_at') =>
    http.get<ApiEnvelope<FolderItem[]>>('/api/folders', { params: { search, sort } }).then(unwrap),
  createFolder: (payload: FolderPayload) =>
    http.post<ApiEnvelope<FolderItem>>('/api/folders', payload).then(unwrap),
  updateFolder: (id: number, payload: FolderPayload) =>
    http.patch<ApiEnvelope<FolderItem>>(`/api/folders/${id}`, payload).then(unwrap),
  deleteFolder: (id: number) =>
    http.delete<ApiEnvelope<{ id: number }>>(`/api/folders/${id}`).then(unwrap),
  toggleHide: (id: number) =>
    http.post<ApiEnvelope<FolderItem>>(`/api/folders/${id}/toggle-hide`, {}).then(unwrap),
  masks: () => http.get<ApiEnvelope<Mask[]>>('/api/masks').then(unwrap),
  createMask: (payload: MaskPayload) =>
    http.post<ApiEnvelope<Mask>>('/api/masks', payload).then(unwrap),
  updateMask: (id: number, payload: MaskPayload) =>
    http.patch<ApiEnvelope<Mask>>(`/api/masks/${id}`, payload).then(unwrap),
  deleteMask: (id: number) =>
    http.delete<ApiEnvelope<{ id: number }>>(`/api/masks/${id}`).then(unwrap),
}
