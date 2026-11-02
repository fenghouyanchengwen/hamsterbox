/**
 * 全局开关。
 *
 * USE_MOCK = true  时，所有业务请求都返回 api/mock.ts 里的演示数据，不发网络请求。
 *                  后端条目接口就绪后，把它改成 false，其余代码一行都不用动。
 *
 * 提醒：演示数据只用于开发阶段，发布前必须确认它是 false 且 mock 文件已删除。
 */
export const USE_MOCK = true

/** 演示数据模拟的网络延迟，用来验证加载态（骨架屏）是否正常 */
export const MOCK_LATENCY_MS = 300
