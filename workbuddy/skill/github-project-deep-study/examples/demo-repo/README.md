# DemoClip —— 最小可跑示例项目

这个目录**不是真实开源项目**，是 `github-project-deep-study` 技能自带的**夹具（fixture）**，
用来演示三源枚举能抓到什么、导图数据长什么样、章节片段怎么拼。

它故意只包含三源枚举关心的四种声明形式：

| 文件 | 演示的枚举能力 |
|---|---|
| `app/main.py` | `@router.get(...)` 装饰器路由 + `add_api_route(methods=[...])` 多方法路由 |
| `app/services/llm_provider.py` | `XxxSpec("id", ...)` 注册表声明（可插拔点） |
| `app/services/tts.py` | 第二组注册表（同一正则不同前缀） |
| `app/webui/ui.py` | UI 层入口（Streamlit 控件文案来源） |
| `config.example.toml` | Key 问题单要引用的真实字段名 |

跑法：

```bash
python scripts/enum_features.py examples/demo-repo --depth 3
```

期望看到「服务 / 模块层」「注册表 / Provider 声明」「源码中的路由声明」「UI 层入口」四节。
真实输出见 `examples/walkthrough.md`。
