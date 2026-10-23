# examples · 三个可直接跑的输入

| 文件 | 体量 | 用途 | 跑完得到 |
|---|---|---|---|
| `minimal-content.json` | 3 KB · 1 个项目 / 2 段履历 | **先跑这个**。最小可用输入，验证环境对不对 | `dist/minimal-demo/index.html` + `img/card/namecard.jpg` |
| `content.json` | 39 KB · 13 个项目 / 8 段履历 / 22 张图 | 真实案例（含架构图、证书、二维码），看**满配**长什么样 | `<paths.out_dir>/index.html` + `img/` 下 22 张图 |
| `demo-content.json` | 640 KB | **不要手改**。由 `scripts/make_demo.py` 从 `content.json` 生成，图片压到演示尺寸后内联，供表单「载入示例」用 | 经 `sync_assets.py` 注入 `assets/form.html` |

`assets/namecard-demo.jpg` 是 `minimal-content.json` 用的占位名片（1000×520，纯图形 + 英文，无真实个人信息）。

## 30 秒跑通

在技能根目录执行：

```bash
python scripts/build_portfolio.py examples/minimal-content.json --skill-dir . --stats
python scripts/verify.py "dist/minimal-demo/index.html" \
    --last-section projects --must "订单履约平台重构"
```

期望输出（节选）：

```
外置 namecard            29.6 KB -> img/card/namecard.jpg
外置资源 0.03 MB ｜ index.html 0.03 MB ｜ 区块 capability+stack+career+credential+projects
STATS:{"metrics": 3, "namecard": 1, "intro": 1, "pillars": 2, "projects": 1, "stack": 1,
       "timeline": 2, "certs": 0, "qrs": 0, "images": 1, "kept": [...], "bytes": 31671, ...}
PASS: 全部检查通过
```

注意 `certs 0 / qrs 0`：这份输入没配证书与二维码，页面里对应的两个网格**整块不渲染**，
`verify.py` 对此打印 `SKIP` 而不是判缺。这是「区块由数据决定」的正常表现，不是错误。

## 改成你自己的

1. 复制 `minimal-content.json` 为 `my-content.json`；
2. 改 `content` 里的 `intro / pillars / stack / timeline / projects / edu`；
3. `images` 里每张图给一个键，`src` 写**磁盘路径**（相对当前工作目录，或配 `paths.src_dir`）；
4. 项目卡的 `fig` 填图片键 → 出架构图；留 `""` → 只出文字卡，编号仍连续；
5. `paths.out_dir` 决定产物落哪，`paths.external` 非空（如 `"img"`）则图片外置。

字段全量规格见 [`../references/03-content-schema.md`](../references/03-content-schema.md)。

## 两个常见手误

- **图片键没被正文引用** → 构建报错 `正文引用了 images 段里没有的资源键`：先检查键名拼写；
- **只拷走 `index.html`** → 外置模式下页面全破图。产物是一个**目录**，`index.html` 与 `img/` 必须同级一起发。
