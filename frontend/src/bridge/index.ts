/**
 * PyWebView JS 桥的封装。
 *
 * 为什么需要这层：浏览器拿不到文件的真实路径，而本项目要保存绝对路径，
 * 所以选文件、打开文件、保存对话框这些能力必须由 Python 一侧提供。
 *
 * 现状：desktop/launcher.py 还没有挂载 js_api，桥方法尚未实现。
 * 这里先把调用端写好，等成员七、成员八把 Python 侧补齐即可直接接通。
 *
 * 重要：在 http://127.0.0.1:5173 的浏览器里，window.pywebview 永远是 undefined。
 * 因此每个函数都必须在无桥时退化，否则开发阶段界面会直接崩。
 */

/** Python 侧需要暴露的方法，命名以 frontend/README.md 的约定为准。 */
export interface HamsterBoxBridge {
  /** 打开系统文件选择器，返回绝对路径列表 */
  pick_files: () => Promise<string[]>
  /** 用系统默认程序打开某个资源，只接受资源 id，不接受路径 */
  open_resource: (resourceId: number) => Promise<void>
  /** 选择分享包文件，返回绝对路径 */
  pick_package: () => Promise<string | null>
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

/** 桥是否已经就绪，界面可以据此启用/禁用依赖原生的按钮 */
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

/**
 * 选择本地文件。
 * 浏览器环境下返回模拟路径，方便在没有桌面窗口时调界面。
 */
export async function pickFiles(): Promise<string[]> {
  if (!hasBridge()) {
    console.warn('[bridge] 当前不在桌面窗口中，pickFiles 返回模拟路径')
    return ['D:\\Media\\示例文件.mp4']
  }
  return window.pywebview!.api.pick_files()
}

/** 用系统默认程序打开资源。注意只传 resource_id，路径由后端解析。 */
export async function openResource(resourceId: number): Promise<void> {
  if (!hasBridge()) {
    console.warn(`[bridge] 当前不在桌面窗口中，openResource(${resourceId}) 未执行`)
    return
  }
  return window.pywebview!.api.open_resource(resourceId)
}

/** 选择分享包文件。 */
export async function pickPackage(): Promise<string | null> {
  if (!hasBridge()) {
    console.warn('[bridge] 当前不在桌面窗口中，pickPackage 返回 null')
    return null
  }
  return window.pywebview!.api.pick_package()
}
