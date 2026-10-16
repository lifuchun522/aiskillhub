---
name: cloudq-oss-cert-rotation
description: 当用户提到 OSS 自定义域名证书快过期、网站提示不安全时，先只读检查访问入口与证书状态，实测耗时并生成结果页面、更新操作单与人工基线效率对照；可经显式 --authorized 执行免费证重新申请并部署到 OSS，但任何写操作都必须人工授权。
---

# cloudq-oss-cert-rotation · OSS 自定义域名证书只读巡检

> 版本 1.4.0。在 1.3.1 只读巡检基础上，新增**带授权门控的轮换模块** `cert_rotate.py`（免费证重新申请 + 部署到 OSS）。
> 只读诊断层保持零凭证、零写操作；写操作仅在显式 `--authorized` 且提供环境变量 AK 时执行，未授权时只产出更新操作单。

> 只读诊断层不申请、不部署、不回滚证书，也不读取任何云账号 AK/SK；只向用户指定的报告目录写结果文件。
> 轮换模块 `cert_rotate.py` 仅在 `--authorized` 时读取环境变量中的 AK/SK 并执行写操作，未授权时只出操作单、不触碰任何云资源。

## 什么时候用它

- 用户说「网站提示不安全」「证书快过期了」「域名访问打不开」；
- 需要确认某个自定义域名的 TLS 证书是否有效、还剩多少天；
- 需要先弄清「访问入口是 OSS 直连还是 CDN」，再决定证书该部署到哪里；
- 需要一份可复核的**结果页面**（含耗时 P50/P95、外部调用次数与证据），而不是一句结论；
- 需要「自动化比人工省多少」的**可审计对照**，而不是一个拍出来的倍数。

## 权限模型（先分清两件事）

| 用户意图 | 动作 | 权限 |
|---|---|---|
| 「帮我查查证书还有多久到期」 | 只读识别入口 + 一次只读 TLS 握手 + 写结果页面到本地目录 | 只读，可直接执行 |
| 「把 OSS 的证书换掉」（未授权） | 生成更新操作单，停在授权步骤 | **需人工授权**，无 `--authorized` 不执行 |
| 「把 OSS 的证书换掉」（已授权） | `cert_rotate.py rotate --authorized`：重新申请免费证 + 部署到 OSS | **需显式 `--authorized` + 环境变量 AK**，否则拒绝执行 |

## 执行步骤

1. **确认接入入口**（`entry_probe.py`）：一次 DNS 查询 + 一次只读 HTTPS GET，按**响应头为主证据**判定：

   ```bash
   python3 scripts/entry_probe.py --domain example.com
   ```

   - `OSS_DIRECT`：回包由 OSS 直接应答（`Server: AliyunOSS` 或出现 `x-oss-*` 头），且无 CDN 特征头。
   - `BEHIND_CDN`：响应头出现 `x-cache` / `via` / `ali-swift-stat-host` 等 CDN 特征；或仅 CNAME 命中 CDN 片段（弱提示，证据里会写明）。
   - `UNKNOWN`：取不到响应头、CNAME 也无线索 → **入口未确定**，交由人工判断，**不硬猜**。

   > **判据纪律**：CNAME 名称里有没有 `oss-cn-*` **不能**用来判定入口。真实案例中自定义域名 CNAME 到非 OSS 域名，回包仍是 `Server: AliyunOSS`，本质是 OSS 直连。

2. **只读探活**（`cert_probe.py`）：

   ```bash
   python3 scripts/cert_probe.py --domain example.com --warn-days 30
   ```

   - `HEALTHY`：握手成功、信任链与主机名校验通过、剩余天数 ≥ 阈值。
   - `EXPIRING`：握手成功、校验通过，但剩余天数 < 阈值。
   - `UNVERIFIED`：DNS 不通 / 握手失败 / 证书过期 / 域名不匹配等，保留 `error_type`，
     **不擅自认定具体根因**。`UNVERIFIED` ≠「证书已过期」。

3. **巡检并生成结果页面**（`probe_report.py`，v1.2 新增）：把上面两步合成一次巡检，重复 R 轮，
   统计端到端耗时并渲染结果页：

   ```bash
   python3 scripts/probe_report.py --domain example.com --rounds 20 --warn-days 30 --out-dir report/
   ```

   产出 `report/cert-report.html`（结果页面，内联样式、可直接预览或复制）、
   `report/cert-report.md`（同源 Markdown）与 `report/cert-report.json`（原始结构）。

   结果页必须写明三件事，缺一不可：
   - **样本量**：`--rounds` 轮，默认 5；少于 20 轮时 P95 会退化成观测到的最大值，须在结论里说明；
   - **观测窗口**：每轮的首末 UTC 时间戳；
   - **耗时口径**：最近秩法（nearest-rank）分位数，不做插值；同时给入口识别、证书探活、整轮合计三段。

   > **性能纪律**：单次样例不代表总体表现。实测中同一台机器上证书握手在 `80–150 ms` 与 `7.7–8.0 s`
   > 两个量级间跳动，只贴最快那次会得到完全错误的结论。

