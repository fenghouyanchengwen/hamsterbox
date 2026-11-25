# 成员六任务清单（按当前接口）

| 项目 | 内容 |
|---|---|
| 用途 | 把成员六的前端任务对齐到仓库当前已实现/已冻结的接口，可直接拆成 Issue |
| 负责人 | 成员六：界面与交互 |
| 状态 | 依据 `main` 分支 f1af8a3，待成员五评审 |
| 最后更新 | 2026-11-07 |
| 依据契约 | `docs/api/entries-resources.md`、`docs/tag-rating-contract.md`、`backend/app/api/README.md` |

---

## 0　现状：前端骨架落后接口两个版本

`frontend/src/` 还停在 10 月 31 日的骨架，后端在 11 月 2 日和 11 月 7 日各冻结了一次契约。**当前前端代码调用的路径、字段名、评分范围全部对不上**，所以第一优先级不是加功能，是把契约对齐。

主要差异：

| 前端现在以为 | 实际约定 |
|---|---|
| `Entry.summary` / `Entry.cover` | `description` / `cover_path` |
| 无 | `share_id`、`review`、`lifecycle_state` |
| `type` 是中文（电子书、影视…） | 英文枚举 `game`/`book`/`video`/`audio`/`image`/`model`/`other` |
| `Tag{color, rating_enabled}` 一层 | `TagCategory{color, sort_order, system_key}` → `Tag{category_id, name}` 两层 |
| 评分 1–5，五颗星 | 评分 `null` 或 **1–10** |
| `/api/entries/{id}/ratings/{tag_id}` | `/api/entries/{id}/tags/{tag_id}` |
| `Resource.exists: boolean` | `availability: "present"` / `"missing"`，另有 `extension`、`mtime_ns`、`share_id` |
| `getEntryResources()` 返回 `Resource[]` | 返回 `{items, total}` |
| `Entry.tag_ids` | 没有这个字段，标签要单独调 `/api/entries/{id}/tags` |

### 三个硬阻塞

| 阻塞 | 卡住什么 | 找谁 |
|---|---|---|
| `GET /api/entries` 不存在 | 列表页、关键词搜索、标签筛选全部无法接真数据 | 成员四（该接口归他） |
| `review` 字段没进 Pydantic 模型 | 整体评价能显示不能保存 | 成员二 |
| `launcher.py` 没挂 `js_api` | 选文件、打开文件在桌面窗口里全都不工作 | 成员八 |

---

## 1　任务总表

估点单位为「天」，一个 Issue 不超过 2 天。**状态**：⬜ 可开工 / 🟡 部分完成 / ⛔ 被阻塞 / ✅ 已完成。

### Alpha 一阶段（0.1.0）

| 编号 | 标题 | 对应接口 | 估点 | 状态 |
|---|---|---|---|---|
| T6-01 | `[ui] 按冻结契约重写类型与 API 客户端` | 全部已实现接口 | 2 | ✅ 2026-11-07 |
| T6-02 | `[ui] 评分控件改为 1 至 10 分` | `PUT /api/entries/{id}/tags/{tag_id}` | 0.5 | 🟡 功能已就位，剩打磨 |
| T6-03 | `[ui] 条目标签与评分面板` | `GET` / `PUT` / `DELETE /api/entries/{id}/tags` | 2 | ⬜ |
| T6-04 | `[ui] 条目表单与类型中文映射` | `POST` / `PATCH /api/entries` | 1 | 🟡 映射与表单已就位，编辑功能待补 |
| T6-05 | `[ui] 资源面板接 availability 与重新检测` | `GET /resources`、`POST /resources/{rid}/recheck`、`DELETE` | 1.5 | 🟡 状态显示已就位，重新检测与解绑待补 |
| T6-06 | `[ui] 条目整体评价输入框` | `PATCH /api/entries/{id}` 的 `review` | 1 | ⛔ 等成员二 |
| T6-07 | `[ui] 列表页接真实接口` | `GET /api/entries` | 1.5 | ⛔ 等成员四 |
| T6-08 | `[ui] 桥接层对齐真实返回值` | JS 桥 | 1 | ⛔ 等成员八 |

