# dtyl

把一条技术原理讲成**看得见的动态过程**的技能（v1.0.0）。

喊一句「把 Redis 缓存击穿的原理动态地讲清楚」，它不给你一段解释文字，而是产出一份**自包含、可播放**的 HTML：左边一排参与组件（客户端 / 缓存 / 互斥锁 / 数据库），点「播放」看机制一步步演化——缓存过期、请求涌入、无锁时数据库被打垮、加锁后单线程回源、回填、恢复命中。每一步组件的状态徽章实时变色，读者一眼看懂「锁到底改了什么」。

- **可播放**：上一步 / 播放 / 下一步 / 重置 + 进度条，7 步动画把「无锁击穿 vs 加锁抑制」摆在一起对比。
- **双版本**：严谨版给可直接翻译成生产代码的伪代码；白话版用生活化类比覆盖同一机制，且不掩盖关键代价。
- **含改变条件的自测题**：不只问「是什么」，而是问「删掉双重检查会怎样」「换成随机退避能不能替代锁」，答案点明退化路径。
- **原理演示，不是压测**：页首强制声明；正文不给 QPS / 延迟实测数字冒充结论。要容量评估，另去做压测。
- **零依赖**：生成器纯 Python 标准库，输出 HTML 内联 CSS/JS，双击即可离线打开。

## 快速开始

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cp -r aiskillhub/workbuddy/skill/dtyl ~/.workbuddy/skills/dtyl
```

```bash
# 1) 写一份规格 JSON（字段见 references/spec-format.md）
# 2) 生成
python ~/.workbuddy/skills/dtyl/scripts/gen_dpv.py my.spec.json out.html
# 3) 双击 out.html
```

或直接看现成例子：

```bash
cd workbuddy/skill/dtyl
python scripts/gen_dpv.py examples/redis-cache-breakdown.spec.json examples/redis-cache-breakdown.html
```

## 它解决什么问题

讲原理时，真正难的不是「把定义念一遍」，而是三件事：

1. **状态在时间上怎么变。** 缓存「过期 → 未命中 → 击穿 → 回填 → 命中」是一条时间线，静态段落很难让读者建立时序。可播放的步骤动画把每一步的组件状态摆出来，时序自己会说话。
2. **「加了个东西」到底改变了什么。** 只说「加互斥锁就好了」没有信息量。动画把「无锁：5 个请求同时打到 DB → DB 被打垮」和「加锁：1 个回源、其余等待 → 回填 → 恢复」并排演一遍，差异可见。
3. **代价藏在哪。** 锁会抬高未命中期间的延迟、单节点锁在主从切换时会丢、锁超时过短会双回源——这些不写进限制，演示就是骗人的。本技能强制保留「限制」区块与「改变条件」自测题。

## 输出长什么样

生成页固定 8 块（缺一不算完成）：

| 区块 | 内容 |
|---|---|
| 页首声明 | ⚠ 原理演示，非压测 / 非生产基准 |
| 结构拆解 | 组件卡片 + 职责 + 状态徽章 |
| 动态过程 | 分步播放器（上一步 / 播放 / 下一步 / 重置 + 进度条） |
| 严谨版 | 伪代码 / 公式（含锁超时、双重检查等关键防御） |
| 白话版 | 一个覆盖全流程的生活化类比 |
| 自测题 | 至少一题「改变条件」 |
| 适用场景 | 何时该用 |
| 限制 + 实践结论 | 边界、失败条件、与相邻概念的区分、一句话结论 |

`examples/redis-cache-breakdown.html` 就是完整成品：7 步、4 个组件、2 道改变条件自测题、6 条限制。`screenshots/` 下是渲染截图（S4 击穿态数据库变红、S7 抑制态缓存变绿）。

## 规格 JSON

最小可运行结构：

```jsonc
{
  "title": "Redis 热点缓存过期后，互斥锁如何抑制缓存击穿",
  "disclaimer": "原理演示，非压测 / 非生产基准",
  "components": [
    {"id": "cache", "label": "Redis 缓存", "role": "热点数据"},
    {"id": "db", "label": "数据库", "role": "真实数据源"}
  ],
  "steps": [
    {"cap": "S1 命中", "actors": ["客户端 → 缓存"], "state": {"cache": {"text": "正常", "cls": "hit"}, "db": {"text": "空闲", "cls": "none"}}},
    {"cap": "S2 过期", "actors": ["客户端 → 缓存（未命中）"], "state": {"cache": {"text": "已过期", "cls": "miss"}}}
  ],
  "rigorous": "// 伪代码",
  "plain": "白话类比",
  "quiz": [{"q": "删掉双重检查会怎样？", "change": "改变条件：删除缓存检查", "a": "每个未命中请求都去抢锁……"}],
  "scenarios": ["热点 key 集中过期"],
  "limits": ["锁必须带超时"],
  "conclusion": "一句话结论。"
}
```

字段全表与状态徽章取值见 [`references/spec-format.md`](references/spec-format.md)。

## 例子

- [`examples/redis-cache-breakdown.spec.json`](examples/redis-cache-breakdown.spec.json) — 完整规格：4 组件 / 7 步 / 2 题 / 6 限制。
- [`examples/redis-cache-breakdown.html`](examples/redis-cache-breakdown.html) — 由上面规格生成的成品，双击即可播放。
- [`examples/README.md`](examples/README.md) — 复现方法与字段速查。

## 验证

```bash
python scripts/gen_dpv.py examples/redis-cache-breakdown.spec.json examples/redis-cache-breakdown.html
```

打开生成的 HTML，确认：
- 7 步可前进 / 后退 / 自动播放；
- S4 数据库徽章为「被打垮（红）」，S7 缓存徽章为「命中（绿）」；
- 控制台无报错（尤其无 `Cannot set properties of null`）；
- 严谨版、白话版、自测题、场景 / 限制 / 结论齐全。

## 边界声明

- **只解释机制，不做压测**：不产出 QPS / 延迟 / 吞吐实测，也不替代容量评估。
- **相邻概念不混讲**：击穿（单 key 过期）、雪崩（大量 key 同时过期）、穿透（查不存在的 key）机制不同，本技能的规格要求你在限制里点明。
- **示例用单实例语义**：分布式锁的 Redlock / 看门狗 / 主从切换丢锁等，需在具体规格的 `limits` 里写清，不能默认「有锁就万事大吉」。
- **生成器不联网**：纯本地渲染，输出为静态 HTML；播放逻辑是前端 JS，无后端依赖。
