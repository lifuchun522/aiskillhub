# cloudq-oss-cert-rotation

OSS 自定义域名证书的巡检 Skill 原型（v1.4.0）。只读诊断层（入口识别 / TLS 探活 / 结果页 / 效率对照）保持零凭证、零写操作；v1.4 新增带授权门控的轮换模块 `cert_rotate.py`，可在显式 `--authorized` 下重新申请免费证并部署到 OSS。用于在更换证书前先确认访问入口与证书状态，实测耗时并生成结果页面，再产出需要人工授权的更新操作单；同时给出「人工基线 vs Skill 路径」的可审计效率对照。

- **只读**：DNS 查询 + HTTPS GET（不读响应体）+ TLS 握手；不申请、不部署、不回滚。
- **无凭证**：不读取云账号 AK/SK，不连接云 API。
- **不猜根因**：任何外部失败写入 `errors[]` 并保留 `error_type`；`UNVERIFIED` ≠「证书已过期」。
- **不硬猜入口**：取不到响应头就给 `UNKNOWN`，不凭 CNAME 名字推断。
- **有口径**：结果页写明样本量、观测窗口、分位数算法与外部调用次数。
- **不混口径**：效率对照里人脑段永远标注为建模区间，不写成实测；不申报节省写操作工时。

## 快速开始

```bash
python3 scripts/entry_probe.py --domain example.com
python3 scripts/cert_probe.py --domain example.com --warn-days 30
python3 scripts/probe_report.py --domain example.com --rounds 20 --out-dir report/
python3 scripts/bench_baseline.py --domain example.com --runs 10 --out-dir report/
python3 -m unittest discover -s tests -v
```

## 轮换（写操作，授权门控，v1.4 新增）

`scripts/cert_rotate.py` 把"换证书"真正落地，但**任何写操作必须显式 `--authorized` 才执行；AK/SK 仅从环境变量读取，绝不落盘**。

```bash
# 离线生成更新操作单（无需 AK）
python3 scripts/cert_rotate.py plan --config config.example.json

# 只读查询免费额度 / 证书列表 / OSS CNAME 状态（需 AK，仍不写）
ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=yyy \
  python3 scripts/cert_rotate.py inspect --config config.example.json

# 真正执行：申请免费证 -> DNS 验证 -> 轮询签发 -> 下载 -> 部署 OSS（必须 --authorized）
ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=yyy \
  python3 scripts/cert_rotate.py rotate --config config.example.json --authorized
```

- 流程六步：检查免费额度 → 申请免费证（消耗 1/20 额度）→ DNS TXT 验证（默认手动加；`--auto-dns` 可在同账号自动加）→ 轮询至签发 → 下载证书（默认仅内存，不落盘）→ 部署到 OSS 自定义域名（覆盖旧证）。
- 依赖 `alibabacloud_cas20200407` / `oss2`（见 `requirements-rotate.txt`），仅在 `rotate`/`inspect` 真正执行时才 `import`，因此可被离线单测完整覆盖。
- 免费证不支持"续费"，本质是重新申请一张 3 个月新证；每年每账号上限 20 张单域名。

## 入口判定

| 结果 | 含义 |
|---|---|
| `OSS_DIRECT` | 回包由 OSS 直接应答（`Server: AliyunOSS` 或 `x-oss-*` 头），无 CDN 特征头 |
| `BEHIND_CDN` | 响应头出现 CDN 特征头；或仅 CNAME 命中 CDN 片段（弱提示） |
| `UNKNOWN` | 无响应头且 CNAME 无线索，入口未确定 |

> CNAME 名称里有没有 `oss-cn-*` **不能**作为判据；回包才是强证据。

## 证书状态

| 状态 | 含义 |
|---|---|
| `HEALTHY` | 握手成功、信任链与主机名校验通过、剩余天数 ≥ `--warn-days` |
| `EXPIRING` | 握手成功、校验通过，但剩余天数 < `--warn-days` |
| `UNVERIFIED` | DNS 不通 / 握手失败 / 证书过期 / 域名不匹配，附 `error_type` |

## 结果页面

`probe_report.py` 产出 `cert-report.html` / `.md` / `.json`，页内固定包含：

- 样本量（轮数）与观测窗口（UTC 首末时间戳）
- 入口识别、证书探活、整轮合计三段耗时（min / P50 / P95 / max / 均值）
- 失败轮次与失败率
- 外部只读调用清单（每轮 3 次，合计 = 3 × 轮数）

**性能纪律**：单次样例不代表总体表现。少于 20 轮时 P95 等于观测到的最大值，须在结论里说明；
实测中同一台机器上证书握手曾在 `80–150 ms` 与 `7.7–8.0 s` 两个量级间跳动。

## 效率对照

`bench_baseline.py` 产出 `baseline-report.html` / `.md` / `.json`，把一次巡检拆成两段：

- **机器段（实测）**：人工命令序列（`nslookup` → `curl -sSI` → `openssl s_client`）与 Skill 单命令，
  各真实执行 `--runs` 次并计时；
- **人脑段（建模）**：发现异常、判定入口、计算分级、成文操作单，按区间列出并标注依据类型。

三条纪律：

1. 口径不混 —— 人脑段永不写成实测值；
2. 范围不夸大 —— 只对照「发现 + 诊断 + 成文」，写操作两条路径都要人工授权；
3. 不报倍数 —— 机器段差值常被网络抖动淹没，结论应落在「量级差出现在人脑段」。

## CloudQ 接入测试

见 `references/cloudq-integration-test.md`：四个入口、六步测试（冒烟 / 只读触发 / 证据核对 /
写操作边界 / 失败路径 / 授权链路）、每步判据与总通过标准。

## 边界声明

本 Skill 是**可检查的原型**，不是 CloudQ 已上线插件；不包含自动部署能力。
本地实跑通过不等于 CloudQ 租户内端到端调用已验证 —— 验证方法见上面的接入测试文档。