> T6-01 完成情况（2026-11-07）：`types/api.ts`、`api/client.ts`、`api/mock.ts`、`bridge/index.ts`
> 已按冻结契约重写，`components/`、`views/`、`App.vue` 同步改完，构建与 `vue-tsc` 均通过。
> 认证方式：`vite build` 51 模块通过，`vue-tsc --noEmit` 退出码 0。
> 顺带完成的部分：`RatingStars.vue` 已由 `RatingScale.vue` 取代（1–10 分）；
> 类型中文映射抽到 `constants/labels.ts`；错误码文案抽到 `utils/error.ts`。
> **仍未做**：条目编辑表单、条目上标签的增删（只做了评分编辑）、资源的重新检测与解绑、
> 列表页真实接口。这些对应 T6-03、T6-04、T6-05、T6-07。

### Alpha 二阶段（0.2.0）

| 编号 | 标题 | 对应接口 | 估点 | 状态 |
|---|---|---|---|---|
| T6-09 | `[ui] 标签分类与标签管理界面` | `GET`/`POST`/`PATCH`/`DELETE /api/tag-categories`、`/api/tags` | 2 | ⬜ |
| T6-10 | `[ui] 分享包导出界面` | `POST /api/share/export` | 2 | ⛔ 等成员五 |
| T6-11 | `[ui] 分享包导入预览页` | `POST /api/share/preview`、`/import` | 2 | ⛔ 等成员五 |
| T6-12 | `[ui] 设置页：库文件位置与重建索引` | 接口尚未定义 | 1.5 | ⛔ 等接口 |
| T6-13 | `[ui] 统一控件样式` | 无 | 1 | ⬜ |

**Alpha 一最小路径**：T6-01 → T6-02 → T6-03 → T6-04 → T6-05 → T6-07。T6-06 和 T6-08 解冻后插入。T6-09 不在 Alpha 一必需范围内——系统"未分类标签"分类和种子分类由后端预置，没有管理界面也能打标签。

---

## 2　任务详细卡

### T6-01　按冻结契约重写类型与 API 客户端

**目标**：让 `frontend/src/types/api.ts` 和 `api/client.ts` 与后端 domain 模型逐字段一致，后续所有界面工作都建立在正确的类型上。

**要改的文件**：`types/api.ts`、`api/client.ts`、`api/mock.ts`、`bridge/index.ts`、`views/EntryDetailView.vue`、`views/LibraryView.vue`、`components/EntryCard.vue`、`components/TagChip.vue`

**验收标准**：

- [ ] `Entry`：`id`、`share_id`、`title`、`type: EntryType`、`description: string | null`、`cover_path: string | null`、`created_at`、`updated_at`
- [ ] `EntryType` 为联合类型 `'game' | 'book' | 'video' | 'audio' | 'image' | 'model' | 'other'`
- [ ] `Resource`：`id`、`share_id`、`entry_id`、`file_name`、`extension`、`size_bytes`、`mtime_ns`、`sha256`、`availability: 'present' | 'missing'`（**不含 `path`**，契约明令不返回绝对路径）
- [ ] `ResourceList` 为 `{ items: Resource[]; total: number }`
- [ ] `TagCategory`：`id`、`name`、`color: string | null`、`sort_order`、`system_key: string | null`、`created_at`、`updated_at`
- [ ] `Tag`：`id`、`category_id`、`name`、`created_at`、`updated_at`（**没有 color，没有 rating_enabled**）
- [ ] `EntryTag`：`entry_id`、`tag_id`、`tag_name`、`category_id`、`rating: number | null`、`created_at`、`updated_at`
- [ ] 评分范围常量集中定义，取值 1–10
- [ ] 错误码写成常量联合类型，覆盖 `ENTRY_NOT_FOUND`、`TAG_CATEGORY_NOT_FOUND`、`TAG_NOT_FOUND`、`ENTRY_TAG_NOT_FOUND`、`TAG_CATEGORY_NAME_DUPLICATED`、`TAG_NAME_DUPLICATED`、`TAG_IN_USE`、`TAG_CATEGORY_NOT_EMPTY`、`SYSTEM_CATEGORY_PROTECTED`、`TAG_NAME_INVALID`、`TAG_CATEGORY_COLOR_INVALID`、`RATING_OUT_OF_RANGE`、`ENTRY_REVIEW_TOO_LONG`、`RESOURCE_*` 系列
- [ ] 每个已实现接口都有对应函数，路径与 `backend/app/api/README.md` 一致
- [ ] `npm run type-check` 无输出

**注意**：错误码是稳定标识，**判断分支一律用 `code`，不要用 `message`**（契约第 3.2 节明确要求）。

---

### T6-02　评分控件改为 1 至 10 分

