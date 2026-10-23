# dtyl 规格 JSON 契约

`gen_dpv.py` 的输入是一份 JSON。本文件定义全部字段、状态徽章取值与继承语义。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | string | 是 | 页面标题（H1） |
| `subtitle` | string | 否 | 副标题 |
| `disclaimer` | string | 否 | 页首声明；默认「原理演示，非压测 / 非生产基准」 |
| `components` | array | 是 | 参与组件，见下 |
| `steps` | array | 是 | 动态步骤，见下 |
| `rigorous` | string | 否 | 严谨版；`\n` 会渲染为换行，放在 `<pre>` 里 |
| `plain` | string | 否 | 白话版 |
| `quiz` | array | 否 | 自测题，见下 |
| `scenarios` | string[] | 否 | 适用场景 |
| `limits` | string[] | 否 | 限制 |
| `conclusion` | string | 否 | 实践结论 |

## components[]

```jsonc
{"id": "cache", "label": "Redis 缓存", "role": "热点数据"}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 组件唯一标识；`steps[].state` 用它做 key，前端用它定位徽章 |
| `label` | 是 | 显示名 |
| `role` | 否 | 职责说明（卡片副标题） |

> `id` 必须全篇唯一。改 `id` 时同步改所有 `steps[].state` 的 key，否则该组件永远显示「—」。

## steps[]

```jsonc
{
  "cap": "S4【无锁】所有请求直接击穿到数据库，数据库瞬时被打垮。",
  "actors": ["客户端 → 数据库（并发 ×5，直接击穿）"],
  "state": {
    "cache": {"text": "未命中", "cls": "miss"},
    "db": {"text": "被打垮", "cls": "db"}
  }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `cap` | 是 | 该步字幕 |
| `actors` | 否 | 调用链描述数组，渲染为「调用链：A → B → C」 |
| `state` | 否 | 变化的组件状态；key 为组件 `id`，值为 `{text, cls}` |

**继承语义**：`state` 只需写**相对上一步发生变化**的组件。未出现的组件沿用上一步状态。要清空某组件，显式写 `{"text": "空闲", "cls": "none"}`。

## 状态徽章 cls

| cls | 颜色 | 语义（建议） |
|---|---|---|
| `none` | 灰 | 中性 / 空闲 |
| `hit` | 绿 | 命中 / 正常 / 成功 |
| `miss` | 红 | 未命中 / 失效 |
| `locked` | 琥珀 | 已加锁 / 占用中 |
| `db` | 深红 | 数据库过载 / 被打垮 |
| `warn` | 琥珀 | 重建中 / 降级 / 警告 |

## quiz[]

```jsonc
{
  "q": "若去掉『双重检查』，只在外面判一次缓存空就抢锁，会有什么问题？",
  "change": "改变条件：删除第一重 / 第二重缓存检查。",
  "a": "每个缓存未命中的请求都会去抢锁……"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `q` | 是 | 题干 |
| `change` | 否 | 「改变条件」一行；技能要求至少一题填此项 |
| `a` | 是 | 答案，`<details>` 折叠 |

## 内容硬约束（生成器不校验，靠编写者保证）

1. 页首声明必须存在，且不得在正文用压测数字冒充结论。
2. 相邻概念（击穿 / 雪崩 / 穿透）必须在 `limits` 里区分。
3. 严谨版必须包含关键防御（如锁超时、双重检查、TTL 错开）。
4. 至少一道 `quiz` 带 `change`。
5. 白话类比不得掩盖关键代价（延迟、丢锁、双回源）。

## 完整示例

见 [`../examples/redis-cache-breakdown.spec.json`](../examples/redis-cache-breakdown.spec.json)。
