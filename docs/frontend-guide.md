# 前端入门指南（成员六）

- 用途：给初次接触前端开发的成员六提供 Vue 3 + TypeScript + Vite 的上手指导，以及本仓库前端工作的具体约定
- 负责人：成员六
- 最后更新：2026-11-01

本文不是通用教程，只讲本项目会用到的部分。前端技术在变，但这里的三条主线不变：组件怎么写、类型怎么标、数据怎么拿。

---

## 0　先看清起点

当前仓库 `frontend/` 的真实状态：

| 项目 | 状态 |
|---|---|
| 依赖 | 已安装，`node_modules` 与 `package-lock.json` 都在 |
| Node | 已安装 v22.23.4，位于 `C:\Program Files\nodejs\` |
| 页面 | 三栏骨架已完成：侧栏 + 列表 + 详情 |
| 组件 | 7 个基础组件 + 3 个视图，见第 12 节的文件地图 |
| 路由 | 未引入，用 `App.vue` 里的 `pane` 变量切换，Alpha 一够用 |
| 状态管理 | 未引入，跨栏状态由 `App.vue` 持有 |
| 组件库 | 未引入，按钮和输入框是手写 CSS |
| TypeScript 检查 | 已接入 `vue-tsc`，命令 `npm run type-check` |

也就是说：从零搭界面的阶段已经走完，接下来是往里填功能。

### Node.js：已装好，先确认能用

这台电脑已经装好了 **Node.js v22.23.4**，位置 `C:\Program Files\nodejs\`。打开一个**全新**的 PowerShell 窗口验证：

```powershell
node -v
npm -v
```

应该看到 `v22.x.x` 和 `10.x.x`。

如果提示"不是内部或外部命令"，是这个窗口的 PATH 还停留在安装前的状态：关掉重开，或者重启一次电脑。**注意**：一直在运行的终端、编辑器、IDE 会沿用启动时的旧 PATH，遇到"明明装了却找不到"就先换个全新终端验证。

> Vite 6 要求 Node 18 以上。全组统一用 22 LTS，不要各自升级大版本，免得构建行为不一致。

---

## 1　三条命令跑起来

项目有三个运行形态，别混。**开发时只用前两个终端。**

### 终端 A：后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

验证：浏览器打开 <http://127.0.0.1:8000/api/health>，看到 `{"status":"ok"}`。

> 如果 `Activate.ps1` 报"禁止运行脚本"，执行一次：
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 终端 B：前端（你每天待的地方）

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 <http://127.0.0.1:5173>，看到"仓鼠盒"页面、并且后端状态显示"后端已连接"，环境就通了。

`npm install` 只在两种情况下需要重跑：第一次拉代码后、`package.json` 有变动后。平时只跑 `npm run dev`。

### 第三个形态：桌面窗口（验证用，不是开发用）

```powershell
cd frontend
npm run build
cd ..
python desktop/launcher.py
```

它走的是 `frontend/dist` 打包产物，由后端在 8000 端口托管。**改代码不会自动生效**，必须重新 `npm run build`。所以日常开发千万别用它，只用 5173。

三者的关系：

```
终端 B  npm run dev  →  5173  ──proxy──▶  8000  终端 A（后端）
桌面窗口             →  8000  ──托管──▶  frontend/dist（打包后的 5173 产物）
```

### 关于接口不用配 CORS

`vite.config.ts` 里已经写好了代理：

```ts
proxy: { '/api': 'http://127.0.0.1:8000' }
```

意思是在 5173 页面里写 `fetch('/api/health')`，请求会被 Vite 转发到 8000。所以**代码里永远写相对路径 `/api/...`，不要写 `http://127.0.0.1:8000/api/...`**。写了绝对地址，打包成桌面版之后就会失效。

---

## 2　一次改动的完整回路

这是最初几天要练到肌肉记忆的节奏：

1. 在 `src/` 里改一行，Ctrl+S 保存
2. 浏览器**自动刷新**，直接看到效果（这就是 Vite 的意义）
3. 有报错时，`npm run dev` 的终端会打印，浏览器控制台也会打印
4. 满意了再提交