4. **效率对照**（`bench_baseline.py`，v1.3 新增）：把一次巡检拆成**机器段**与**人脑段**分开处理：

   ```bash
   python3 scripts/bench_baseline.py --domain example.com --runs 10 --renewals-per-year 4 --out-dir report/
   ```

   - **机器段（实测）**：人工要手敲的命令序列（`nslookup` → `curl -sSI` → `openssl s_client`）
     与 Skill 的一条命令，各自真实执行 `--runs` 次并计时，产出 P50/P95 与逐条证据。
   - **人脑段（建模，不假装实测）**：发现异常、判定入口、计算分级、成文操作单四步，
     按显式区间列出，逐条标注「依据」还是「建模」。

   产出 `report/baseline-report.{html,md,json}`。三条纪律：

   - **口径不许混**：人脑段永远不许写成实测值；区间必须让读者能代入自己的耗时；
   - **范围不许夸大**：对照只覆盖「发现 + 诊断 + 成文」。申请、部署、回滚是写操作，
     两条路径都要人工授权，**不得**把这部分算成节省；
   - **不许报倍数**：机器段两边的差值常被网络抖动淹没（实测 P95 几乎持平），
     报「快 N 倍」会误导。结论应落在「量级差出现在人脑段」这个判断上。

5. **成本口径**：每轮固定 3 次外部只读调用（DNS 1 + HTTPS GET 1 + TLS 握手 1），
   结果页显式列出，作为「调用次数 × 样本量」的分母。**不把调用次数换算成费用或人效。**
6. **生成更新操作单**（写操作前）：目标范围、当前证据、更新准备、人工授权、验收五项。
7. **停下等授权**。新证书未签发、路由不清楚、无审批时，明确终止并交人工处置。

## 轮换模块：免费证重新申请 + 部署到 OSS（写操作，授权门控）

`scripts/cert_rotate.py` 把"换证书"真正落地，但严格遵守铁律：**任何写操作必须显式 `--authorized` 才执行；AK/SK 仅从环境变量读取，绝不落盘**。

```bash
# 1) 离线生成更新操作单（无需 AK，等价于只读层的"出操作单"步骤）
python3 scripts/cert_rotate.py plan --config config.json

# 2) 只读查询免费额度 / 证书列表 / OSS CNAME 状态（需 AK，仍不写）
ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=yyy \
  python3 scripts/cert_rotate.py inspect --config config.json

# 3) 真正执行：申请免费证 -> DNS 验证 -> 轮询签发 -> 下载 -> 部署 OSS
#    必须 --authorized；否则直接拒绝并退出码 2
ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=yyy \
  python3 scripts/cert_rotate.py rotate --config config.json --authorized
```

流程六步（与操作单一致）：检查免费额度 → 申请免费证（消耗 1/20 额度）→ DNS TXT 验证（默认手动加；`--auto-dns` 可在同账号自动加）→ 轮询至签发 → 下载证书（默认仅内存，不落盘）→ 部署到 OSS 自定义域名（覆盖旧证）。

安全边界：
- 未授权（`rotate` 不带 `--authorized`，或缺少 AK）→ 拒绝执行，退出码 2，绝不悄悄写；
- AK/SK 只来自 `ALIYUN_ACCESS_KEY_ID` / `ALIYUN_ACCESS_KEY_SECRET`，脚本不读取、不打印、不写入任何文件；
- 依赖 `alibabacloud_cas20200407` / `oss2`（见 `requirements-rotate.txt`），仅在 `rotate`/`inspect` 真正执行时才 `import`，因此本模块可被离线单测（注入假客户端）完整覆盖；
- 免费证不支持"续费"，本质是重新申请一张 3 个月新证；每年每账号上限 20 张单域名。

## CloudQ 接入测试

迁到租户内验证时，按 `references/cloudq-integration-test.md` 执行。它给出四个 CloudQ 入口、
六步测试（T1 冒烟 / T2 只读触发 / T3 证据核对 / T4 写操作边界 / T5 失败路径 / T6 授权链路）、
每步判据与总通过标准。核心验证点是：**CloudQ 的授权门控与本 Skill 的只读边界能否叠起来而不互相绕过**。

## 六维自查（结论必须标状态，不给无证据的 PASS）

