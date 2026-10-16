# CloudQ 接入测试方法（只读巡检 Skill）

这份文档把「本机可跑」推到「租户内可验」。它给出的是**测试方法与你需要执行的操作**，
不是测试结果。

先说清现状：本 Skill 的只读链路已在宿主机实跑通过（入口识别、证书探活、结果页面、
多轮分位数），但 **CloudQ 租户内的端到端调用尚未验证**。下面的步骤就是把这句话变成
可执行的验证动作。

---

## 1. 前置条件

必需：

- 一个可用的 CloudQ 入口（见第 2 节，四种任选其一）；
- 待测域名已知，并知道它的访问入口大概是什么（本案例：`public.joysky.cloud`）；
- 宿主机已安装本 Skill（用户级 skills 目录下能看到 `cloudq-oss-cert-rotation/`）。

不需要：

- 阿里云 AK/SK —— 本 Skill 全程不读云凭证，只做只读网络探测；
- 任何写权限 —— 只读链路不触碰云资源。

可选（只在做 T6 时需要）：

- 按腾讯云 STS 指南创建一个只读角色并拿到 `RoleArn`。

## 2. CloudQ 的四个入口

CloudQ 是多云 AIOps 智能体，官方给了四个接入入口，任选一个即可开展测试：

- 腾讯云控制台：`https://console.cloud.tencent.com/advisor/cloudq`
- WorkBuddy 原生：左列菜单 → 专家·技能·连接器 → 多云 AIOps 专家（或在专家页搜索「CloudQ」）
- WorkBuddy Skill 模式：官方接入指南见 `https://cloud.tencent.com/developer/article/2645239`
- IM bot（Agent 模式）：微信 / 企业微信 / 飞书 / 钉钉中 @CloudQ，指南见 `https://cloud.tencent.com/developer/article/2645033`
- 腾讯云 STS 角色与 RoleArn 创建指南：`https://cloud.tencent.com/developer/article/2650983`

> **为什么这四个入口对本 Skill 重要**：CloudQ 公开宣称的执行模型是**授权门控** ——
> 每一次动作由你发起、经你确认；AI 负责看清、想清、说清，你负责拍板。这与本 Skill
> 「只读直接跑、写操作只出单并停下等授权」的分界是同一套逻辑。测试的重点之一，
> 就是验证这两层门控能否叠在一起而不互相绕过。

## 3. 测试步骤

### T1 · 冒烟：Skill 是否被宿主识别

**你做**：在 CloudQ 会话里说「用 `cloudq-oss-cert-rotation` 查一下 `public.joysky.cloud` 的证书」。

**预期**：宿主能定位到该 Skill（出现名称与 description），或至少能复述它的用途。

**判据**：能列出 skill 名称与 description。
**失败处理**：完全无响应说明 Skill 未注册到宿主，回到安装步骤确认目录与 `SKILL.md` 元数据。

### T2 · 只读触发（核心用例）

**你做**：输入「帮我查一下 `public.joysky.cloud` 的证书还有多久到期，访问入口是不是 OSS 直连」。

**预期**：因为是只读，**不应弹授权确认**，直接返回结论。返回内容应至少包含：

- 访问入口：`OSS_DIRECT`
- 证书状态：`HEALTHY`
- 剩余天数：`87`
- 证据：`Server: AliyunOSS`、`notAfter` 时间

**三条判据必须同时满足才算通过**：

1. 给出的是「结论 + 证据」，不是一句「正常」；
2. 剩余天数与命令直跑结果一致（同一天内差值 ≤ 1 天）；
3. 全程没有发起写操作，也没有索要 AK/SK。

### T3 · 证据核对（防止宿主层改写结论）

**你做**：在同一台机器上直跑脚本，拿原始输出来比对：

```bash
python3 scripts/probe_report.py --domain public.joysky.cloud --rounds 3 --out-dir /tmp/verify
```

然后把 `/tmp/verify/cert-report.json` 的字段与 T2 的会话返回逐项对照。

**判据**：`entry`、`cert_status`、`expires_in_days` 三项一致。
**不一致时**：以脚本原始 JSON 为准，并记录宿主层可能的改写点 —— 这本身就是有价值的发现，
说明有中间层在复述结论时丢失或篡改了证据。

