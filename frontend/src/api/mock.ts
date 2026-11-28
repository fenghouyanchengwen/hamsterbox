/**
 * 开发阶段用的演示数据。
 *
 * 用途：在 GET /api/entries 等接口就绪前，让界面能显示真实形状的数据。
 * 数据形态刻意贴合当前契约：
 * - 条目类型用英文枚举，界面显示中文
 * - 标签分两级：分类带颜色，标签只有名字
 * - 评分是 1 至 10
 * - 资源用 availability 表示状态，且**不含绝对路径**
 * - 留了一个 availability='missing' 的资源用于验证"部分失效"
 *
 * config.ts 里 USE_MOCK 改成 false 后本文件不再被调用，发布前删除。
 */

import type {
  Entry,
  EntryTag,
  Resource,
  Tag,
  TagCategory,
} from '../types/api'

const CREATED_AT = '2026-10-20T02:10:00Z'

export const mockCategories: TagCategory[] = [
  {
    id: 1,
    name: '内容题材',
    color: '#5B8FF9',
    sort_order: 10,
    system_key: null,
    created_at: CREATED_AT,
    updated_at: CREATED_AT,
  },
  {
    id: 2,
    name: '进度与状态',
    color: '#61DDAA',
    sort_order: 20,
    system_key: null,
    created_at: CREATED_AT,
    updated_at: CREATED_AT,
  },
  {
    id: 3,
    // 系统分类：不可删除，名称固定
    name: '未分类标签',
    color: null,
    sort_order: 999,
    system_key: 'uncategorized',
    created_at: CREATED_AT,
    updated_at: CREATED_AT,
  },
]

export const mockTags: Tag[] = [
  { id: 11, category_id: 1, name: '科幻', created_at: CREATED_AT, updated_at: CREATED_AT },
  { id: 12, category_id: 1, name: '剧情', created_at: CREATED_AT, updated_at: CREATED_AT },
  { id: 13, category_id: 1, name: '画面', created_at: CREATED_AT, updated_at: CREATED_AT },
  { id: 21, category_id: 2, name: '已通关', created_at: CREATED_AT, updated_at: CREATED_AT },
  { id: 22, category_id: 2, name: '待看', created_at: CREATED_AT, updated_at: CREATED_AT },
]

export const mockEntries: Entry[] = [
  {
    id: 1,
    share_id: 'a19d1060-7288-4c86-a2e7-3340c7c58be1',
    title: '三体（全集）',
    type: 'book',
    description: '刘慈欣的科幻长篇三部曲，从文革背景一直写到宇宙终结。',
    cover_path: null,
    review: '设定密度极高，重读仍然有收获。',
    lifecycle_state: 'library',
    created_at: '2026-10-20T02:10:00Z',
    updated_at: '2026-10-30T09:12:00Z',
  },
  {
    id: 2,
    share_id: 'b29e2171-8399-4d97-b3f8-4451d8d69cf2',
    title: '赛博朋克 2077',
    type: 'game',
    description: '夜之城的开放世界角色扮演，主线与支线的叙事密度差异明显。',
    cover_path: null,
    review: '支线写得比主线好，夜之城的灯光是最大卖点。',
    lifecycle_state: 'library',
    created_at: '2026-10-21T11:30:00Z',
    updated_at: '2026-10-29T15:40:00Z',
  },
  {
    id: 3,
    share_id: 'c30f3282-9400-4ea8-c409-5562e9e70d03',
    title: '银翼杀手 2049',
    type: 'video',
    description: '维伦纽瓦执导的续作，摄影与配乐是主要看点。',
    cover_path: null,
    review: null,
    lifecycle_state: 'library',
    created_at: '2026-10-22T08:05:00Z',
    updated_at: '2026-10-28T20:00:00Z',
  },
  {
    id: 4,
    share_id: 'd41a4393-a511-4fb9-d510-6673f0f81e14',
    title: '空洞骑士',
    type: 'game',
    description: '银河恶魔城类独立游戏，地图设计与战斗手感口碑稳定。',
    cover_path: null,
    review: null,
    lifecycle_state: 'library',
    created_at: '2026-10-23T14:20:00Z',
    updated_at: '2026-10-27T10:30:00Z',
  },
  {
    id: 5,
    share_id: 'e52b54a4-b622-4ac0-e621-7784a1092f25',
    title: '三体 广播剧 第一季',
    type: 'audio',
    description: '基于原著的多人广播剧，配音与音效完成度较高。',
    cover_path: null,
    review: '改编取舍合理。',
    lifecycle_state: 'library',
    created_at: '2026-10-24T19:45:00Z',
    updated_at: '2026-10-26T09:00:00Z',
  },
]

