"""文案生成通道注册表 —— 演示 XxxSpec("id", ...) 形式的可插拔点枚举。"""


class ProviderSpec:
    def __init__(self, pid, free=False, base_url=""):
        self.pid = pid
        self.free = free
        self.base_url = base_url


LLM_SPECS = [
    ProviderSpec("openai", base_url="https://api.openai.com/v1"),
    ProviderSpec("deepseek", base_url="https://api.deepseek.com"),
    ProviderSpec("ollama", free=True, base_url="http://127.0.0.1:11434/v1"),
]

# 计数口径：一律 len(LLM_PROVIDER_REGISTRY)，不要 grep 手数
LLM_PROVIDER_REGISTRY = {s.pid: s for s in LLM_SPECS}
