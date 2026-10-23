---
name: dtyl
description: 动态原理拆解（动态原理可视化）。把一条技术原理 / 机制拆成「结构拆解 → 可播放动态过程 → 严谨版 + 白话版 → 含改变条件的自测题 → 适用场景 / 限制 / 实践结论」，产出自包含动画 HTML。触发词：动态原理拆解、动态原理可视化、原理可视化、讲清楚原理、原理动画、机制拆解、dtyl、dynamic principle visualizer。
---

# dtyl — 动态原理拆解

> 版本 1.0.0。把一个抽象原理讲成「看得见的动态过程」，而不是一段解释文字。
> 仓库地址：<https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/dtyl>

## 这个 skill 解决什么

用户说「把 X 的原理讲清楚 / 动态地演示一下 X / 做个原理可视化」时，产出一份**自包含、可播放**的 HTML：读者能点「播放」看机制一步步演化，而不是读一堆静态段落。

统一输出 8 块，缺一不算完成：

| # | 区块 | 要求 |
|---|---|---|
| 1 | 页首声明 | 「原理演示，非压测 / 非生产基准」——本技能只解释机制，不产出压测结论 |
| 2 | 结构拆解 | 参与角色（组件）及其职责，每个组件一个状态徽章 |
| 3 | 动态过程 | 分步可播放动画：上一步 / 播放 / 下一步 / 重置 + 进度条 |
| 4 | 严谨版 | 伪代码 / 公式 / 精确规则（可直接改成生产代码） |
| 5 | 白话版 | 一个生活化类比，覆盖同一机制，不引入错误简化 |
| 6 | 自测题 | 至少一题**改变条件**（删掉某个环节 / 换一种策略），答「会怎样」 |
| 7 | 适用场景 | 什么时候该用它 |
| 8 | 限制 + 实践结论 | 边界、失败条件、与相邻概念的区分；一句话落地结论 |

## 快速开始

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/dtyl ~/.workbuddy/skills/dtyl
```

```bash
# 1) 写一份规格 JSON（见 references/spec-format.md）
# 2) 生成自包含 HTML
python ~/.workbuddy/skills/dtyl/scripts/gen_dpv.py my.spec.json out.html
# 3) 双击 out.html，或用 playwright 截图核验
```

纯标准库，无需 `pip install`。生成器只用 Python 3.8+。

## 工作流

1. **定题与边界**：明确要拆的机制（例：Redis 缓存击穿 + 互斥锁），一句话写清「它解决什么 / 不解决什么」。相邻但不同的概念必须点明（击穿 / 雪崩 / 穿透）。
2. **列组件**：客户端、缓存、锁、数据库……每个组件给 `id / label / role`。`id` 全篇唯一，后面前端按它定位状态徽章。
3. **编步骤**：每步一条 `cap`（字幕）+ 变化的组件 `state`（`text` + `cls`）+ `actors`（调用链）。**未提及的组件自动继承上一步状态**，所以只写变化项。
4. **写严谨版**：伪代码要能直接翻译成生产代码；把「锁超时 / 双重检查 / TTL 错开」这类关键防御写进去。
5. **写白话版**：一个类比覆盖全流程；类比不能掩盖关键差异（如「锁必须带超时」要讲）。
6. **出自测题**：至少一题改变条件，考「删掉某环节会怎样」，答案要点明退化路径。
7. **生成 + 校验**：跑 `gen_dpv.py`；用 headless 浏览器打开，确认无 JS 报错、关键步骤状态正确（如击穿态组件变红、抑制态变绿）。
8. **交付**：给 HTML 路径 + 关键步骤截图；明确声明「原理演示，非压测」。

## 规格文件

`gen_dpv.py <spec.json> [out.html]`。字段：

| 字段 | 必填 | 含义 |
|---|---|---|
| `title` | 是 | 标题 |
| `subtitle` | 否 | 副标题 |
| `disclaimer` | 否 | 页首声明，默认「原理演示，非压测 / 非生产基准」 |
| `components[]` | 是 | `{id, label, role}`；`id` 唯一，前端按它渲染状态徽章 |
| `steps[]` | 是 | `{cap, actors[], state{}}`；`state` 的 key 是组件 `id`，值为 `{text, cls}` |
| `rigorous` | 否 | 严谨版（支持 `\n` 换行） |
| `plain` | 否 | 白话版 |
| `quiz[]` | 否 | `{q, change, a}`；`change` 写「改变条件」 |
| `scenarios[]` | 否 | 适用场景列表 |
| `limits[]` | 否 | 限制列表 |
| `conclusion` | 否 | 实践结论 |

状态徽章 `cls` 取值：`none`（灰）/ `hit`（绿）/ `miss`（红）/ `locked`（琥珀）/ `db`（深红）/ `warn`（琥珀）。

完整字段与示例见 [`references/spec-format.md`](references/spec-format.md)。

## 目录结构

```
dtyl/
├── SKILL.md
├── README.md                    # 用户向：安装 / 快速开始 / 验证 / 边界
├── scripts/
│   └── gen_dpv.py               # 规格 JSON → 自包含动画 HTML（纯标准库）
├── references/
│   └── spec-format.md           # 规格 JSON 字段契约
└── examples/
    ├── README.md                # 例子索引与复现方法
    ├── redis-cache-breakdown.spec.json   # Redis 缓存击穿案例规格
    └── redis-cache-breakdown.html        # 由上面规格生成的成品（可直接打开）
```

## 硬约束（不可省略）

1. **原理演示 ≠ 压测**：页首必须有声明，正文不得给「QPS / 延迟 / 吞吐」等实测数字冒充结论。要谈容量，单独去做压测。
2. **相邻概念必须区分**：缓存击穿（单 key 过期）/ 雪崩（大量 key 同时过期）/ 穿透（查不存在的 key）机制不同，别混讲。
3. **防御点写进严谨版**：互斥锁要写「锁超时防死锁 + 双重检查 + 回填错开 TTL」，否则演示是假的。
4. **白话版不掩盖差异**：类比要覆盖关键约束，不能为了好懂而删掉「锁会抬高延迟」「单节点锁会丢」这类代价。
5. **自测题必须含改变条件**：只问「是什么」不算；要问「删掉/换掉某环节会怎样」。

## 踩坑

1. **`ids` 必须是真数组**：生成器里 `const ids = {comp_ids}` 不能写成 `const ids = [{comp_ids}]`，否则变成「含一个字符串的数组」，`getElementById('state-'+id)` 全返回 null，页面白屏并在控制台报 `Cannot set properties of null`。已在 v1.0.0 修正。
2. **组件 id 与 state key 必须一致**：`components[].id` 和 `steps[].state` 的 key 是同一套字符串，错一个字母该组件就永远显示「—」。
3. **状态继承**：`steps[].state` 只写**变化**的组件，未写项沿用上一步；想清空某组件状态就显式给 `{text, cls:"none"}`。
4. **截图为证**：交付前用 headless 浏览器打开，确认控制台无报错、关键步骤徽章颜色正确（击穿红 / 抑制绿），再截图。
5. **HTML 自包含**：不要外链 CSS/JS/字体，确保双击即可离线打开。

## 验证

```bash
python scripts/gen_dpv.py examples/redis-cache-breakdown.spec.json examples/redis-cache-breakdown.html
```

用浏览器打开 `examples/redis-cache-breakdown.html`：
- 播放 7 步，S4 应见「数据库：被打垮（红）」，S7 应见「缓存：命中（绿）」；
- 控制台无 `Cannot set properties of null` 等报错；
- 严谨版伪代码、白话版、2 道自测题、场景 / 限制 / 结论齐全。