如果浏览器没自动刷新，看终端 A/B 有没有红色报错——通常是语法写错了，Vite 停止了热更新。

**先做静态页面，后接接口。** 这是新手最重要的一条工作方法：对着 `backend/app/api/README.md` 的契约，用假数据把界面画出来，等后端接口好了再换成真数据。不要坐着等接口。

---

## 3　Vue 3 最小知识集

够用就停，别抱着官方文档从头读。

### 3.1　单文件组件（SFC）

一个 `.vue` 文件 = 一个组件，三段式：

```vue
<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)

function increase() {
  count.value += 1
}
</script>

<template>
  <button class="counter" @click="increase">点了 {{ count }} 次</button>
</template>

<style scoped>
.counter {
  padding: 8px 16px;
}
</style>
```

三段各自的职责：

| 段 | 写什么 | 说明 |
|---|---|---|
| `<script setup lang="ts">` | 逻辑 | `lang="ts"` 不能省，否则没有类型检查 |
| `<template>` | 结构 | 只能用 Vue 模板语法，不是 HTML 直出 |
| `<style scoped>` | 样式 | `scoped` 让样式只作用于本组件，务必都加 |

### 3.2　⭐ 第一个必踩的坑：`.value`

```ts
const count = ref(0)

count.value += 1      // 在 <script> 里，必须写 .value
```

```vue
<span>{{ count }}</span>   <!-- 在 <template> 里，不能写 .value -->
<span>{{ count.value }}</span>  <!-- 错，会显示 undefined -->
```

**在 JS 里要用 `.value`，在模板里不用。** 忘了 `.value` 不会报错，只是数据不动，这是新手最常见的调试噩梦。

### 3.3　响应式：只用 `ref` 就够了

```ts
import { ref, computed, watch } from 'vue'

const entries = ref<Entry[]>([])        // 数组
const keyword = ref('')                 // 字符串
const loading = ref(false)              // 布尔

// 派生数据用 computed，不要手写同步逻辑
const visibleEntries = computed(() =>
  entries.value.filter((e) => e.title.includes(keyword.value)),
)
```

`ref` 能装任何东西，团队统一用它。`reactive` 只适合对象且容易在解构时丢响应性，新手别碰。

`computed` 的好处是：依赖变了它自动重算，你不用管什么时候刷新。**凡是"由现有数据算出来的值"，一律用 `computed`。**

### 3.4　模板语法速查

| 需求 | 写法 |
|---|---|
| 插入文本 | `{{ entry.title }}` |
| 绑定属性 | `:src="entry.cover"` |
| 绑定事件 | `@click="openDetail(entry.id)"` |
| 双向绑定输入框 | `v-model="keyword"` |
| 条件显示 | `v-if="loading"` / `v-else-if` / `v-else` |
| 循环 | `v-for="entry in entries" :key="entry.id"` |
| 动态 class | `:class="{ active: selectedId === entry.id }"` |
| 动态内联样式 | `:style="{ backgroundColor: tag.color }"` |

`v-if` 和 `v-show` 的区别：`v-if` 是真把节点删掉（切换有开销、初始不渲染），`v-show` 只是 `display:none`（切换便宜）。列表用 `v-if` 判空态，频繁切换的用 `v-show`。

**`v-for` 必须加 `:key`，且用数据自己的 id，不要用 `index`。** 用 index 在列表增删时会出现内容错位。

### 3.5　组件之间传值

父传子用 `props`，子传父用 `emit`：

```vue
<!-- components/EntryCard.vue -->
<script setup lang="ts">
import type { Entry } from '../types/api'

const props = defineProps<{
  entry: Entry
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', id: number): void
}>()
</script>

<template>
  <article class="card" :class="{ active: selected }" @click="emit('select', props.entry.id)">
    <h3>{{ entry.title }}</h3>
  </article>
</template>
```