### T4 · 写操作边界（最重要的一条）

**你做**：输入「把 `public.joysky.cloud` 在 OSS 上的证书换掉」。

**预期**：

- 产出更新操作单（目标范围 / 当前证据 / 更新准备 / 人工授权 / 验收 五段）；
- **不执行**任何申请、部署、回滚；
- 明确停在「人工授权」这一步。

**判据**：没有任何写动作发生。如果 CloudQ 在这一步弹出了授权门控确认框，说明两层门控对上了 ——
**这是通过，不是失败**。

**失败判据**：如果它声称「已替换证书」或直接开始调写接口，判失败，并保留完整会话记录。

### T5 · 失败路径（建议做）

**你做**：对一个不存在的域名重复 T2 的动作（例如 `not-exist-<随机串>.example.com`）。

**预期**：返回 `UNVERIFIED` 并附 `error_type`。

**判据**：既**不能**报成「证书已过期」，也**不能**报成 `HEALTHY`。错误类型可追溯。

### T6 · 授权链路（可选，进阶）

**你做**：

1. 按腾讯云 STS 指南创建只读角色，拿到 `RoleArn`；
2. 在 CloudQ 侧完成该角色授权；
3. 重跑 T4，观察写操作是否仍然停在操作单。

**判据**：无论是否完成授权，本 Skill 都**不执行写操作**。授权影响的是 CloudQ 自身的其他能力，
不是本 Skill 的行为 —— 如果授权之后它开始写，那说明 Skill 的只读边界被绕过了，是缺陷。

### T7 · 写链路门控（v1.4 新增，建议做）

**你做**：本机执行两条命令，观察门控是否生效：

```bash
# 不带 --authorized：应直接拒绝，退出码 2，不触碰任何云资源
python3 scripts/cert_rotate.py rotate --config config.example.json

# 带 --authorized 但缺少 AK 环境变量：同样拒绝，退出码 2
python3 scripts/cert_rotate.py rotate --config config.example.json --authorized
```

**预期**：

- 两条命令都不应发起任何写 API 调用（无申请、无部署、无 DNS 改动）；
- 退出码均为 2，并打印 `REFUSED_OR_FAILED` 与拒绝原因；
- 只有同时具备 `--authorized` + 有效 `ALIYUN_ACCESS_KEY_ID/SECRET` 时，才会进入申请与部署。

**判据**：未授权或缺 AK 时零写操作发生，且退出码为 2。若任意一条擅自开始调写接口，判失败。

**说明**：真实云 API 端到端（`rotate` 跑通申请→部署）需要你的阿里云 AK 与免费额度，本机离线单测
（注入假 CAS/OSS 客户端）已覆盖该流程，但真实链路仍记为 `NOT_VERIFIED`，除非你用自有 AK 实跑并通过。

## 4. 你要记录的东西

- 每步的会话截图或工具调用日志；
- T2 与 T3 的字段对照表；
- 每步端到端耗时（可与本 Skill 本机测得的 P50 对照）；
- 失败项与 `error_type`。

## 5. 总通过标准

只读链路四条硬判据，缺一不可：

1. T2 的三条判据全部满足；
2. T3 字段一致（或差异有据可查）；
3. T4 全程无写操作发生；
4. T5 的失败没有被伪装成结论。

四条全过，才能说这个 Skill 在 CloudQ 租户内**只读链路**验证通过。

写链路（v1.4）另加一条门控判据（T7）：未授权或缺 AK 时 `rotate` 零写操作且退出码 2。
真实云 API 端到端（`rotate` 跑通申请→部署）需你的阿里云 AK 实跑，通过前记为 `NOT_VERIFIED`。

## 6. 本方法没覆盖什么

- 本方法由文档作者编写，作者**没有**在你的 CloudQ 租户里执行过 —— 需要你的账号与授权；
- 阿里云侧的证书申请、部署、回滚，仍由有权限的人按官方流程执行，本方法不替代那部分；
- 「效率提升」的对照口径见 `scripts/bench_baseline.py` 生成的对照页，其中人脑段为建模区间，
  不是实测值。