| 维度 | 本 Skill 的证据 | 状态 |
|---|---|---|
| 功能性 | 36+ 项离线单测：只读层覆盖正常/临期/过期/主机名不匹配/超时/DNS 失败，入口判定含「CNAME 不得越权定性」；v1.4 新增 `cert_rotate` 离线单测，用假 CAS/OSS 客户端覆盖「申请→轮询→下载→部署」全流程与授权门控；真实域名实跑 | 本地 `PASS`；CloudQ 租户内 / 真实云 API 端到端 `NOT_VERIFIED` |
| 安全性 | 只读层零凭证、零写操作；v1.4 `cert_rotate` 写链路受 `--authorized` 门控 + 环境变量 AK 双重约束，未授权零写操作，AK 不读盘不打印；`rotate` 缺授权/缺 AK 一律拒绝并退出码 2 | `PASS`（只读链路）；写链路本地 `PASS`（门控 + 离线单测）；真实 AK 端到端 `NOT_VERIFIED` |
| 可靠性 | 任何外部失败写入 `errors[]` 并保留 `error_type`，退出码 0；`UNVERIFIED` 不冒充「已过期」 | 本地 `PASS`；跨厂商接口 `NOT_VERIFIED` |
| 用户体验 | 一句话自然语言触发；结果页给出结论、证据、耗时与下一步 | 本地实跑 `PASS`；真实值班人复核 `NOT_VERIFIED` |
| 性能效率 | `probe_report.py` 实测 P50/P95、失败率、调用次数，写明样本量与窗口 | `PASS`（本机样本，非跨环境承诺） |
| 成本效益 | `bench_baseline.py` 给出人工基线对照：机器段实测 + 人脑段建模区间，并申报不节省写操作工时 | `PASS`（诊断段对照）；写操作段 `N/A` |

## 安全边界

- 脚本仅使用 Python 标准库（`ssl` / `socket` / `urllib` / `struct` / `json` / `subprocess`），开启系统信任链与主机名校验。
- 只读：DNS 查询、HTTPS GET（**不读响应体**）、TLS 握手；不连接云 API、不读取凭证、不修改任何云资源。
- `bench_baseline.py` 会通过 shell 执行三条**固定的只读命令**（`nslookup` / `curl -sSI` / `openssl s_client`），
  命令模板写死在 `HUMAN_COMMANDS` 里，不接受外部传入的命令串。Windows 下优先用 bash 执行（命令含管道与重定向）。
- **写文件仅限结果页面**：只写 `--out-dir` 下的 `cert-report.{html,md,json}` 与 `baseline-report.{html,md,json}`，不写云资源、不写系统目录。
- 回滚不是无条件动作：仅当旧证书仍有效且旧部署对象可恢复时，回退才有意义。
- 预警阈值 `--warn-days` 默认 30 天，是可配置初始值，不是任何官方规定的阈值。
- `entry_probe.py` 默认解析服务器为 `223.5.5.5`，可用 `--dns-server` 覆盖。

## 铁律

- 入口判定以**响应头为主证据**；`oss-cn-*` 这类 CNAME 名称不得单独定性，取不到响应头就报 `UNKNOWN`，不硬猜。
- `UNVERIFIED` ≠「证书已过期」；入口判不出的情况，绝不写成「OSS 直连」。
- 单次样例不作性能结论；分位数用最近秩法、不做插值，结果页必须写明样本量与观测窗口。
- 人脑段只给建模区间并逐条标注「依据 / 建模」，不冒充实测；申请、部署、回滚这段写操作工时，一律不计入节省。
- 只读诊断不做变更：写操作只出更新操作单并终止，等有权限的人授权后再由人工执行。

## 失败与降级

任何外部失败（超时、DNS、握手、HTTP 异常）都写入 `errors[]` 并保留 `error_type`，退出码 0；
只有参数错误或脚本内部异常才返回非 0。**绝不把检查失败谎报为「证书已过期」，也绝不把入口判不出的情况谎报为「OSS 直连」，更不把人脑段的建模区间谎报成实测值。**

## 文件

- `scripts/entry_probe.py`：只读识别访问入口（OSS 直连 / 经 CDN / 未确定）。
- `scripts/cert_probe.py`：只读 TLS 探活与状态分级。
- `scripts/probe_report.py`：多轮巡检 + 耗时分位统计 + 结果页面渲染（HTML/MD/JSON）。
- `scripts/bench_baseline.py`：人工基线 vs Skill 路径效率对照（机器段实测 + 人脑段建模）。
- `scripts/cert_rotate.py`：v1.4 新增，带授权门控的轮换模块（免费证重新申请 + 部署到 OSS），`plan`/`inspect`/`rotate` 三个子命令。
- `config.example.json`：轮换模块配置样例（domain / oss_bucket / region / oss_endpoint 等）。
- `requirements-rotate.txt`：轮换模块专用第三方依赖（alibabacloud_cas20200407 / oss2 等）。
- `references/cloudq-integration-test.md`：CloudQ 接入测试方法、六步操作与通过判据。
- `tests/test_entry_probe.py`：入口判定的离线回归（含「CNAME 不得越权定性」用例）。
- `tests/test_cert_probe.py`：证书探活离线回归（含超时、过期、主机名不匹配、临期等场景）。
- `tests/test_probe_report.py`：分位数、汇总、渲染的离线回归（空样本不得被当成 0）。
- `tests/test_bench_baseline.py`：对照口径回归（建模区间求和、年度折算、实测/建模标注不得混）。