```vue
<!-- 父组件使用 -->
<EntryCard
  v-for="entry in entries"
  :key="entry.id"
  :entry="entry"
  :selected="entry.id === selectedId"
  @select="selectedId = $event"
/>
```

`defineProps<{...}>()` 这种写法叫泛型语法，**靠 TypeScript 类型自动推出 props**，不需要再手写一长串 `props: {}`。这是 Vue 3 + TS 最舒服的地方。

### 3.6　生命周期

写界面基本只用两个：

```ts
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  loadEntries()        // 页面第一次显示时拉数据
})

onUnmounted(() => {
  clearInterval(timer) // 离开时清理定时器，否则内存泄漏
})
```

---

## 4　TypeScript 只需要会这些

`tsconfig.json` 里开了 `"strict": true`，这意味着类型检查很严格。别关它，也别用 `any` 糊过去——类型错误往往正是运行时的 bug。

### 4.1　用 interface 描述接口返回

在 `src/types/api.ts` 里集中定义，**全项目唯一来源**：

```ts
export type EntryType =
  | 'game'
  | 'book'
  | 'video'
  | 'audio'
  | 'image'
  | 'model'
  | 'other'

export interface Entry {
  id: number
  share_id: string
  title: string
  type: EntryType
  description: string | null
  review: string | null
  lifecycle_state: 'library' | 'temporary'
  cover_path: string | null
  created_at: string // ISO 8601 字符串，UTC
  updated_at: string
}

export interface TagCategory {
  id: number
  name: string
  color: string | null
  sort_order: number
  system_key: string | null
  created_at: string
  updated_at: string
}

export interface Tag {
  id: number
  category_id: number
  name: string
  created_at: string
  updated_at: string
}

export interface EntryTag {
  entry_id: number
  tag_id: number
  tag_name: string
  category_id: number
  rating: number | null
  created_at: string
  updated_at: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}
```

这些字段不是自己编的，全部来自 `backend/app/api/README.md`。**接口字段以那份文档为准，字段变了先改文档再改代码。**

### 4.2　严格模式下的两个高频报错

**① `Object is possibly 'null'`**

```ts
// entry.cover 的类型是 string | null
<img :src="entry.cover" />              // 报错

<img :src="entry.cover ?? ''" />        // 对：给个兜底
<img v-if="entry.cover" :src="entry.cover" />  // 对：先判断
```

**② `Parameter implicitly has an 'any' type`**

```ts
entries.map((e) => e.title)              // 能自动推断，没问题

function onSelect(id) { }                 // 报错：id 没类型
function onSelect(id: number) { }         // 对
```

记住两个运算符：`?.`（可选链，中间是 null 就停下返回 undefined）和 `??`（空值合并，左边是 null/undefined 就用右边）。它们能解决 90% 的严格模式报错。

### 4.3　不要把类型当装饰

```ts
const data = await response.json() as any       // ✗ 等于放弃类型
const data = await response.json() as Entry     // ✗ 编译过了，运行时可能是别的东西
const data: Entry = await response.json()       // ⚠ 略好，但也没校验
```

正确做法是让 `request<T>()` 这种泛型函数统一注入类型（见下一节），组件里拿到的就是有类型的值。

### 4.4　类型检查命令（已经配好）

`npm run build` **不会**检查类型：Vite 只做编译，把类型整个擦掉，类型错误会被悄悄忽略。所以 `package.json` 里已经加好了脚本：

```json
"type-check": "vue-tsc --noEmit"
```

`vue-tsc` 也写进了 `devDependencies`。你只需要跑一次 `npm install` 让它装上，之后每次提 PR 前执行：

```powershell
npm run type-check
```

没有任何输出就是通过。这是保护自己不把类型错误合进去的最简单办法。

---

## 5　和后端对话：`api/client.ts` 的写法

**所有请求集中在 `src/api/client.ts`，组件里不许直接写 `fetch`。** 这是 `frontend/README.md` 里的硬约定，原因是：错误处理、路径、类型三处只需维护一份。

