# 六步流水线与校验清单

## 步骤 1 · 核实素材

联网检索，落地一张**事实清单**，每条都能追到来源：

| 字段 | 说明 |
|---|---|
| 时间 / 地点 | 事件本身的第一手坐标 |
| 主体 | 公司、产品、型号全称 |
| 价格 / 参数 | 具体数字，不写「大概」「约」 |
| 关键人物原话 | 一句话能引用的 |
| 第三方数据 | 机构名 + 结论 |
| 反面声音 | 至少一条，用来平衡 |

**禁止凭记忆写数据。** 记忆里的数字经常是旧版或者记混的，写错一次整篇的可信度都没了。

## 步骤 2 · 定角度与结构

四幕起步：**现象 → 原因 → 卡点 → 带走**。每幕一个论点，论点后必须跟案例里的具体部件或场景。

选题时先问三句：

1. 这件事**最反常识**的那一点是什么？
2. 读者**最容易被带偏**的地方在哪？
3. 读完能**一句话带走**什么？

三句答不上来，说明角度没定，不要往下写。

## 步骤 3 · 写正文

先写 1000 字，再砍到 500。砍的顺序：

1. 铺垫和背景介绍（读者能自己查）
2. 第二组并列证据（留最强的一组）
3. 形容词和副词
4. 重复的论点复述

**不砍**：数据、金句、比喻、反面声音。

## 步骤 4 · 生成配图

| 图类型 | 用什么生成 | 注意 |
|---|---|---|
| 场景 / 形象 | ImageGen | 图内绝不放中文（100% 乱码） |
| 示意 / 推理 | Pillow + 中文字体直排 | 画布底部留 ≥100px |
| 对比 / 流程 | Pillow | 卡片高度与画布同步调，否则下半截留白 |

配图数量 3-6 张，**「形象说明」与「逻辑推演」两处必须有**。每章最多一张，不做装饰性配图。

## 步骤 5 · 构建

```bash
python scripts/build.py --src draft.html --out 成稿.html \
  --img img1.jpg img2.jpg img3.jpg \
  --cap "图注1" "图注2" "图注3"
```

参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--width` | 900 | 内嵌图片宽度 |
| `--quality` | 82 | JPEG 质量 |
| `--band` | 84 | 底部信息条高度 |
| `--wm` | 资深架构师 李福春 | 品牌水印文字 |
| `--no-watermark` | 关 | 图片已带底带时跳过 |

## 步骤 6 · 校验清单（逐项实跑，不推断）

```bash
python - <<'PY'
import re
t = open("成稿.html", encoding="utf-8").read()
txt = re.sub(r"<[^>]+>", "", t)
n = len(re.findall(r"[\u4e00-\u9fff]", txt))
print("页面CJK:", n, "->", "达标" if n <= 1000 else "超标")
print("img:", t.count("<img"), "| data:", t.count("data:image/jpeg"), "| http:", "http" in t)
print("JS:", bool(re.search(r"\bon\w+=|<script", t)), "| style块:", t.count("<style"),
      "| class:", "class=" in t, "| id:", "id=" in t, "| input:", len(re.findall(r"<input", t)))
print("实体残留:", len(re.findall(r"&[a-zA-Z#0-9]+;", t)))
print("图X编号:", len(re.findall(r"图[一二三四五六七八]", t)))
print("口号行:", "把复杂系统，设计成简单可依赖的产品" in t)
print("br残留:", t.count("<br"))
print("占位残留:", re.findall(r"\{\{[^}]+\}\}", t) or 0)
for tag in ["div", "p", "h1", "section", "b", "span"]:
    o = len(re.findall(r"<%s[ >/]" % tag, t)); c = len(re.findall(r"</%s>" % tag, t))
    print("%-8s open=%d close=%d %s" % (tag, o, c, "OK" if o == c else "MISMATCH"))
PY
```

Playwright 实渲染必查四项：

1. **标题行数**：`h1.clientHeight / lineHeight` 取整必须 = 1
2. **栏宽**：`section` 盒子宽度 = 677
3. **逐图截图**：中文无乱码、底带左侧图注与右侧水印同排
4. **页高**：无异常塌陷（例如图片没加载出来导致高度只有几百 px）

## 步骤 7 · 交付闸门（D12）

在**决定发送的那一刻**才加载 `delivery-no-pseudoblock`。加载时机早于实质工作 = 闸门失效。交付消息必须贴 D1-D12 逐项快照，每项写实际核对了什么，不写「各 D 全空」这种空话。
