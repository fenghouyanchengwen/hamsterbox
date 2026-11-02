/**
 * 开发阶段用的演示数据。
 *
 * 用途：在后端条目、标签、评分接口就绪前，让界面能显示真实形状的数据。
 * 数据量和形态刻意贴合 Alpha 第一阶段的验收标准：5 个条目、2 个条目各 3 个标签、
 * 其中有标签开启评分，并且留了一个"文件已失效"的资源用于验证部分失效态。
 *
 * config.ts 里 USE_MOCK 改成 false 后，本文件不再被调用，发布前删除。
 */

import type { Entry, Rating, Resource, Tag } from '../types/api'

export const mockTags: Tag[] = [
  { id: 1, name: '剧情', color: '#5B8FF9', rating_enabled: true, entry_count: 5 },
  { id: 2, name: '画面', color: '#61DDAA', rating_enabled: true, entry_count: 3 },
  { id: 3, name: '音乐', color: '#F6BD16', rating_enabled: true, entry_count: 2 },
  { id: 4, name: '收藏', color: '#7262FD', rating_enabled: false, entry_count: 2 },
  { id: 5, name: '待看', color: '#78D3F8', rating_enabled: false, entry_count: 2 },
]

export const mockEntries: Entry[] = [
  {
    id: 1,
    title: '三体（全集）',
    type: '电子书',
    cover: null,
    summary: '刘慈欣的科幻长篇三部曲，从文革背景一直写到宇宙终结。',
    created_at: '2026-10-20T02:10:00Z',
    updated_at: '2026-10-30T09:12:00Z',
    tag_ids: [1, 4],
  },
  {
    id: 2,
    title: '赛博朋克 2077',
    type: '游戏',
    cover: null,
    summary: '夜之城的开放世界角色扮演，主线与支线的叙事密度差异明显。',
    created_at: '2026-10-21T11:30:00Z',
    updated_at: '2026-10-29T15:40:00Z',
    tag_ids: [1, 2, 3],
  },
  {
    id: 3,
    title: '银翼杀手 2049',
    type: '影视',
    cover: null,
    summary: '维伦纽瓦执导的续作，摄影与配乐是主要看点。',
    created_at: '2026-10-22T08:05:00Z',
    updated_at: '2026-10-28T20:00:00Z',
    tag_ids: [2, 3, 5],
  },
  {
    id: 4,
    title: '空洞骑士',
    type: '游戏',
    cover: null,
    summary: '银河恶魔城类独立游戏，地图设计与战斗手感口碑稳定。',
    created_at: '2026-10-23T14:20:00Z',
    updated_at: '2026-10-27T10:30:00Z',
    tag_ids: [1, 2, 5],
  },
  {
    id: 5,
    title: '三体 广播剧 第一季',
    type: '音频',
    cover: null,
    summary: '基于原著的多人广播剧，配音与音效完成度较高。',
    created_at: '2026-10-24T19:45:00Z',
    updated_at: '2026-10-26T09:00:00Z',
    tag_ids: [1, 4],
  },
]

/** 条目 → 评分列表 */
export const mockRatings: Record<number, Rating[]> = {
  1: [{ tag_id: 1, rating: 5, review: '设定密度极高，重读仍然有收获。' }],
  2: [
    { tag_id: 1, rating: 4, review: '支线写得比主线好。' },
    { tag_id: 2, rating: 5, review: '夜之城的灯光是最大卖点。' },
    { tag_id: 3, rating: 4, review: '电台音乐能一直开着听。' },
  ],
  3: [
    { tag_id: 2, rating: 5, review: '每一帧都能当壁纸。' },
    { tag_id: 3, rating: 5, review: '低频用得很克制。' },
  ],
  4: [{ tag_id: 1, rating: null, review: '' }],
  5: [{ tag_id: 1, rating: 4, review: '改编取舍合理。' }],
}

/** 条目 → 资源列表。条目 3 留一个 exists=false 用于验证"部分失效"状态。 */
export const mockResources: Record<number, Resource[]> = {
  1: [
    {
      id: 11,
      entry_id: 1,
      path: 'D:\\Books\\三体全集.epub',
      file_name: '三体全集.epub',
      sha256: '9f2c8a1d4b6e7f30a5c9d2e1b8f4a7c6d3e0b9a8f7c6d5e4b3a2c1d0e9f8a7b6',
      size_bytes: 8_421_376,
      exists: true,
    },
  ],
  2: [
    {
      id: 21,
      entry_id: 2,
      path: 'E:\\Games\\Cyberpunk2077\\setup.exe',
      file_name: 'setup.exe',
      sha256: 'c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6',
      size_bytes: 68_719_476_736,
      exists: true,
    },
    {
      id: 22,
      entry_id: 2,
      path: 'E:\\Games\\Cyberpunk2077\\soundtrack.zip',
      file_name: 'soundtrack.zip',
      sha256: null,
      size_bytes: 1_073_741_824,
      exists: true,
    },
  ],
  3: [
    {
      id: 31,
      entry_id: 3,
      path: 'F:\\Movies\\Blade.Runner.2049.2017.mkv',
      file_name: 'Blade.Runner.2049.2017.mkv',
      sha256: '4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b',
      size_bytes: 14_495_514_624,
      exists: false,
    },
  ],
  4: [],
  5: [
    {
      id: 51,
      entry_id: 5,
      path: 'G:\\Audio\\三体广播剧S1\\01.mp3',
      file_name: '01.mp3',
      sha256: null,
      size_bytes: 41_943_040,
      exists: true,
    },
  ],
}