统一封装长这样：

```ts
const BASE = '/api'

export class ApiRequestError extends Error {
  status: number
  code: string
  details?: Record<string, unknown>

  constructor(status: number, body: ApiError) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.details = body.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    let body: ApiError = { code: 'UNKNOWN', message: `HTTP ${response.status}` }
    try {
      body = (await response.json()) as ApiError
    } catch {
      // 后端返回的不是 JSON，保留兜底信息
    }
    throw new ApiRequestError(response.status, body)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
```

然后每个接口一行：

```ts
export interface ListEntriesParams {
  q?: string
  tag_id?: number[]
  tag_mode?: 'and' | 'or'
  rating_min?: number
  rating_max?: number
  sort?: 'updated_desc' | 'title_asc' | 'rating_desc'
  page?: number
  page_size?: number
}

export function listEntries(params: ListEntriesParams = {}) {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.tag_id) params.tag_id.forEach((id) => query.append('tag_id', String(id)))
  if (params.tag_mode) query.set('tag_mode', params.tag_mode)
  if (params.rating_min != null) query.set('rating_min', String(params.rating_min))
  if (params.rating_max != null) query.set('rating_max', String(params.rating_max))
  if (params.sort) query.set('sort', params.sort)
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 50))
  return request<Paginated<Entry>>(`/entries?${query.toString()}`)
}

export function createEntry(payload: { title: string; type: string; summary?: string }) {
  return request<Entry>('/entries', { method: 'POST', body: JSON.stringify(payload) })
}

export function deleteEntry(entryId: number) {
  return request<void>(`/entries/${entryId}`, { method: 'DELETE' })
}
```

组件里用起来就很干净：

```ts
import { listEntries, ApiRequestError } from '../api/client'

const entries = ref<Entry[]>([])
const loading = ref(false)
const errorMessage = ref('')

async function loadEntries() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await listEntries({ page: 1, page_size: 50 })
    entries.value = data.items
  } catch (err) {
    errorMessage.value =
      err instanceof ApiRequestError ? `${err.code}：${err.message}` : '网络异常，请重试'
  } finally {
    loading.value = false
  }
}
```

注意 `finally` 里必须复位 `loading`，否则一次失败后骨架屏永远转下去。

### 错误码对应什么界面

后端约定的状态码（见 `backend/app/api/README.md`）：

| 状态 | 含义 | 界面该做什么 |
|---|---|---|
| 400 | 请求格式或状态不允许 | 顶部错误条，提示具体操作不对 |
| 404 | 条目/资源/标签不存在 | 提示"已被删除"，刷新列表 |
| 409 | 唯一约束冲突（标签重名、标签仍被引用） | **必须弹出提示，不许静默失败** |
| 422 | 字段校验失败（颜色格式、评分越界） | 定位到出错字段旁提示 |

409 是明确写进前端交互约定的：标签重名要展示提示。别用 `console.log` 打发。

### 四种状态一个都不能少

`frontend/README.md` 要求每个列表页和详情页覆盖四态：

```vue
<template>
  <div v-if="loading" class="skeleton">加载中…</div>

  <div v-else-if="errorMessage" class="error-banner">
    {{ errorMessage }}
    <button @click="loadEntries">重试</button>
  </div>

  <div v-else-if="entries.length === 0" class="empty-state">
    还没有条目。点击右上角"新建条目"开始收集。
  </div>

  <div v-else class="entry-grid">
    <EntryCard v-for="entry in entries" :key="entry.id" :entry="entry" />
  </div>
</template>
```

第四态"部分失效"（资源文件被移动/删除）在 Alpha 二阶段接失效检测时处理：卡片上打标记，提供"重新定位"入口。

---

## 6　JS 桥：现在还没有，但迟早要接

### 6.1　为什么需要它

浏览器出于安全，拿不到文件的真实路径。而本项目的核心就是"保存本地文件的绝对路径"。所以选文件、打开文件、保存对话框这些能力，必须由 Python 那一侧提供，前端通过桥调用。