**目标**：`RatingStars.vue` 改为 10 档评分控件，与 1–10 契约一致。

**验收标准**：

- [ ] 组件重命名为 `RatingScale.vue`（原名会误导后来的人）
- [ ] 能选 1–10，选中的档位高亮
- [ ] 点当前分数取消评分，提交 `null`
- [ ] `rating === null` 时显示"未评分"
- [ ] 半星/浮点值一律不出现，只接受整数
- [ ] 组件不自己发请求，只通过 `change` 事件向上报值（保持现有受控模式）
- [ ] 详情页里评分越界时，把后端 `RATING_OUT_OF_RANGE` 显示成提示

---

### T6-03　条目标签与评分面板

**目标**：详情页能添加标签、移除标签、给每个标签打 1–10 分。

**对应接口**：

| 操作 | 接口 |
|---|---|
| 读取条目已有关联 | `GET /api/entries/{id}/tags` |
| 添加标签 / 改评分 | `PUT /api/entries/{id}/tags/{tag_id}`，请求体 `{"rating": 9}` 或 `{"rating": null}` |
| 移除标签 | `DELETE /api/entries/{id}/tags/{tag_id}` |

**验收标准**：

- [ ] 详情页列出该条目所有标签，按分类分组显示，分组用分类的本地颜色
- [ ] "添加标签"从现有标签里挑，可跨分类搜索
- [ ] 添加标签允许只关联不评分（提交 `{"rating": null}`）
- [ ] `PUT` 是幂等更新：已有关系再次 `PUT` 只改评分，不报错
- [ ] 移除标签只删关系，标签定义仍在（`DELETE` 返回 204）
- [ ] 每个标签只有一个评分控件，**没有**每标签独立评价框（契约 2.6：标签不保存评价文字）
- [ ] 标签被别处引用时删除标签定义返回 409，界面提示而不是静默失败

**依赖**：T6-01、T6-02。标签列表可先用 T6-09 之前的种子数据（后端已预置"未分类标签"分类）。

---

### T6-04　条目表单与类型中文映射

**目标**：新建和编辑条目都用英文枚举提交、中文显示。

**对应接口**：`POST /api/entries`、`PATCH /api/entries/{id}`

**验收标准**：

- [ ] 类型下拉显示中文（游戏、书籍、影视、音频、图片、模型、其他），提交英文值
- [ ] 映射集中在一处常量表，不要散在组件里
- [ ] `title` 去空格后 1–200 字符，超长或为空时前端先拦
- [ ] `description` 最多 20000 字符，超长时提示
- [ ] 编辑时 `PATCH` 只发送改过的字段（契约：至少提供一个字段）
- [ ] 卡片、详情页、筛选器三处的类型文案共用同一张映射表

---

### T6-05　资源面板接 availability 与重新检测

**目标**：详情页资源列表改用 `availability` 判断状态，并支持重新检测和解除关联。

**对应接口**：

| 操作 | 接口 |
|---|---|
| 读取资源 | `GET /api/entries/{id}/resources` → `{items, total}` |
| 重新检测 | `POST /api/resources/{rid}/recheck` → 带 `changed` 标记 |
| 解除关联 | `DELETE /api/entries/{id}/resources/{rid}` → 204 |
| 关联新文件 | `POST /api/entries/{id}/resources`，body `{path, file_name?}` |

**验收标准**：

- [ ] `availability === 'present'` 正常显示，`'missing'` 显示"文件已失效"标记
- [ ] 失效资源旁有"重新检测"按钮，检测后 `changed === true` 时提示"状态已更新"
- [ ] 资源列表只显示 `file_name`、`extension`、`size_bytes`、`sha256`，**不显示也不拼接任何路径**
- [ ] `size_bytes` 为 null 显示 `—`，`sha256` 为 null 显示"未计算"
- [ ] 解除关联前二次确认，文案写清"只解除关联，不删除磁盘文件"
- [ ] `RESOURCE_ALREADY_LINKED`（409）显示"该文件已关联到此条目"
- [ ] `RESOURCE_FILE_MISSING`、`RESOURCE_PATH_NOT_ABSOLUTE`、`RESOURCE_NOT_FILE` 分别有可读提示

---

### T6-06　条目整体评价输入框（⛔ 等成员二）

**目标**：详情页提供一个整体评价输入框，写进 `entries.review`。

**对应接口**：`PATCH /api/entries/{id}`，body `{"review": "..."}`

