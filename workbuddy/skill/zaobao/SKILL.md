---
name: zaobao
description: 将三栏早报形成芒格三问、三道架构讨论、微信HTML和手绘白板图；首页附早报Markdown创作链接，运行后只交付一个带用户本地时间戳的article-YYYYMMDDHHMM.zip，Skill仅在明确要求时另行交付。图片生成统一使用 hy3（混元图像 3.0）。
version: 6.2.0
---

# zaobao v6.2｜早报三问、同盟讨论、手绘图及发布包（hy3 出图版）

## 1. 输入、输出

**输入：**【科技热点】【架构文章推荐】【今日一言】三个栏目。必须分别抽一个问题，不得挪用其他日期话题。保留早报逐字原文及真实 URL。

**正式输出 `article-YYYYMMDDHHMM.zip`：**（例如 `article-202610101257.zip`；执行完成时按用户本地时区生成，不采用早报日期）

```text
article-YYYYMMDDHHMM.zip
├── index.html             # 早报原文+三问芒格回答，首页导航含 2 个 HTML 和 md/zaobao.md
├── talk.htm               # 同盟3个讨论：复制引导语→独立配图→主持人答案
├── index.json             # wxp-writer 标准元数据
├── md/
│   ├── zaobao.md         # 三问三答，段落间空行
│   ├── talk.md           # 三道同盟讨论，带背景、角度、模型答案与改进项
│   └── talk-prompts.txt  # 三段群发讨论引导语
├── img/
│   ├── original-brief-imagegen.png # hy3（混元图像 3.0）原始早报技术白板
│   ├── original-talk-imagegen.png  # hy3（混元图像 3.0）原始讨论技术白板
│   ├── 01-brief-whiteboard.png    # 真实 hy3 早报白板原画（保持构图）
│   ├── 02-talk-whiteboard.png     # 真实 hy3 同盟白板原画（必要时仅裁去图片页眉制作用语）
│   ├── brief-topic-{1,2,3}.png   # 可单独截图/分享的早报块
│   └── talk-topic-{1,2,3}.png    # 可单独截图/分享的讨论块
└── imagegen-provenance.json      # 原始 hy3 回执、哈希、衍生方式
```

**发布 ZIP 内不得包含 `skill/`、开发测试日志等目录。默认 `checkStatus=unaudited`，不得宣称已在微信后台发布。**

**用户可见输出合同：** 每次调用 `zaobao`，研究、写作、出图、测试、打包均自动闭环；完成后最终回复只展示一个可下载的 `article-YYYYMMDDHHMM.zip` 链接，不展示多份单文件、测试报告或 Skill 包，也不要求用户再追问“给我产物”。仅用户本次明确要求 Skill 安装包、测试报告或其他文件时，再追加其指定交付物。时间戳按运行完成时用户时区（默认 `Asia/Shanghai`，可通过 `--timezone` 指定）生成，精确到分钟，必须实际创建并校验文件后才能给下载链接。默认不得额外展示其他附件链接。

## 2. 资料检索与问题设计

1. 按标签保存完整原文；提炼引导词：对象、问题、技术机制、产品体验、AI边界、成本、风险、商业价值。仅保留原文中有的事实；有链接必须先阅读。
2. 按官方文档→官方发布说明→标准/RFC/论文→权威文章的层级核验；无链接则搜索对应关键词。用七问法：事实、核心命题、机制、条件、反例、二阶后果、行动。
3. 对每栏提出**一个短、专业、尖锐、能迫使架构师做取舍的问题**。三个问题必须紧贴三栏原文，不得把无关话题强塞入来。
4. 芒格思维模型选 1–2 个，逐个给**名称与定义**，用模型要点推导结论而不是贴标签。答案依次：**第一句明确结论→模型及定义→分析推演→3–5条工程措施→边界/指标→一句话小结→参考URL**。单题回答 ≤500 中文字符（原文、链接不计）。
5. `md/zaobao.md` 三个自然段，段落间恰好一个空行；每段格式：`技术思考问题N：问题？ | 芒格模型：……核心结论：……模型推演：……工程落地：……边界与验证：……一句话小结：……参考资料：真实链接 ---【栏目】完整原始文案`。

## 3. 架构师同盟的讨论帖格式

每栏对应一个同盟话题。以真实聊天风格写 100–340 字的**可直接复制开场白**：

- 先用「各位老师早上好。」引入一个现象/原文和自己数字人、智能客服的类比。
- 抛出自己的初步判断，必须包含「我的判断是：」。
- 末尾**恰好一个问句**，兼具竞争目标或架构取舍；答案不要提前泄露给群成员。
- 发群话术后配独立 `talk-topic-N.png`，之后才提供主持人参考答案：**第一句直接下结论→芒格模型名称及定义→系统性失败原因→数字人/智能客服项目方案→拟改进项→衡量指标→一句话小结**。
- “建议的演进措施”与“已上线的生产事实”要区分，不能伪造运行数据或系统能力。

