export type NativeDropCallback = (paths: string[]) => void

export function installNativeDropBridge(callback: NativeDropCallback): () => void {
  window.MaskBox = {
    onNativeDrop: (paths: string[]) => callback(paths.filter((p) => Boolean(p))),
  }

  void window.pywebview?.api?.register_drop_zone?.()

  const onDocumentDrop = (event: DragEvent) => {
    const files = Array.from(event.dataTransfer?.files ?? [])
    const paths = files
      .map((file) => {
        const anyFile = file as File & { path?: string; pywebviewFullPath?: string }
        return anyFile.path || anyFile.pywebviewFullPath || ''
      })
      .filter(Boolean)
    if (paths.length === 0) return
    event.preventDefault()
    callback(paths)
  }

  const onDragOver = (event: DragEvent) => {
    event.preventDefault()
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
  }

  document.addEventListener('drop', onDocumentDrop)
  document.addEventListener('dragover', onDragOver)

  return () => {
    document.removeEventListener('drop', onDocumentDrop)
    document.removeEventListener('dragover', onDragOver)
  }
}
