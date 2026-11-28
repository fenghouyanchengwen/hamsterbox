/**
 * PyWebView JS 桥的封装。
 *
 * 为什么需要这层：浏览器拿不到文件的真实路径，而本项目要保存绝对路径，
 * 所以选文件、打开文件、保存对话框这些能力必须由 Python 一侧提供。
 *
 * 后端实现：backend/app/adapters/bridge.py 的 NativeBridge，
 * 已在 desktop/launcher.py 通过 `js_api=bridge` 挂载（PR #49）。
 *
 * 重要：在 http://127.0.0.1:5173 的浏览器里 window.pywebview 永远是 undefined，
 * 因此每个函数都必须在无桥时退化，否则开发阶段界面会直接崩。
 *
 * 约定：打开类方法统一返回 { ok, error?, message? }，不抛异常，
 * 由调用方根据 ok 决定是否提示；error 与后端 HTTP 错误码同一套语义。
 */

/**
 * 桥的业务方法返回结果。
 *
 * Python 侧返回 {"ok": True} 或 {"ok": False, "error": "...", "message": "..."}。
 */
export interface BridgeResult {
  ok: boolean
  error?: string
  message?: string
}

/**
 * Python 侧 NativeBridge 暴露的方法。
 *
 * 必须与 backend/app/adapters/bridge.py 的公开方法一一对应：
 * 后端没有的方法不要在这里声明，否则运行时会得到 undefined。
 *
 * 注意：可执行文件的二次确认已由后端在 open_resource 内部用原生对话框完成，
 * 因此不再单独提供 confirm_open_executable。
 */
export interface HamsterBoxBridge {
  /** 打开文件选择器，返回绝对路径列表；取消返回空数组 */
  pick_files: () => Promise<string[]>
  /** 选择文件夹；取消返回 null */
  pick_folder: () => Promise<string | null>
  /** 选择分享包文件；取消返回 null */
  pick_package: () => Promise<string | null>
  /** 另存为对话框，返回目标路径；取消返回 null */
  choose_save_path: () => Promise<string | null>
  /** 用系统默认程序打开资源；只接受 resource_id，路径由后端解析 */
  open_resource: (resourceId: number) => Promise<BridgeResult>
  /** 在文件管理器中定位资源 */
  reveal_resource: (resourceId: number) => Promise<BridgeResult>
}

declare global {
  interface Window {
    pywebview?: {
      api: HamsterBoxBridge
    }
  }
}

/** 当前是否运行在 PyWebView 窗口里（而不是普通浏览器） */
export function hasBridge(): boolean {
  return typeof window.pywebview !== 'undefined'
}

/** 等桥就绪。界面可以据此启用/禁用依赖原生的按钮 */
export function waitForBridge(timeoutMs = 3000): Promise<boolean> {
  if (hasBridge()) {
    return Promise.resolve(true)
  }
  return new Promise((resolve) => {
    const timer = window.setTimeout(() => resolve(false), timeoutMs)
    window.addEventListener(
      'pywebviewready',
      () => {
        window.clearTimeout(timer)
        resolve(true)
      },
      { once: true },
    )
  })
}

/** 选择本地文件。浏览器环境下返回模拟路径，方便没有桌面窗口时调界面 */
export async function pickFiles(): Promise<string[]> {
  if (!hasBridge()) {
    console.warn('[bridge] 当前不在桌面窗口中，pickFiles 返回模拟路径')
    return ['D:\\Media\\示例文件.mp4']
  }
  return window.pywebview!.api.pick_files()
}

/** 选择文件夹。浏览器环境下返回 null */
export async function pickFolder(): Promise<string | null> {
  if (!hasBridge()) {
    console.warn('[bridge] 当前不在桌面窗口中，pickFolder 返回 null')
    return null
  }
  return window.pywebview!.api.pick_folder()
}

/** 选择分享包文件。浏览器环境下返回 null */
export async function pickPackage(): Promise<string | null> {
  if (!hasBridge()) {
    console.warn('[bridge] 当前不在桌面窗口中，pickPackage 返回 null')
    return null
  }
  return window.pywebview!.api.pick_package()
}

/** 另存为对话框。浏览器环境下返回 null */
export async function chooseSavePath(): Promise<string | null> {
  if (!hasBridge()) {
    console.warn('[bridge] 当前不在桌面窗口中，chooseSavePath 返回 null')
    return null
  }
  return window.pywebview!.api.choose_save_path()
}

/**
 * 打开资源。只传 resource_id，路径由后端解析（契约 §6）。
 *
 * 不抛异常：后端拒绝时返回 { ok: false, error, message }，
 * 可执行文件的二次确认由后端弹原生对话框，用户取消同样走这个分支。
 */
export async function openResource(resourceId: number): Promise<BridgeResult> {
  if (!hasBridge()) {
    console.warn(`[bridge] 当前不在桌面窗口中，openResource(${resourceId}) 未执行`)
    return { ok: false, error: 'BRIDGE_UNAVAILABLE', message: '当前不在桌面窗口中' }
  }
  return window.pywebview!.api.open_resource(resourceId)
}

/** 在文件管理器中定位资源 */
export async function revealResource(resourceId: number): Promise<BridgeResult> {
  if (!hasBridge()) {
    return { ok: false, error: 'BRIDGE_UNAVAILABLE', message: '当前不在桌面窗口中' }
  }
  return window.pywebview!.api.reveal_resource(resourceId)
}
