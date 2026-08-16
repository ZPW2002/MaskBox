/// <reference types="vite/client" />

declare interface Window {
  pywebview?: {
    api?: {
      select_folder?: () => Promise<{ ok: boolean; path?: string; folder?: string; error?: string }>
      register_drop_zone?: () => Promise<boolean>
      app_version?: () => Promise<string>
    }
  }
  MaskBox?: {
    onNativeDrop?: (paths: string[]) => void
  }
}
