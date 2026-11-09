# Adapter 接口 alpha二阶段
## 一、 阶段目标回顾
在 Alpha 二阶段，本模块的核心目标是将一阶段的 Mock 占位替换为真实的多媒体解析逻辑，彻底落实桥接层的安全规则，并完成与数据服务（成员二）的链路联调，确保文件类型识别能正确落库。

## 二、 核心交付物与完成情况
### 1. 内置适配器真实化 (元数据解析)
#### 图片适配器 (ImageAdapter)： 
引入 Pillow 库，真实读取图片的 width、height 和 format。遇到损坏图片时安全兜底，仅返回 file_size，绝不抛出异常导致主链路崩溃。

#### 视频适配器 (VideoAdapter)：
引入 pymediainfo，提取视频的 duration、resolution 和 codec。严格遵循文档要求，未实现缩略图生成。

#### 电子书适配器 (EbookAdapter)：

引入 ebooklib 解析 EPUB（提取书名、作者、尝试提取页数）。

引入 pypdf 解析 PDF（提取书名、作者、页数）。

引入 ebookatty 解析 MOBI（提取 EXTH 头部元数据）。

#### 兜底：
引入 parse_status 字段，明确区分“文件损坏（failed）”与“正常但无元数据（metadata_extracted: False）”。

### 2. 注册表与枚举对齐 (TypeRegistry & enums.py)
#### 全局兜底机制：
优化了 TypeRegistry，新增 _default_adapter。对于所有未被特定适配器接管的扩展名（含无后缀文件），自动交由全局 FallbackAdapter 处理并返回 EntryType.OTHER。

### 3. 系统能力桥接层重构 (bridge.py)
#### 安全规则落实：

#### 可执行文件拦截：
新增 user_confirmed: bool 参数。当检测到 .exe, .bat, .cmd, .lnk 等可执行文件且未确认时，拦截打开操作，返回 EXECUTABLE_CONFIRM_REQUIRED。

#### 禁止路径注入：
彻底废弃本地 _resolve_path，全面接入成员二的 ResourceService。所有打开、定位操作，均由后端根据 resource_id 去数据库查真实路径。

#### 命令注入防护：
在 reveal_resource 中调用 explorer 时，使用 subprocess.run([...]) 列表传参，彻底杜绝 shell=True 带来的命令注入风险。



## 三、 单元测试与质量保障
#### 新增了 tests/adapters/test_adapters_alpha2.py 和 tests/adapters/test_bridge.py，测试用例覆盖以下场景：

动态生成真实图片，验证宽高解析是否正确。

伪造损坏的 EPUB/图片文件，验证 parse_status 和安全兜底。

Mock ResourceService，验证桥接层对 .exe 文件的安全拦截与二次放行逻辑。

验证未知后缀文件能否被全局兜底。

测试结果：所有新增用例均一次性通过（PASSED）。

## 四、 下一步交接与协作备忘
### @成员二：

已在协作 Issue 中约定，请在 ResourceService.attach_resource 中注入 TypeRegistry，并调用 detect(path) 将识别结果更新到 Entry.type 字段。

### @成员六：
请根据接口文档，在前端统一处理 EXECUTABLE_CONFIRM_REQUIRED 的弹窗逻辑；如果 cover 或解析字段为 null，请按严格模式做好空值兜底。

### @成员八：
#### 请添加以下库，用于实现适配器功能
```python
Pillow>=10.0,<11          # 用于读取图片宽高
pymediainfo>=6.0,<7       # 用于读取视频时长和分辨率
ebooklib>=0.18,<1         # 用于读取 EPUB 电子书书名/作者
pypdf>=4.0,<5             # 用于读取 PDF 电子书元数据
ebookatty>=0.1,<1         # 用于读取 MOBI 电子书元数据
```