本期示例对应：①即时生成 UI 与审批权限；②11篇文章+11条视频与真实试用；③模型声称完成与真实事务状态。**不转成 Claude Code、WorkBuddy 或其他期的话题。**

## 4. 用户确认的白板漫画手绘风格（v6 强制）

**风格参考以 `assets/style-reference-brief.png` 和 `assets/style-reference-talk.png` 为准。** 用户确认的白板漫画手绘：纯白底、粗细不齐的黑色马克笔外框、粗糙手绘线条、漫画人物/小机器人/问号/箭头作为轻量装饰、橙红为主要重点标注色、少量淡黄纸签与少量淡蓝点缀。结构图中的每条线须有明确数据或控制流含义；内容构图要活泼、有机，而不是 Excel 网格。

- **必须真实使用 hy3（混元图像 3.0，通过 ImageGen 工具调用）生成源架构图**，出图时用这两个图作为风格锚点（以 `image1` 传入风格参考并给出内容描述）。不要使用程序替代 hy3 创作架构图；程序仅能裁剪与等比归一到画布，不得重新画技术模块、重排成廉价模板。不要输出蓝色大标题卡片、网页 UI 复刻、照片感人像或软件自动生成的精致矢量卡片风。
- **三个栏目分别占据可完整截图的独立矩形区域**。每栏包含：真实早报内容对应的手绘架构图；独立红橙问题矩形；同盟图中紧跟问题的模型回答与改进矩形。每个子区域不与其他栏交叉，依然允许矩形内部架构节点自由布置。
- `01-brief-whiteboard.png` 与 `02-talk-whiteboard.png` 应尽可能直接沿用整张已校准的 hy3 原画，禁止为方便截图而重绘整图。`brief-topic-N.png`、`talk-topic-N.png` 只能从对应真实原画按完整主题矩形做像素裁剪（原画先等比归一到标准画布 `1448×1086` 后再按固定坐标裁剪）。
- **禁止制作用途文案进入图片**，包括但不限于“便于截图”“方便发起讨论”“问题与回答分区”“每个主题独立成块”“写作目标”“适合分享”；这些只写在 Skill、README 或 HTML 操作提示里，不是用户要看的早报正文。禁止页脚广告、署名、版权水印。保留唯一主题标题及事实/技术标签。
- **内容核验先于美观**：每期只展示【科技热点】【架构文章推荐】【今日一言】三个本期标签的真实内容；不可把其他期的 GPT-6、22 篇内容等放进本期 Gemini Agent + Vibe Coding + 判断力早报。模型回答和项目案例须与三栏一一对应；对错别字、英文技术名、日期年份、错误栏目进行人工目视复核。错误图不得入包。
- **溯源明确**：`original-*-imagegen.png` 保留 hy3 原始图片字节及 SHA-256；生成回执有记录时填写真实生成 ID，回执缺失时明确写“此前生成记录缺失”，不得编造。衍生图及分栏图在 `imagegen-provenance.json` 列出准确裁切/归一操作，不得冒称直接生成。
- **如正在使用的生成结果质量不满足规则，自动重新生成并检查，不能以程序绘图兜底。若复用此前通过复核的同一期 hy3 画稿，必须逐项核对本期三个栏目一致性。**

**回归样例**：三栏分别为【科技热点】企业级通用 Agent、【架构文章推荐】AI 编程/Vibe Coding、【今日一言】技术判断力；输入保留原始全量文案，图片引用 `assets/` 的风格参考并用 hy3 出图。禁止把无关期次的话题写进本期成品。

## 5. HTML 规则（v6.1 更新）

- `index.html`：首部早报白板图片 → 标题与导航 → 三条真实文字问答、原始素材全文 → 尾部讨论图片。
- `talk.htm`：首部同盟白板图 → 三个可复制群发话术和各自独立配图 → 主持人模型答案 → 尾部早报图片。
- 中间所有正文保持真实 HTML 文字可选中复制，UTF-8、自适应宽度、微信友好的**内联 CSS**，仅使用 ZIP 内图片相对路径，不依赖 CDN 或 JS。
- **首页资源导航严格保留三个入口**：`index.html`、`talk.htm` 和 `md/zaobao.md`（用于自媒体内容创作）。不得添加 `md/talk.md`、`talk-prompts.txt`、`img/` 资源导航或页内问题锚点导航。Markdown 作为 ZIP 内相对链接，在新页签打开。
- **所有 HTML 页面上的每个 `<a>`（包括首页导航、讨论页返回入口、外部官方参考资料及潜在页内链接）都必须带 `target="_blank" rel="noopener noreferrer"`。** 不允许只给部分导航加 `_blank`。内部地址使用相对路径，不能在 HTML 中出现 `file://`、容器绝对路径，或未部署公网地址。
- `index.json` 的 `resourceLinks` 必须与三条真实导航路径一致；沿用 wxp-writer：`title`、`summary`、`backgroundImage`、`articlePath`、`imagePaths`、`tags`；增量 `talkPath`、`resourceLinks`（两个 HTML + 早报 Markdown）、`checkStatus`。
- 资源路径在解压包内验证；将 HTML 复制粘贴到微信公众号后平台可能移除或重写相对链接，不能宣称已在微信后台进行发布验收。

