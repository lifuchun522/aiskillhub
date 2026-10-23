# dtyl｜动态原理拆解 / 动态原理可视化（v1.0.0）

> 本页对应 **WorkBuddy 版 v1.0.0**：把一句「把 X 的原理讲清楚」，变成一份 **可播放** 的自包含 HTML——结构拆解、分步动画、严谨版 + 白话版、含改变条件的自测题、场景 / 限制 / 结论，一次给全。

仓库路径：[`workbuddy/skill/dtyl/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/dtyl)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/dtyl/SKILL.md) ｜ 概览：[`README.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/dtyl/README.md) ｜ 规格契约：[`references/spec-format.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/dtyl/references/spec-format.md)

## 一句话

输入一条技术原理（例：Redis 热点缓存过期 + 互斥锁抑制击穿），产出一份双击即可播放的 HTML：一排组件状态徽章随步骤演化，直观看到「无锁时数据库被打垮、加锁后单线程回源并恢复命中」，并附严谨伪代码、白话类比、改变条件自测题与落地结论。

## 它解决什么问题

讲原理难的不是「念定义」，而是三件事：

| 痛点 | 本技能的做法 |
|---|---|
| 静态文字讲不清时序 | 7 步可播放动画 + 进度条，组件状态逐步变色 |
| 只说「加个锁就好了」没有信息量 | 「无锁击穿」与「加锁抑制」并排演，差异可见 |
| 代价被藏起来 | 强制保留「限制」区块与「改变条件」自测题（延迟、丢锁、双回源） |

## 输出八块（缺一不算完成）

| # | 区块 | 要求 |
|---|---|---|
| 1 | 页首声明 | ⚠ 原理演示，非压测 / 非生产基准 |
| 2 | 结构拆解 | 组件卡片 + 职责 + 状态徽章 |
| 3 | 动态过程 | 上一步 / 播放 / 下一步 / 重置 + 进度条 |
| 4 | 严谨版 | 可直接翻译成生产代码的伪代码（含锁超时、双重检查） |
| 5 | 白话版 | 覆盖全流程的生活化类比，不掩盖关键代价 |
| 6 | 自测题 | 至少一题「改变条件」 |
| 7 | 适用场景 | 何时该用 |
| 8 | 限制 + 实践结论 | 边界、失败条件、与相邻概念区分、一句话结论 |

## 能力边界与铁律

| 铁律 | 说明 |
|---|---|
| **原理演示 ≠ 压测** | 页首强制声明；正文不得用 QPS / 延迟 / 吞吐实测数字冒充结论。要容量评估，另去做压测 |
| **相邻概念必须区分** | 击穿（单 key 过期）/ 雪崩（大量 key 同时过期）/ 穿透（查不存在的 key）机制不同，必须在 `limits` 点明 |
| **防御点写进严谨版** | 互斥锁要写「锁超时防死锁 + 双重检查 + 回填错开 TTL」 |
| **白话不掩盖差异** | 类比要覆盖「锁抬高延迟」「单节点锁会丢」等代价 |
| **自测题含改变条件** | 只问「是什么」不算；要问「删掉 / 换掉某环节会怎样」 |
| **HTML 自包含** | 不外链 CSS / JS / 字体，双击即可离线打开 |

## 安装与环境

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/dtyl ~/.workbuddy/skills/dtyl
```

- **依赖**：Python 3.8+，**仅标准库**，无需 `pip install`。
- 可选：`playwright`（仅用于截图核验，生成器本身不依赖）。

## 使用步骤

### 第 1 步：写规格 JSON

见 [`references/spec-format.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/dtyl/references/spec-format.md)。最小结构：

```jsonc
{
  "title": "标题",
  "disclaimer": "原理演示，非压测 / 非生产基准",
  "components": [{"id": "cache", "label": "Redis 缓存", "role": "热点数据"}],
  "steps": [
    {"cap": "S1 命中", "actors": ["客户端 → 缓存"], "state": {"cache": {"text": "正常", "cls": "hit"}}},
    {"cap": "S2 过期", "actors": ["客户端 → 缓存（未命中）"], "state": {"cache": {"text": "已过期", "cls": "miss"}}}
  ],
  "rigorous": "// 伪代码",
  "plain": "白话类比",
  "quiz": [{"q": "…", "change": "改变条件：…", "a": "…"}],
  "scenarios": ["…"],
  "limits": ["…"],
  "conclusion": "…"
}
```

### 第 2 步：生成

```bash
python scripts/gen_dpv.py examples/redis-cache-breakdown.spec.json examples/redis-cache-breakdown.html
```

### 第 3 步：核验并交付

用浏览器打开成品，确认 7 步可播放、S4 数据库变红、S7 缓存变绿、控制台无报错，然后交付 HTML 路径 + 关键步骤截图，并声明「原理演示，非压测」。

## 例子

| 文件 | 说明 |
|---|---|
| [`examples/redis-cache-breakdown.spec.json`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/dtyl/examples/redis-cache-breakdown.spec.json) | 完整规格：4 组件 / 7 步 / 2 题 / 6 限制 |
| [`examples/redis-cache-breakdown.html`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/dtyl/examples/redis-cache-breakdown.html) | 生成成品，双击即播 |

## 验证

- 生成器可复现：同上命令重跑，输出 HTML；
- 播放 S1→S7，组件徽章颜色与步骤语义一致；
- 控制台无 `Cannot set properties of null` 等报错（v1.0.0 已修复 `ids` 嵌套数组的坑）；
- 八块内容齐全。

## 边界

- 只解释机制，不做压测，不替代容量评估。
- 击穿 / 雪崩 / 穿透不混讲，需在 `limits` 明确区分。
- 示例用单实例语义；分布式锁的 Redlock / 看门狗 / 主从切换丢锁需在具体规格写清。
- 输出为静态 HTML，前端 JS 播放，无后端依赖。