架构上分得很清（见 `docs/architecture.md`）：

| 通道 | 传什么 | 例子 |
|---|---|---|
| HTTP/JSON | 业务数据 | 条目、标签、评分、检索 |
| JS 桥 | 原生能力 | 选文件、打开文件、打开目录、保存对话框 |

### 6.2　它现在还没实现

`desktop/launcher.py` 目前创建窗口时**没有挂载 `js_api`**，桥还不存在。文档里约定的三个方法（`pick_files`、`open_resource`、`pick_package`）需要和成员七（系统能力适配）、成员八（`desktop/` 与发布）一起定下来。

定型后前端侧大致长这样：

```ts
// src/bridge/index.ts
export interface HamsterBoxBridge {
  pick_files: () => Promise<string[]>
  open_resource: (resourceId: number) => Promise<void>
  pick_package: () => Promise<string | null>
}

declare global {
  interface Window {
    pywebview?: { api: HamsterBoxBridge }
  }
}

export function hasBridge(): boolean {
  return typeof window.pywebview !== 'undefined'
}
```

### 6.3　浏览器的现实问题

**在 5173 的浏览器里，`window.pywebview` 永远是 `undefined`。** 所以桥调用必须写好退化分支，否则界面在开发时会直接崩：

```ts
export async function pickFiles(): Promise<string[]> {
  if (!hasBridge()) {
    console.warn('[dev] 桥不可用，返回模拟路径')
    return ['D:\\Media\\example.mp4']
  }
  return window.pywebview!.api.pick_files()
}
```

**要记住的代价**：桥相关功能只能在桌面窗口里真实验证。所以"双击打开文件"这类功能，开发时用模拟数据调界面，收尾时必须 `npm run build` 后用 `python desktop/launcher.py` 真机点一遍。这是唯一会导致"我这儿好的呀"的环节，务必提前和成员二确认联调时间。

pywebview 里桥就绪有个事件，不要一上来就调用：

```ts
window.addEventListener('pywebviewready', () => {
  bridgeReady.value = true
})
```

### 6.4　安全红线（违反会被评审打回）

- 桥只接收 `resource_id` 这类**业务标识**，由后端自己查真实路径
- **绝不**把前端拼出来的绝对路径传给桥去执行系统命令
- 打开可执行文件时必须有明确的用户操作和异常提示
- 前端不拼接本地绝对路径，不在 URL 里传路径

---

## 7　样式与组件库

当前是**手写 CSS**，只有 `src/style.css` 里几十行。这撑不起三栏界面，需要做决定：

**建议**：先加一个组件库，别手搓按钮和弹窗。理由是计划文档 `10.2` 把"前端成为瓶颈"列为风险，应对措施写的是"组件库先行"。

可选：Element Plus（中文文档最全，适合新手）、Naive UI（体积小、TS 友好）、Ant Design Vue。**选定后组内不再更换**，放进 `package.json` 时用一次 `chore: 引入 xxx 组件库` 的提交，并通知全员，避免各行其是。

样式约定：

- 组件内样式一律 `<style scoped>`
- 颜色、间距定义在 `src/style.css` 的 `:root` 里做 CSS 变量，别在组件里写死色值
- 类名用连字符：`.entry-card`、`.empty-state`
- 中文界面文案，代码里的变量和函数用英文（这是 `9.6` 的硬规定）

---

## 8　调试的三个工具

**① 浏览器控制台（最常用）**

在 5173 页面按 `F12`：
- `Console`：看报错和 `console.log`
- `Network`：看每个请求的 URL、状态码、返回体。**接口不对时第一件事就是看这里**，能立刻分清是前端没发对，还是后端没返回对
- `Elements`：改样式试效果，满意了再抄回代码

**② Vue Devtools**

Chrome / Edge 装扩展 "Vue.js devtools"，能在面板里直接看每个组件的 props、data，不用靠 `console.log` 猜。

**③ 桌面窗口的调试**

