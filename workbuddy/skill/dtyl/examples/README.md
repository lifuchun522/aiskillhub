# dtyl 例子（examples）

本目录是**可直接对照运行**的样例，演示「规格 JSON → 自包含动画 HTML」的完整链路。

| 文件 | 用途 |
|---|---|
| [`redis-cache-breakdown.spec.json`](./redis-cache-breakdown.spec.json) | 完整规格：Redis 热点缓存过期 + 互斥锁抑制击穿。4 组件 / 7 步 / 2 道改变条件自测题 / 6 条限制。 |
| [`redis-cache-breakdown.html`](./redis-cache-breakdown.html) | 由上面规格生成的**成品**，双击即可播放，无需服务器。 |

渲染截图见 `../screenshots/`（S4 击穿态数据库变红、S7 抑制态缓存变绿）。

## 复现

```bash
cd workbuddy/skill/dtyl
python scripts/gen_dpv.py examples/redis-cache-breakdown.spec.json examples/redis-cache-breakdown.html
# 然后双击 examples/redis-cache-breakdown.html
```

## 规格速查

```jsonc
{
  "title": "标题",
  "disclaimer": "原理演示，非压测 / 非生产基准",
  "components": [{"id": "cache", "label": "Redis 缓存", "role": "热点数据"}],
  "steps": [
    {"cap": "S1 命中", "actors": ["客户端 → 缓存"],
     "state": {"cache": {"text": "正常", "cls": "hit"}}},
    {"cap": "S2 过期", "actors": ["客户端 → 缓存（未命中）"],
     "state": {"cache": {"text": "已过期", "cls": "miss"}}}
  ],
  "rigorous": "// 伪代码",
  "plain": "白话类比",
  "quiz": [{"q": "…", "change": "改变条件：…", "a": "…"}],
  "scenarios": ["…"],
  "limits": ["…"],
  "conclusion": "…"
}
```

- **状态继承**：`steps[].state` 只写变化项，未写组件沿用上一步。
- **徽章色**：`none` 灰 / `hit` 绿 / `miss` 红 / `locked` 琥珀 / `db` 深红 / `warn` 琥珀。
- 全字段契约见 [`../references/spec-format.md`](../references/spec-format.md)。

## 验证要点

打开成品 HTML 后确认：
1. 7 步可前进 / 后退 / 自动播放，进度条随步骤推进；
2. S4 数据库徽章为「被打垮（红）」，S7 缓存徽章为「命中（绿）」；
3. 控制台无报错（尤其无 `Cannot set properties of null`）；
4. 严谨版、白话版、自测题、场景 / 限制 / 结论齐全。
