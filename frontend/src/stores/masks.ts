import { ref } from 'vue'

import { api } from '@/api'
import type { Mask } from '@/types'

// 面具列表被 HomeView 与 MasksView 共享；模块级 ref 保证两个视图看到同一份数据。
const masks = ref<Mask[]>([])
const loading = ref(false)
let inFlight: Promise<void> | null = null

export function useMasks() {
  function loadMasks(): Promise<void> {
    // 并发去重：两个视图同时挂载时只发一次请求。
    if (inFlight) return inFlight
    loading.value = true
    inFlight = api
      .masks()
      .then((envelope) => {
        masks.value = envelope.data
      })
      .finally(() => {
        loading.value = false
        inFlight = null
      })
    return inFlight
  }

  return { masks, loading, loadMasks }
}