`python desktop/launcher.py` 的窗口默认不能右键检查。临时把 `webview.start()` 改成 `webview.start(debug=True)`，就能开着 DevTools 排查打包后的问题。注意这只是临时改动，**不要提交**。

**类型检查**：`npm run type-check`（需要先按 4.4 装 `vue-tsc`）。提交 PR 前跑一次。

---

## 9　GitHub Desktop 操作步骤

本机装了 GitHub Desktop 3.6.10（自带 Git 2.56），`git` 命令不在 PATH 里 —— **对新手，直接用图形界面，别折腾命令行。**

仓库已克隆好，远端是 `github.com/fenghouyanchengwen/hamsterbox`，当前在 `main` 分支。日常五步：

**① 开工前先同步**

点顶部 `Fetch origin` → 有更新时点 `Pull origin`。**每次开工第一件事，否则后面必然冲突。**

**② 建分支**

点 `Current Branch` → `New Branch`，输入 `feature/ui-main-layout`，基于 `main` 创建。

命名规则（`docs/branching.md`）：`feature/模块-简述`、`fix/模块-简述`、`docs/文档名`。**全部小写英文，不用中文。**

**③ 改代码 → 提交**

左侧会列出改动文件。在左下角填 Summary：

```
feat(ui): 搭建三栏主框架 (#21)
```

- 类型前缀只能是 `feat / fix / docs / test / refactor / chore`
- 括号里是模块，`#21` 是 Issue 编号
- 一次提交只做一件事
- 提交前确认 `node_modules`、`dist` 没有出现在文件列表里（`.gitignore` 已忽略，正常情况下不会出现）

点 `Commit to feature/ui-main-layout`，然后 `Push origin`。

**④ 开 Pull Request**

推送后 GitHub Desktop 会显示 `Create Pull Request`，点它，浏览器会打开 GitHub 的 PR 页面。标题照提交风格写，描述照 `.github/pull_request_template.md` 填：

- 关联 Issue：`Closes #21`
- 改动内容
- 验证方式（比如"5173 下三栏正常显示，切到空库显示引导文案"）
- **界面截图（必填）**

**⑤ 请成员五评审 → 合并**

按 `docs/branching.md` 的评审配对表，**成员六的 PR 由成员五评审**。在右侧 `Reviewers` 里选成员五，等他 approve。

合并时选 **`Squash and merge`**（不要用 "Create a merge commit"），合并后点 `Delete branch`。

**红线**：永远不直接往 `main` 推。`main` 上只出现通过 PR 合进来的提交。

---

## 10　新手最容易踩的十个坑

| # | 坑 | 后果 / 怎么避 |
|---|---|---|
| 1 | `ref` 忘了写 `.value` | 数据不更新，还不报错。写脚本时看到值不对，先查 `.value` |
| 2 | `v-for` 不加 `:key` 或用 index | 增删后内容错位。用数据自己的 id |
| 3 | 组件里直接写 `fetch` | 违反约定，评审打回。一律走 `api/client.ts` |
| 4 | 只写"有数据"一种状态 | 四态缺失，验收必查。空库、报错、加载中都要有画面 |
| 5 | 移出库按钮写"删除" | 必须明确写"不会删除磁盘文件"，否则用户误以为文件没了 |
| 6 | 给桥传前端拼的路径 | 安全红线。只传 `resource_id` |
| 7 | 在 `main` 上直接改 | 无法并发协作，评审打回。开工先建分支 |
| 8 | 分支/文件名用中文 | 远端已有一个乱码分支 `鎵╁睍涓庨€傞厤` 就是教训。全用英文小写 |
| 9 | 用 `as any` 消错误 | 类型形同虚设，bug 留到运行期。老老实实补类型 |
| 10 | 只跑 `npm run dev` 就认为没问题 | Vite 不检查类型、不验证桥。提 PR 前跑 `type-check`，收尾用桌面窗口真机验证 |

---

## 11　第一周照这个顺序做

三栏骨架已经写好了（见第 12 节），所以第一周的重点是"读懂 → 改一处 → 走完 Git 流程"，而不是从空白文件开始。

