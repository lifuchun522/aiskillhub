# cloudq-oss-cert-rotation｜OSS 自定义域名证书轮换（v1.4.0）

> 本页对应 **WorkBuddy 版 v1.4.0**：在「只读巡检」原型之上新增**带授权门控的写链路**，解决阿里云免费个人测试证书（3 个月有效期）到期后不能续费、只能重新申请并部署到 OSS 自定义域名的真实场景。

仓库路径：[`workbuddy/skill/cloudq-oss-cert-rotation/`](https://github.com/lifuchun522/aiskillhub/tree/main/workbuddy/skill/cloudq-oss-cert-rotation)

完整使用说明（HTML，逐条可核对）：[`USAGE.html`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/cloudq-oss-cert-rotation/USAGE.html)

技能规范入口：[`SKILL.md`](https://github.com/lifuchun522/aiskillhub/blob/main/workbuddy/skill/cloudq-oss-cert-rotation/SKILL.md)

## 一句话

输入域名 + OSS bucket 配置，先只读出「更新操作单」确认风险，再一键（显式授权后）完成「免费证重新申请 → DNS 验证 → 轮询签发 → 下载 → 部署到 OSS 自定义域名 HTTPS」。

## 它解决什么问题

阿里云**免费个人测试证书不支持续费**，到期只能重新申请（每账号每年 20 张单域名额度，有效期 3 个月）。大量用户误以为能「续期」，实际要做的是**重新申请 + 重新部署**。本 skill 把这套流程做成了可复用、可审计、带安全门控的工具。

| 证书类型 | 能否续期 | 本 skill 做法 |
|---|---|---|
| 免费个人测试证书（3 个月） | ❌ 不支持续费 | 重新申请 + 部署到 OSS（v1.4.0 写链路） |
| 商业付费证书（DV/OV/EV） | ✅ 可续费 | 续费延长订阅期（读链路可查状态） |
| 上传型 / 其他 CA 证书 | ⚠️ 不支持 | 回原渠道续，再上传新证 |

## 能力边界与铁律

本 skill 由两层组成，铁律**三层**：

- **只读巡检层**（原 v1.3.1）：`entry_probe` / `cert_probe` / `probe_report` / `bench_baseline`，只诊断、不写。
- **写链路层**（v1.4.0 新增）：`scripts/cert_rotate.py`，三子命令 `plan` / `inspect` / `rotate`。

铁律（缺一不可）：

1. 任何写操作（申请 / 部署 / 改 DNS）必须显式传 `--authorized`，否则只出操作单、不触云；
2. AK/SK 仅从环境变量 `ALIYUN_ACCESS_KEY_ID` / `ALIYUN_ACCESS_KEY_SECRET` 读取，**绝不硬编码、绝不写盘**；
3. 证书内容默认仅在内存中传递部署到 OSS，不落本地磁盘。

## 安装与环境

```bash
# 从本仓库拷贝整目录到本地 skills 目录（按平台约定）
cp -r workbuddy/skill/cloudq-oss-cert-rotation ~/.workbuddy/skills/cloudq-oss-cert-rotation
# 或上传到 WorkBuddy / Claude Code / Codex / Cursor 等支持 Agent Skills 的工具

# 安装写链路依赖（仅 plan 不需要）
python3 -m pip install -r requirements-rotate.txt
# 含：alibabacloud_cas20200407 alibabacloud_tea_openapi alibabacloud_tea_util oss2
# 可选：--auto-dns 自动加 TXT 验证记录时需 alibabacloud_alidns20150109
```

## 使用步骤

先准备最小权限的 RAM 子账号 AK（**切勿用主账号**），注入环境变量：

```bash
export ALIYUN_ACCESS_KEY_ID="LTAI5txxxxxxxxxxxx"
export ALIYUN_ACCESS_KEY_SECRET="xxxxxxxxxxxxxxxxxxxx"
```

填写 `config.json`（复制 `config.example.json`）：必填 `domain` / `oss_bucket` / `oss_endpoint`，其余可选。

| 子命令 | 用途 | 需要 AK | 写操作 |
|---|---|---|---|
| `plan` | 离线生成更新操作单（6 步 + 风险），不触云 | 否 | 无 |
| `inspect` | 只读查免费额度 + OSS 自定义域名证书状态 | 是（环境变量） | 无 |
| `rotate` | 端到端执行申请→验证→轮询→下载→部署 | 是 + `--authorized` | 有 |

```bash
# 1) 离线出操作单（确认 6 步与风险，尤其第 2 步消耗额度、第 6 步覆盖旧证）
python3 scripts/cert_rotate.py plan --config config.json

# 2) 只读核查：确认免费 remain>0 且 CNAME 已绑到 bucket
ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=yyy \
  python3 scripts/cert_rotate.py inspect --config config.json

# 3) 真正轮换（必须 --authorized；--auto-dns 自动加 TXT；--no-confirm-dns 跳过回车）
ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=yyy \
  python3 scripts/cert_rotate.py rotate --config config.json --authorized
```

`rotate` 成功输出示例：

```json
{ "order_id": "123456", "domain": "www.example.com",
  "status": "deployed", "cert_not_after": "2612..." }
```

## 重要警告

- **免费证只有 3 个月**：每 3 个月重跑一次，每次消耗 1/20 年额度；建议做成定时自动化（每 ~2 个月自动 rotate）。
- **真实云链路仍为 NOT_VERIFIED**：当前 47 个离线单测（假客户端注入）+ `plan`/`rotate` 授权门控冒烟已通过；但 `rotate` 真正申请 + 部署的端到端需用你的真实 RAM AK 验证。
- **覆盖即生效**：`deploy_oss` 使用 `force=True`，直接覆盖 OSS 自定义域名旧证书，无回滚按钮——确保 domain / oss_bucket 填对。
- **DNS 验证窗口**：手动加 TXT 后未等生效就回车会轮询超时；`--auto-dns` 可免去手动但需额外 AliDNS 权限。

## 相关文件

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 技能规范与触发条件、只读/写链路边界、六维自查表 |
| `README.md` | 概览、目录结构、子命令速查、单测方法 |
| `USAGE.html` | 精确到每步命令/参数/退出码的使用手册（本页精简版） |
| `scripts/cert_rotate.py` | v1.4.0 写链路：plan / inspect / rotate |
| `scripts/{entry_probe,cert_probe,probe_report,bench_baseline}.py` | 原 v1.3.1 只读巡检层 |
| `tests/` | 47 个离线单测（假客户端注入，覆盖申请→轮询→下载→部署全流程与授权门控） |
| `references/cloudq-integration-test.md` | CloudQ 接入测试方法（含 T7 写链路门控） |
| `config.example.json` | 配置样例 |
| `requirements-rotate.txt` | 写链路依赖 |

更多细节以仓库内 `SKILL.md` 与 `USAGE.html` 为准。