/** 条目 → 标签关系（不含评分），评分在 mockEntryTagRatings 里 */
export const mockEntryTagLinks: Record<number, number[]> = {
  1: [11, 12],
  2: [11, 12, 13],
  3: [12, 13],
  4: [11, 13, 21],
  5: [11, 22],
}

/** 条目 → 标签 → 评分（1 至 10） */
export const mockEntryTagRatings: Record<number, Record<number, number | null>> = {
  1: { 11: 9, 12: 8 },
  2: { 11: 8, 12: 7, 13: 10 },
  3: { 12: 7, 13: 10 },
  4: { 11: 8, 13: 9, 21: 10 },
  5: { 11: 7, 22: null },
}

/** 条目 → 资源。条目 3 留一个 missing 用于验证"部分失效" */
export const mockResources: Record<number, Resource[]> = {
  1: [
    {
      id: 101,
      share_id: 'f63c65b5-c733-4bd1-f732-8895b21a3f36',
      entry_id: 1,
      file_name: '三体全集.epub',
      extension: '.epub',
      size_bytes: 8_421_376,
      mtime_ns: 1_730_000_000_000_000_000,
      sha256: '9f2c8a1d4b6e7f30a5c9d2e1b8f4a7c6d3e0b9a8f7c6d5e4b3a2c1d0e9f8a7b6',
      availability: 'present',
    },
  ],
  2: [
    {
      id: 201,
      share_id: 'a74d76c6-d844-4ce2-a843-99a6c32b4a47',
      entry_id: 2,
      file_name: 'setup.exe',
      extension: '.exe',
      size_bytes: 68_719_476_736,
      mtime_ns: 1_731_000_000_000_000_000,
      sha256: 'c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6',
      availability: 'present',
    },
    {
      id: 202,
      share_id: 'b85e87d7-e955-4df3-b954-aab7d43c5b58',
      entry_id: 2,
      file_name: 'soundtrack.zip',
      extension: '.zip',
      size_bytes: 1_073_741_824,
      mtime_ns: 1_731_100_000_000_000_000,
      sha256: null,
      availability: 'present',
    },
  ],
  3: [
    {
      id: 301,
      share_id: 'c96f98e8-fa66-4ea4-ca65-bbc8e54d6c69',
      entry_id: 3,
      file_name: 'Blade.Runner.2049.2017.mkv',
      extension: '.mkv',
      size_bytes: 14_495_514_624,
      mtime_ns: 1_731_200_000_000_000_000,
      sha256: '4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b',
      availability: 'missing',
    },
  ],
  4: [],
  5: [
    {
      id: 501,
      share_id: 'd07a09f9-0b77-4fb5-db76-ccd0f65e7d7a',
      entry_id: 5,
      file_name: '01.mp3',
      extension: '.mp3',
      size_bytes: 41_943_040,
      mtime_ns: 1_731_300_000_000_000_000,
      sha256: null,
      availability: 'present',
    },
  ],
}

/** 生成 share_id 用的简易 UUID，避免依赖 crypto 在旧 webview 里缺失 */
export function newShareId(): string {
  const hex = '0123456789abcdef'
  let out = ''
  for (let i = 0; i < 32; i += 1) {
    out += hex[Math.floor(Math.random() * 16)]
    if (i === 7 || i === 11 || i === 15 || i === 19) {
      out += '-'
    }
  }
  return out
}

/** 把内部存储的关系拼成接口返回的 EntryTag */
export function buildEntryTags(entryId: number): EntryTag[] {
  const tagIds = mockEntryTagLinks[entryId] ?? []
  const ratings = mockEntryTagRatings[entryId] ?? {}
  const result: EntryTag[] = []
  for (const tagId of tagIds) {
    const tag = mockTags.find((item) => item.id === tagId)
    if (!tag) {
      continue
    }
    result.push({
      entry_id: entryId,
      tag_id: tag.id,
      tag_name: tag.name,
      category_id: tag.category_id,
      rating: ratings[tag.id] ?? null,
      created_at: CREATED_AT,
      updated_at: CREATED_AT,
    })
  }
  return result
}