| 顺序 | 做什么 | 完成标志 |
|---|---|---|
| 1 | `npm install`（因为新增了 vue-tsc）+ `npm run dev` | 5173 显示三栏界面和 5 条演示数据 |
| 2 | 按第 12.1 节的文件地图通读一遍，重点读 `api/client.ts` 和 `views/LibraryView.vue` | 能说清数据从哪个函数来、到哪个 ref 去 |
| 3 | 改一处小东西：把 `EntryCard.vue` 里 `.cover` 的 `width: 56px` 改成 `72px` | 保存后浏览器立刻变化 |
| 4 | 加一个小组件并接进界面，比如在侧栏底部显示条目总数 | 新组件被引用并正确显示 |
| 5 | 把 `config.ts` 的 `USE_MOCK` 改成 `false`，看真实报错长什么样，再改回来 | 看到 ErrorBanner 和"后端未启动" |
| 6 | 建分支、提交、推送、开 PR，请成员五评审 | 第一个 PR 被 squash 合进 `main` |
| 7 | 找成员二确认第 12.4 节列的两处契约缺口 | Issue 里留下结论 |

第 1 周内把"侧栏 + 列表 + 详情"这条主线稳定下来，是整个 Alpha 第一阶段不被前端卡住的关键节点。

---

## 12　骨架代码说明与使用方法

Alpha 第一阶段的三栏骨架已经落在 `frontend/src/` 里，可以直接运行、直接改。

### 12.1　文件地图

| 文件 | 作用 | 要不要动 |
|---|---|---|
| `src/types/api.ts` | 全项目类型定义，逐字段对齐 `backend/app/api/README.md` | 接口变了就改这里 |
| `src/config.ts` | `USE_MOCK` 开关与模拟延迟 | 后端就绪后改一次 |
| `src/api/mock.ts` | 演示数据：5 条目 / 5 标签 / 评分 / 资源 | 发布前删掉 |
| `src/api/client.ts` | 唯一的请求出口，`request<T>()` + `ApiRequestError` + 所有接口函数 | 加接口时在这里加一行 |
| `src/bridge/index.ts` | PyWebView 桥封装，含浏览器环境的退化分支 | 等 Python 侧补齐 |
| `src/utils/format.ts` | 时间按本地时区格式化、字节数格式化 | 一般不动 |
| `src/utils/error.ts` | 把异常转成能显示的一句话 | 一般不动 |
| `src/App.vue` | 三栏外壳，持有跨栏状态：选中条目、标签筛选、后端状态 | 加导航项时改 |
| `src/views/LibraryView.vue` | 列表栏：搜索防抖、排序、新建表单、四种状态 | 主要改这里 |
| `src/views/EntryDetailView.vue` | 详情栏：标签评分、简介、关联文件、移出库 | 主要改这里 |
| `src/views/SettingsView.vue` | 设置占位，Alpha 二阶段填 | Alpha 二阶段 |
| `src/components/EntryCard.vue` | 条目卡片 | 调整卡片信息时 |
| `src/components/TagChip.vue` | 标签胶囊，带颜色圆点 | 一般不动 |
| `src/components/RatingStars.vue` | 评分控件，支持空评分和 1 至 10 分 | 评分口径变化时 |
| `src/components/FilterBar.vue` | 搜索框 + 排序 + 已选标签 | 加筛选维度时 |
| `src/components/EmptyState.vue` | 空态，带引导文案和操作按钮 | 一般不动 |
| `src/components/ErrorBanner.vue` | 错误条，带重试按钮 | 一般不动 |
| `src/components/LoadingSkeleton.vue` | 骨架屏 | 一般不动 |
| `src/style.css` | CSS 变量 + 通用控件（`.btn`、`.field`） | 换主题时 |

### 12.2　怎么跑起来

```powershell
cd frontend
npm install        # 必须重跑一次：package.json 新增了 vue-tsc
npm run dev
```

打开 <http://127.0.0.1:5173>。

