/**
 * 把任意异常转成能显示给用户的一句话。
 *
 * 契约要求（§3.2）：**判断分支用 code，展示文案才用 message**。
 * 后端 message 是中文短句，可以直接展示；但我们优先用本地文案，
 * 这样后端改文案不会打乱界面，而且能按 code 给出更具体的处理建议。
 */

import { ApiRequestError } from '../api/client'
import { isApiErrorCode, type ApiErrorCode } from '../types/api'

/** 按错误码给出的界面文案。没登记过的码回退到后端 message */
const ERROR_TEXT: Partial<Record<ApiErrorCode, string>> = {
  // 条目
  ENTRY_NOT_FOUND: '条目不存在，可能已被移出库',
  // 资源
  RESOURCE_NOT_FOUND: '资源不存在',
  RESOURCE_LINK_NOT_FOUND: '该条目没有关联此资源',
  RESOURCE_FILE_MISSING: '文件已不在原位置，请重新定位',
  RESOURCE_NOT_FILE: '选中的路径不是文件',
  RESOURCE_PATH_NOT_ABSOLUTE: '路径必须是绝对路径',
  RESOURCE_ACCESS_DENIED: '没有权限访问该文件',
  RESOURCE_ALREADY_LINKED: '这个文件已经关联到此条目',
  RESOURCE_OPEN_FAILED: '系统程序无法打开该文件',
  // 标签
  TAG_CATEGORY_NOT_FOUND: '标签分类不存在',
  TAG_NOT_FOUND: '标签不存在',
  ENTRY_TAG_NOT_FOUND: '条目还没有这个标签',
  TAG_CATEGORY_NAME_DUPLICATED: '分类名称已存在',
  TAG_NAME_DUPLICATED: '该分类下已有同名标签',
  TAG_IN_USE: '该标签仍被条目使用，不能删除',
  TAG_CATEGORY_NOT_EMPTY: '该分类下还有标签，不能删除',
  SYSTEM_CATEGORY_PROTECTED: '系统分类不能修改或删除',
  TAG_NAME_INVALID: '名称不合法，长度需在 1 到 32 之间',
  TAG_CATEGORY_COLOR_INVALID: '颜色格式必须是 #RRGGBB',
  // 评分与评价
  RATING_OUT_OF_RANGE: '评分必须是 1 到 10 的整数',
  ENTRY_REVIEW_TOO_LONG: '评价文字最多 10000 字',
  // 通用
  VALIDATION_ERROR: '请求内容不符合要求',
}

/** 某些错误码建议用户下一步做什么，附在文案后面 */
const ERROR_HINT: Partial<Record<ApiErrorCode, string>> = {
  RESOURCE_FILE_MISSING: '可以点「重新检测」确认，或解除这条关联',
  TAG_IN_USE: '先在各条目上移除这个标签',
  TAG_CATEGORY_NOT_EMPTY: '先把分类下的标签移走或删除',
}

/**
 * 从 422 响应的 details.errors 里取出第一个出错字段。
 *
 * 后端 validation_error_handler 会把 Pydantic 的原始错误放进
 * `details.errors`，形状是 [{ loc: ['body','type'], msg: '...', input: '...' }]。
 * 只显示「请求字段校验失败」没法排查，把字段名与原因带出来才有用。
 */
function validationDetail(details?: Record<string, unknown>): string | null {
  const errors = details?.errors
  if (!Array.isArray(errors) || errors.length === 0) {
    return null
  }
  const first = errors[0] as { loc?: unknown; msg?: unknown; input?: unknown }
  const parts = Array.isArray(first.loc)
    ? first.loc.map((part) => String(part)).filter((part) => part !== 'body')
    : []
  const field = parts.join('.')
  const message = typeof first.msg === 'string' ? first.msg : ''
  const input =
    first.input === undefined || first.input === null
      ? ''
      : `，收到 ${JSON.stringify(first.input)}`

  if (field && message) {
    return `字段 ${field}：${message}${input}`
  }
  return message || null
}

export function describeApiError(error: unknown, fallback: string): string {
  if (error instanceof ApiRequestError) {
    const code = error.code
    const text = isApiErrorCode(code) ? ERROR_TEXT[code] : undefined
    const hint = isApiErrorCode(code) ? ERROR_HINT[code] : undefined
    const base = text ?? error.message

    // 422 把具体字段带出来，否则只看到「请求字段校验失败」无从下手
    const detail = validationDetail(error.details)
    const withDetail = detail ? `${base}｜${detail}` : base
    const withCode = `${withDetail}（${code}）`
    return hint ? `${withCode}\n${hint}` : withCode
  }
  if (error instanceof Error) {
    return `${fallback}（${error.message}）`
  }
  return fallback
}
