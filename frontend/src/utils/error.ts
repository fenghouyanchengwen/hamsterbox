/**
 * 把任意异常转成能显示给用户的一句话。
 *
 * 后端错误体的形状是 { code, message, details }，由 client.ts 抛成 ApiRequestError。
 * 界面上把 code 一起显示出来，排查时可以直接对人说"我这儿报 TAG_NAME_DUPLICATED"。
 */
import { ApiRequestError } from '../api/client'

export function toMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiRequestError) {
    return `${error.code}：${error.message}`
  }
  if (error instanceof Error) {
    return `${fallback}（${error.message}）`
  }
  return fallback
}