**为什么被阻塞**：数据库有 `review` 列、契约第 3.1 节也定义了，但 `backend/app/domain/entry.py` 的 `EntryCreate`/`EntryUpdate`/`EntryRead` 都没这个字段，FastAPI 会把 `review` 直接丢掉，响应也不返回。

**先做的事**：给成员二开 Issue，要求三个模型各补 `review`（最多 10000 字符）和 `lifecycle_state`。界面可以先按契约写，等模型补上立刻能通。

**验收标准**：

- [ ] 一个条目只有一个评价输入框（契约 §8 对成员六的第一条）
- [ ] 最多 10000 字符，超出时前端拦住并提示
- [ ] 能清空评价，提交 `{"review": null}`
- [ ] 保存后不刷新整页，本地状态同步更新
- [ ] `ENTRY_REVIEW_TOO_LONG` 有对应提示

---

### T6-07　列表页接真实接口（⛔ 等成员四）

**目标**：`LibraryView.vue` 从 `GET /api/entries` 取真实数据，替换掉 mock。

**对应接口**：`GET /api/entries`

**查询参数**（`backend/app/api/README.md` 已冻结）：

| 参数 | 值 |
|---|---|
| `q` | 标题与简介关键词 |
| `type` | 可重复，英文枚举 |
| `tag_id` | 可重复 |
| `tag_mode` | `and` / `or`，默认 `and` |
| `rating_min` / `rating_max` | **1–10** |
| `sort` | `updated_desc`、`title_asc`、`rating_desc` |
| `page` / `page_size` | 默认 1 与 50 |

**要跟成员四确认的两件事**：

1. 列表项是否携带标签摘要（否则卡片上显示标签就得每条一次 `GET /entries/{id}/tags`，20 条就是 20 个请求）
2. `lifecycle_state=temporary` 的条目是否已在 SQL 层排除（契约 §4 第 14 条要求不出现在列表里）

**验收标准**：

- [ ] 关键词、单标签、多标签（与/或）、评分区间、排序、分页全部走真实查询参数
- [ ] 搜索保持 250ms 防抖
- [ ] 四种状态齐全：加载中、空、错误、有数据
- [ ] 分页能翻页，`total` 显示正确
- [ ] `USE_MOCK` 改为 `false`，并删除 `api/mock.ts`

---

### T6-08　桥接层对齐真实返回值（⛔ 等成员八）

**目标**：让 `bridge/index.ts` 与 `adapters/bridge.py` 的实际行为一致。

**已存在的差异**：

| 前端以为 | 桥实际返回 |
|---|---|
| `open_resource(id): Promise<void>` | `{ok: true}` 或 `{ok: false, error: "RESOURCE_NOT_FOUND"}` |
| 只有 `pick_files` / `open_resource` / `pick_package` | 还有 `pick_folder`、`choose_save_path`、`confirm_open_executable`、`reveal_resource` |
| `pick_package(): Promise<string \| null>` | Python 侧标注 `list[str]` 但取消时返回 `None` |

**另外**：`launcher.py` 创建窗口时没有传 `js_api=NativeBridge(...)`，必须由成员八补上，否则桌面窗口里所有桥方法都是 `undefined`。

**验收标准**：

- [ ] 桥返回结果为 `{ok, error?}` 时，前端把 `error` 按错误码转成提示
- [ ] 可执行文件（`.exe`/`.bat`/`.cmd`/`.lnk`）返回 `EXECUTABLE_CONFIRM_REQUIRED` 时弹二次确认，确认后调 `confirm_open_executable`
- [ ] 无桥环境（5173 浏览器）继续走退化分支，不崩
- [ ] 桌面窗口里 `npm run build` 后实机验证一次打开文件

---

### T6-09　标签分类与标签管理界面

**目标**：侧栏或独立页面能管理分类和标签（Alpha 二）。

**对应接口**：`/api/tag-categories` 四个 + `/api/tags` 四个，全部已实现。

**验收标准**：

- [ ] 分类可建、可改名、可改色、可调 `sort_order`
- [ ] `system_key === 'uncategorized'` 的分类不显示删除按钮，改名也禁用（`SYSTEM_CATEGORY_PROTECTED`）
- [ ] 删除仍有标签的分类返回 409，提示"该分类下还有标签"
- [ ] 标签按分类分组显示，可在分类内新建、改名、移到别的分类
- [ ] 分类内重名返回 `TAG_NAME_DUPLICATED`，提示明确
- [ ] 删除被条目使用的标签返回 `TAG_IN_USE`，提示"该标签仍被 N 个条目使用"
- [ ] 颜色只在本机使用，界面上注明"分类颜色不会出现在分享包中"

