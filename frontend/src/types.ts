export interface Mask {
  id: number
  name: string
  clsid: string | null
  builtin: boolean
  created_at: string
  updated_at: string
}

export interface FolderItem {
  id: number
  path: string
  display_name: string
  hidden: boolean
  mask: Mask | null
  current_path: string
  missing: boolean
  created_at: string
  updated_at: string
}

export interface ApiEnvelope<T> {
  code: number
  msg: string
  data: T
}

export interface FolderPayload {
  path?: string
  display_name?: string
  hidden?: boolean
  mask_id?: number | null
  force?: boolean
}

export interface MaskPayload {
  name?: string
  clsid?: string | null
}
