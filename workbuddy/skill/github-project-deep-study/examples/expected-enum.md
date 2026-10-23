# 特性枚举 · demo-repo

## 1. 目录结构（深度 3）
```
demo-repo/
├── app/
│   ├── services/
│   │   ├── llm_provider.py
│   │   └── tts.py
│   ├── webui/
│   │   └── ui.py
│   └── main.py
├── config.example.toml
└── README.md
```

## 2. 服务 / 模块层

**app/services/** — 2 个模块
```
llm_provider.py
tts.py
```

## 3. 注册表 / Provider 声明（可插拔点）

**ProviderSpec** — 3 项
```
deepseek
ollama
openai
```

**TTSSpec** — 3 项
```
azure
edge
elevenlabs
```

## 4. 源码中的路由声明

| 方法 | 路径 | 文件 |
|---|---|---|
| GET | `/api/v1/download/{task_id}` | `app\main.py` |
| HEAD | `/api/v1/download/{task_id}` | `app\main.py` |
| GET | `/api/v1/ping` | `app\main.py` |
| POST | `/api/v1/task` | `app\main.py` |
| GET | `/api/v1/task/{task_id}` | `app\main.py` |
| HEAD | `/api/v1/task/{task_id}` | `app\main.py` |

## 5. UI 层入口（去浏览器里读控件标签）

```
app\webui\ui.py
```