## 6. 执行与确定性测试

```bash
python scripts/build.py \
  --input examples/demo-2026-10-08.json \
  --brief-image /path/to/verified_imagegen_brief.png \
  --talk-image /path/to/verified_imagegen_talk.png \
  --gen-brief REAL_HY3_ID_1 --gen-talk REAL_HY3_ID_2 \
  --out /mnt/data/zaobao-build \
  --timezone Asia/Shanghai

ZAOBAO_TEST_BRIEF_IMAGE=/path/to/verified_imagegen_brief.png \
ZAOBAO_TEST_TALK_IMAGE=/path/to/verified_imagegen_talk.png \
python -m unittest discover -s tests -v
python scripts/browser_smoke.py --root /mnt/data/zaobao-build --reports /mnt/data/zaobao-reports
```

上面 `REAL_HY3_ID` 仅为 CLI 参数示意，不可伪造。每轮实际测试源图都要提供对应真实 hy3 回执。负例必须覆盖错误栏目/锚点、过长答案、双重问句、图像质量或裁切不符、遗失链接/路径、任一 HTML `<a>` 未使用 `_blank` 或缺 `noopener noreferrer`、ZIP 不完整、Skill 混入 ZIP。检测图像白底比例与哈希只是辅助，最终还要目视核查内容和分区。

## 7. D1–D12 末端闸门

读取 `references/D1-D12.md`，**在生成、打包、完整测试以及拟发送回复都确定之后**进行最终 D1–D12 审计；不能在回合开头提前盖章。每条输出 HIT/CLEAR；发现 HIT 先修复重跑。只对确实执行过的验收打勾。完成时交唯一的 `article-YYYYMMDDHHMM.zip` 链接；只有用户明确要求 Skill ZIP 或核验报告才另行提供；保留人工审核上架步骤，但制作、内容正确性、校验均由 AI 负责。

## v6.1 图片强制回归规则

测试必须核对两张原画 SHA-256、三栏截图取自原画（原画先等比归一到标准画布 `1448×1086` 再按固定坐标裁剪）、早报内容三个栏目逐条对应、输出图片无制作用语、两份 HTML 全部 `<a>` 新页签打开、正式归档 ZIP 无 Skill 目录。质量审查采用人工目视 + 自动化结构校验，不能仅靠色彩阈值证明“风格已一致”。

## v6.2 hy3 出图与画布归一强制回归

1. 源架构图一律由 **hy3（混元图像 3.0）** 生成，`assets/style-reference-*.png` 作为风格锚点；禁止用代码绘制或重排技术模块。
2. hy3 原生输出尺寸不固定。构建时先把两张原画**等比归一到标准画布 `1448×1086`**，再套用已校准的固定裁剪坐标；归一属于允许的确定性衍生操作，须在 `imagegen-provenance.json` 中如实记录（`operation` 写明 resize→crop）。
3. `original-*-imagegen.png` 保留 hy3 原始字节不变（`original_pixels_unchanged=true`）；`01/02-*-whiteboard.png` 与 `*-topic-*.png` 标注为归一/裁剪后的确定性衍生图。
4. 归档命名、双 HTML `<a>` 新页签、单一产物、无 Skill 目录等 v6.1 规则继续生效。


## v6.1 单一产物与时间戳强制回归

1. 运行 `scripts/build.py` 不再生成无日期的 `article.zip`，必须生成 `article-YYYYMMDDHHMM.zip`；时间戳取**打包时刻**而非输入新闻日期，使用用户所在时区，默认 `Asia/Shanghai`。
2. 时间戳生成函数为确定性纯函数：允许注入携带时区的测试时刻，覆盖跨时区转换、无时区时间拒绝、格式长度和无效时区。
3. `index.html` 必须有 `href="md/zaobao.md" target="_blank" rel="noopener noreferrer"`；该目标必须确实存在于最终 ZIP，`index.json.resourceLinks` 与导航保持一致。
4. 最终发布 ZIP 不含 Skill；允许在制作期间生成内部报告，但**用户可见最终回复只显示一条归档下载链接**。除用户本次明确提出其他交付物的情况外，不附带单图、MD、HTML、报告或 Skill 的独立链接。
5. 禁止在结果中写“可继续生成”“需要追问才能拿文件”等延期话术。成功必须以产物存在、ZIP 完整性检查、内容与图像核验为依据。