---

### T6-10　分享包导出界面（⛔ 等成员五）

**对应接口**：`POST /api/share/export`，body `{entry_ids, include_covers}`

**契约对成员六的要求**（tag-rating-contract §8）：

- [ ] 导出前可重新勾选要包含的标签
- [ ] 评价模式三选一：只带原评价（`original`）、只带新评价（`new`）、两者都带（`both`）
- [ ] 部分资源导出时可拆成单文件条目或一组文件
- [ ] 分享完成后询问"删除临时条目"还是"保存为本地条目"
- [ ] 保存路径通过桥的 `choose_save_path()` 取

---

### T6-11　分享包导入预览页（⛔ 等成员五）

**对应接口**：`POST /api/share/preview` → `POST /api/share/import`

**验收标准**：

- [ ] 选包走桥 `pick_package()`，不用 `<input type="file">`
- [ ] 预览页列出：将导入的条目、冲突项、缺失资源
- [ ] 每个导入标签可选择放入哪个本地分类，未选择默认"未分类标签"
- [ ] 冲突项可逐条选择跳过或覆盖
- [ ] **用户确认前不写库**（契约：导入分两步）
- [ ] 导入失败时不留下半截数据

---

### T6-12　设置页：库文件位置与重建索引（⛔ 等接口）

**对应接口**：**尚未定义**

数据层已就绪（`db/app_setting_repository.py`、`db/backup.py`），但一个路由都没有。需要先和成员一、成员二定：

- `GET /api/settings` 返回库文件位置、版本
- `PATCH /api/settings` 修改库文件位置
- `POST /api/library/rebuild-index` 重建标题与标签索引

**验收标准**（接口定下来后）：

- [ ] 显示当前 `library.db` 绝对路径（这个路径可以显示，和资源路径不同）
- [ ] 修改库位置前二次确认，提示会重启生效
- [ ] 重建索引显示进度或至少显示进行中状态
- [ ] 提供备份导出入口（`db/backup.py` 已支持）

---

### T6-13　统一控件样式

**目标**：把散落的手写 CSS 收进一套控件里，为后面所有页面打底。

**验收标准**：

- [ ] 按钮、输入框、下拉、弹窗、标签、卡片各有统一 class，写在 `style.css`
- [ ] 颜色全部取自 `:root` 变量，组件里不出现硬编码色值
- [ ] 焦点态、禁用态、错误态三种状态都有样式
- [ ] 组件库选型定下来后，用一次 `chore: 引入 xx 组件库` 提交切换

---

## 3　需要协调的事项

| 找谁 | 要什么 | 影响的任务 |
|---|---|---|
| 成员四 | `GET /api/entries` 的实现时间；列表项是否带标签摘要 | T6-07 |
| 成员二 | `EntryCreate`/`EntryUpdate`/`EntryRead` 补 `review` 和 `lifecycle_state` | T6-06 |
| 成员八 | `launcher.py` 挂 `js_api=NativeBridge(window)`；修 `pick_package` 返回类型 | T6-08 |
| 成员一 | 设置相关接口（库位置、重建索引）定义 | T6-12 |
| 成员五 | 分享包三个接口 + `docs/share-package-spec.md`；条目类型用英文枚举 | T6-10、T6-11 |

---

## 4　建议排期

| 时间 | 做什么 | 里程碑 |
|---|---|---|
| 第 1–2 天 | T6-01 重写类型与客户端（不做它后面全是返工） | Alpha 一 |
| 第 3 天 | T6-02 评分控件 + T6-04 类型映射 | Alpha 一 |
| 第 4–5 天 | T6-03 条目标签评分面板 | Alpha 一 |
| 第 6 天 | T6-05 资源面板 | Alpha 一 |
| 第 7 天 | T6-07 列表页（前提：成员四接口已上） | Alpha 一 |
| 第 2 周 | T6-09 标签管理、T6-13 控件样式、T6-06/T6-08 解冻后插入 | Alpha 二 |
| 第 3–4 周 | T6-10、T6-11 分享包界面、T6-12 设置页 | Alpha 二 |

**关键路径**：T6-01 是所有任务的前置，一天都不能拖。T6-07 被成员四卡着，建议第一天就在群里催，并且先按契约把界面写好、用 mock 跑通。