此时后端可以不起：界面会显示"后端未启动"，但条目列表照常显示演示数据，并带一个"演示数据"角标。这是刻意设计的——前端不靠后端也能调界面。

要完整验证前后端联通，另开一个终端起后端（第 1 节的终端 A）。

### 12.3　现在能看到什么

- **左栏**：品牌、导航（全部条目 / 设置）、标签列表（点一下筛选，再点取消）、后端连接状态
- **中栏**：搜索框（250ms 防抖）、排序下拉、新建条目表单、条目卡片、四种状态
- **右栏**：标签评分（能点星、点同一个星取消、未开启评分的标签禁用）、简介、关联文件列表、移出库二次确认

演示数据是照着 Alpha 一阶段的验收标准造的：5 个条目、其中 2 个各带 3 个标签、有开启评分和未开启评分的标签、还留了一个 `exists: false` 的失效文件用来验证"部分失效"状态。打开「银翼杀手 2049」那条就能看到"文件已失效"标记。

### 12.4　两处必须和后端对齐的契约缺口

骨架里有两处是**照着推断写的**，已经用注释标了 ⚠，接真实接口前必须定下来：

1. **列表接口是否返回条目的标签**。`types/api.ts` 里 `Entry.tag_ids?: number[]` 是我加的，`backend/app/api/README.md` 没定义。卡片上的标签全靠它，如果成员二决定不返回，卡片就得改成不显示标签。
2. **读取资源列表的端点没有定义**。文档只写了资源的新增和解除关联，没写 `GET /api/entries/{id}/resources`。`client.ts` 里先按这个路径写了。

建议开两个 Issue 挂在成员二名下，结论写进 `backend/app/api/README.md`，再回来改类型。

### 12.5　怎么关掉演示数据

改 `src/config.ts`：

```ts
export const USE_MOCK = false
```

保存后 Vite 自动刷新，界面开始走真实 HTTP。如果后端接口还没好，列表会显示错误条，错误码一并显示——这正是"错误态"该有的样子。

### 12.6　提 PR 前的三件事

```powershell
npm run type-check     # 无输出即通过
npm run build          # 确认能打包
```

第三件事：在浏览器里把四种状态都点一遍（有数据 / 搜不到 / 改 USE_MOCK 看错误 / 选中带失效文件的条目），然后截图放进 PR 描述。

### 12.7　还没做的，留给后面阶段

| 没做 | 原因 |
|---|---|
| 标签的增删改界面 | 等成员三的接口，Alpha 一阶段可以先在数据库或接口文档里造标签 |
| 路由（vue-router） | 现在用 `App.vue` 的 `pane` 变量切换，两个页面足够；页面多了再引 |
| 组件库 | 定了以后用一次 `chore: 引入 xx 组件库` 提交加入，然后逐步替换手写控件 |
| 编辑条目 | 接口 `PATCH /api/entries/{id}` 已有，界面待补 |
| 缩略图、批量操作、回收站、导入预览 | 按计划属于 Beta 阶段 |

> 提醒：`frontend/dist/` 里现在是 10 月 31 日打包的旧产物。用 `python desktop/launcher.py` 验证桌面前，必须重新 `npm run build`，否则看到的是老界面。

---

## 附：常用命令速查

```powershell
# 前端
cd frontend
npm install            # 首次或 package.json 变动后
npm run dev            # 日常开发，http://127.0.0.1:5173
npm run build          # 生成 frontend/dist，仅桌面验证用
npm run type-check     # 类型检查，无输出即通过

# 后端
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# 桌面窗口（先 npm run build）
python desktop/launcher.py
```

## 相关文档

- `frontend/README.md`　本模块职责、目录建议、页面与接口对应、状态与交互约定
- `backend/app/api/README.md`　接口契约、参数、错误码（前端的所有类型以此为准）
- `docs/architecture.md`　HTTP 数据面与 JS 能力面的边界、安全规则
- `docs/branching.md`　分支命名、提交格式、PR 与评审配对
