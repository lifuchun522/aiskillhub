"""配音通道注册表 —— 演示第二组注册表（edge 走系统 TTS，天然免 Key）。"""


class TTSSpec:
    def __init__(self, tid, free=False):
        self.tid = tid
        self.free = free


TTS_SPECS = [
    TTSSpec("edge", free=True),
    TTSSpec("azure"),
    TTSSpec("elevenlabs"),
]

TTS_REGISTRY = {s.tid: s for s in TTS_SPECS}
